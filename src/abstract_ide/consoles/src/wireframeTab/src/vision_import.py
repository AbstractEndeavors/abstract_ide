#!/usr/bin/env python3
"""
vision_import — turn a UI screenshot into an (approximate) wireframe via a VL model.

Unlike the HTML path (which reads exact geometry from a render), a screenshot
has no ground-truth coordinates, so we ask a vision LLM to estimate the regions.
The working hugpy vision model is `Qwen2.5-VL-3B-Instruct-GGUF` (it has the
image projector). Practical realities this module handles:

  * downscale the image to <=768px wide — the GGUF mmproj 500s on larger images;
  * retry through 500/503 — the VL model is on a swap slot and cold-loads;
  * coordinates are COARSE — the model estimates position/size as percentages,
    so the result is a rough starting point to adjust, not a to-scale layout.

Endpoint/key resolution and the /api-prefix handling are reused from servicesTab
(same OpenAI-compatible client). The vision model id is configurable via
VISION_MODEL / ~/.config/services_tab/vision_model.
"""
import base64
import json
import re
import time
import urllib.error
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

VISION_PROMPT = (
    "You are analyzing a screenshot of a user interface. Identify the main "
    "rectangular regions (navbar, sidebar, content panels, buttons, inputs, "
    "images, lists, text blocks). Output ONLY a JSON object, no prose:\n"
    '{"regions":[{"role":"nav|sidebar|container|button|input|image|list|text",'
    '"label":"short name of what it is","x":<0-100>,"y":<0-100>,"w":<0-100>,"h":<0-100>}]}\n'
    "x,y are the top-left corner and w,h the width/height, each as a PERCENT of "
    "the image (0-100). Estimate the real position and size of each region as "
    "accurately as you can. List every distinct region, largest first."
)


def image_to_data_url(path, max_w=768):
    """Load + downscale an image to a base64 PNG data URL using Qt (no PIL dep)."""
    from PyQt6.QtCore import Qt, QByteArray, QBuffer, QIODevice
    from PyQt6.QtGui import QImage
    img = QImage(path)
    if img.isNull():
        raise ValueError("could not load image: %s" % path)
    if img.width() > max_w:
        img = img.scaledToWidth(max_w, Qt.TransformationMode.SmoothTransformation)
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return "data:image/png;base64," + base64.b64encode(bytes(ba)).decode()


def llm_vision(chat_url, key, model, data_url, prompt=VISION_PROMPT,
               timeout=180, retries=6):
    """POST an OpenAI vision message; retry 500/503 (the VL swap-slot cold-loads)."""
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer %s" % key
    body = json.dumps({
        "model": model, "max_tokens": 800, "temperature": 0.1,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}}]}],
    }).encode()
    last = "unknown"
    for _ in range(retries):
        try:
            req = urllib.request.Request(chat_url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode(errors="replace"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            last = "HTTP %d" % exc.code
            if exc.code in (500, 502, 503):      # cold-load / busy → wait + retry
                time.sleep(12)
                continue
            raise
        except Exception as exc:                 # transient network
            last = str(exc)
            time.sleep(8)
    raise RuntimeError("vision request failed after retries: %s" % last)


def parse_regions(text):
    """Pull the regions array out of the model's reply (tolerant of prose/fences)."""
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for r in (data.get("regions") or data.get("shapes") or []):
        try:
            # the model sometimes echoes the enum literal ("nav|sidebar|…") — take
            # the first token.
            role = str(r.get("role", "container")).split("|")[0].strip().lower()
            out.append({
                "role": role,
                "label": str(r.get("label") or r.get("name") or "region")[:40],
                "x": float(r.get("x", 0)), "y": float(r.get("y", 0)),
                "w": float(r.get("w", r.get("width", 10))),
                "h": float(r.get("h", r.get("height", 10))),
            })
        except (TypeError, ValueError):
            continue
    return out


def regions_to_shapes(regions, canvas, grid, roles):
    """Percent regions -> wireframe shape dicts, mapped to the canvas + snapped."""
    cw, ch = canvas

    def snap(v):
        return int(round(v / grid) * grid)

    shapes = []
    for i, r in enumerate(sorted(regions, key=lambda r: -(r["w"] * r["h"]))):
        role = r["role"] if r["role"] in roles else "container"
        shapes.append({
            "x": snap(r["x"] / 100 * cw), "y": snap(r["y"] / 100 * ch),
            "w": max(grid, snap(r["w"] / 100 * cw)),
            "h": max(grid, snap(r["h"] / 100 * ch)),
            "role": role, "label": r["label"], "z": i,
        })
    return shapes


class VisionThread(QThread):
    """Off-GUI: downscale + call the VL model + parse. Emits the regions."""
    result = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, path, chat_url, key, model, parent=None):
        super().__init__(parent)
        self._path, self._url, self._key, self._model = path, chat_url, key, model

    def run(self):
        try:
            data_url = image_to_data_url(self._path)
            text = llm_vision(self._url, self._key, self._model, data_url)
            self.result.emit(parse_regions(text))
        except Exception as exc:
            self.error.emit(str(exc))
