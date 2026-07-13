#!/usr/bin/env python3
"""
hugpyTab generative modalities — the non-chat model tasks.

Two backends, both on dev.hugpy.ai:

  * Async media jobs (image / video): POST /api/video/jobs/generate_image
    (or generate_scene) returns {job_id}; poll GET /api/video/jobs/<id> until
    status is done/failed. On success result.outputs[i].uri is a server path,
    fetched as bytes via GET /api/video/media?handle=<uri>. Jobs are cancelable.
  * Sync /ml/* amenities: POST /api/ml/<embed|transcribe|similarity|depth|
    detect|classify|segment> -> {ok, ...}. Text tasks take JSON {text|texts};
    media tasks (transcribe audio, analyze image) accept a direct multipart file
    (the server saves it like /uploads and runs the fixed task).

The whole panel adapts its inputs to the selected model's modality. Generation
may report `local_serving_disabled` when the fleet has no GPU worker serving the
model — that's a fleet-capacity gap, surfaced verbatim, not a client fault.
"""
import base64
import json
import os
import urllib.parse
import urllib.request

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QScrollArea, QSpinBox, QStackedWidget, QTextEdit, QVBoxLayout,
    QWidget,
)

from ...servicesTab.src.main import _origin


# ─────────────────────────────── HTTP ──────────────────────────────────────
def _headers(key, ctype=None):
    h = {"Accept": "application/json"}
    if ctype:
        h["Content-Type"] = ctype
    if key:
        h["Authorization"] = "Bearer %s" % key
    return h


def post_json(base, path, payload, key="", timeout=60):
    req = urllib.request.Request(_origin(base) + path,
                                 data=json.dumps(payload).encode(),
                                 headers=_headers(key, "application/json"))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode(errors="replace")
    return json.loads(raw) if raw.strip() else {}


def get_json(base, path, key="", timeout=30):
    req = urllib.request.Request(_origin(base) + path, headers=_headers(key))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode(errors="replace")
    return json.loads(raw) if raw.strip() else {}


def post_multipart(base, path, filepath, fields=None, key="", timeout=300):
    """POST a single file as multipart/form-data (no requests dependency)."""
    boundary = "----hugpyTab%s" % base64.b16encode(os.urandom(8)).decode()
    with open(filepath, "rb") as fh:
        content = fh.read()
    lines = []
    for k, v in (fields or {}).items():
        lines.append(b"--" + boundary.encode())
        lines.append(('Content-Disposition: form-data; name="%s"' % k).encode())
        lines.append(b"")
        lines.append(str(v).encode())
    lines.append(b"--" + boundary.encode())
    lines.append(('Content-Disposition: form-data; name="file"; filename="%s"'
                  % os.path.basename(filepath)).encode())
    lines.append(b"Content-Type: application/octet-stream")
    lines.append(b"")
    lines.append(content)
    lines.append(b"--" + boundary.encode() + b"--")
    lines.append(b"")
    body = b"\r\n".join(lines)
    headers = _headers(key, "multipart/form-data; boundary=%s" % boundary)
    req = urllib.request.Request(_origin(base) + path, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode(errors="replace")
    return json.loads(raw) if raw.strip() else {}


def fetch_media(base, key, uri, timeout=60):
    """Raw bytes for a generated media ref (server path via /video/media, or URL)."""
    if uri.startswith("http://") or uri.startswith("https://"):
        url = uri
    else:
        url = (_origin(base) + "/api/video/media?handle="
               + urllib.parse.quote(uri, safe=""))
    req = urllib.request.Request(url, headers=_headers(key))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ──────────────────────────── generation API ───────────────────────────────
_DONE = {"done", "completed", "complete", "success", "succeeded", "finished"}
_FAIL = {"failed", "error", "cancelled", "canceled"}


def enqueue_image(base, key, spec):
    parts = [{"kind": "text", "text": spec["prompt"]}]
    body = {"parts": parts, "model_id": spec["model_id"],
            "width": spec["width"], "height": spec["height"],
            "steps": spec["steps"], "guidance": spec["guidance"]}
    if spec.get("negative"):
        body["negative"] = spec["negative"]
    if spec.get("seed", -1) is not None and spec["seed"] >= 0:
        body["seed"] = spec["seed"]
    return post_json(base, "/api/video/jobs/generate_image", body, key).get("job_id")


def enqueue_scene(base, key, spec):
    parts = [{"kind": "text", "text": spec["prompt"]}]
    body = {"parts": parts, "model_id": spec["model_id"],
            "width": spec["width"], "height": spec["height"],
            "steps": spec["steps"], "guidance": spec["guidance"],
            "n_frames": spec["n_frames"], "fps": spec["fps"], "assemble": True}
    if spec.get("negative"):
        body["negative"] = spec["negative"]
    return post_json(base, "/api/video/jobs/generate_scene", body, key).get("job_id")


def poll_job(base, key, job_id):
    return get_json(base, "/api/video/jobs/%s" % job_id, key)


def cancel_job(base, key, job_id):
    return post_json(base, "/api/video/jobs/%s/cancel" % job_id, {}, key)


def output_uris(result):
    uris = []
    for o in (result.get("outputs") or []):
        if isinstance(o, dict):
            u = o.get("uri") or o.get("url") or o.get("path")
            if u:
                uris.append(u)
        elif isinstance(o, str):
            uris.append(o)
    mv = result.get("movie")
    if isinstance(mv, dict):
        u = mv.get("uri") or mv.get("url") or mv.get("path")
        if u:
            uris.append(u)
    elif isinstance(mv, str):
        uris.append(mv)
    return uris


def job_error(result):
    e = result.get("error")
    if isinstance(e, dict):
        return e.get("message") or e.get("code") or json.dumps(e)
    return e


# ─────────────────────────────── threads ───────────────────────────────────
class _Work(QThread):
    done = pyqtSignal(bool, object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.done.emit(True, self._fn())
        except Exception as exc:
            self.done.emit(False, str(exc))


class JobThread(QThread):
    """Enqueue a media job then poll to completion; cancelable via the endpoint."""
    progress = pyqtSignal(str)
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, base, key, enqueue_fn, parent=None):
        super().__init__(parent)
        self._base, self._key, self._enqueue = base, key, enqueue_fn
        self._job_id = None

    def run(self):
        try:
            job_id = self._enqueue()
            if not job_id:
                self.error.emit("no job_id returned by enqueue")
                return
            self._job_id = job_id
            for _ in range(800):                 # ~20 min ceiling
                if self.isInterruptionRequested():
                    self._finish_cancel(job_id)
                    return
                j = poll_job(self._base, self._key, job_id)
                st = str(j.get("status") or j.get("state") or "?").lower()
                pr = j.get("progress")
                self.progress.emit(st + ("" if pr in (None, "") else " %s" % pr))
                if st in _DONE or st in _FAIL:
                    self.done.emit(j)
                    return
                for _ in range(6):               # chunked sleep = snappy Cancel
                    if self.isInterruptionRequested():
                        break
                    self.msleep(250)
            self.error.emit("timed out waiting for job")
        except Exception as exc:
            self.error.emit(str(exc))

    def _finish_cancel(self, job_id):
        # The job may have completed between the last poll and the interrupt —
        # don't discard a finished result as "cancelled".
        try:
            final = poll_job(self._base, self._key, job_id)
        except Exception:
            final = {}
        if str(final.get("status") or "").lower() in _DONE:
            self.done.emit(final)
            return
        try:
            cancel_job(self._base, self._key, job_id)
        except Exception:
            pass
        self.error.emit("cancelled")


# ──────────────────────────── the panel ────────────────────────────────────
# modality -> (input-page key, run-button label)
_RUN_LABEL = {"image": "Generate", "video": "Generate", "embed": "Embed",
              "audio": "Transcribe", "analyze": "Run"}


class GeneratePanel(QWidget):
    """Adaptive workbench for the generative / analysis modalities. get_ctx() is a
    callable returning (base, key, model_key) from the parent tab."""

    def __init__(self, get_ctx, parent=None):
        super().__init__(parent)
        self._get_ctx = get_ctx
        self._modality = "other"
        self._model_task = None
        self._threads = []
        self._job = None
        self._last_pixmap = None
        self._closing = False
        self._build_ui()

    # ── ui ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        self.header = QLabel("Select a generative model from the catalog.")
        self.header.setWordWrap(True)
        self.header.setStyleSheet("font-weight:bold;")
        root.addWidget(self.header)

        self.inputs = QStackedWidget()
        self.inputs.addWidget(self._build_image_form())    # 0 image
        self.inputs.addWidget(self._build_video_form())    # 1 video
        self.inputs.addWidget(self._build_text_form())     # 2 embed
        self.inputs.addWidget(self._build_file_form("audio"))    # 3 audio
        self.inputs.addWidget(self._build_file_form("analyze"))  # 4 analyze
        self.inputs.addWidget(QLabel("This model has no generative panel."))  # 5 other
        self._page = {"image": 0, "video": 1, "embed": 2, "audio": 3, "analyze": 4, "other": 5}
        root.addWidget(self.inputs)

        brow = QHBoxLayout()
        self.run_btn = QPushButton("Generate")
        self.run_btn.clicked.connect(self._run)
        brow.addWidget(self.run_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setEnabled(False)
        brow.addWidget(self.cancel_btn)
        self.save_btn = QPushButton("Save image…")
        self.save_btn.clicked.connect(self._save_image)
        self.save_btn.setEnabled(False)
        brow.addWidget(self.save_btn)
        brow.addStretch(1)
        root.addLayout(brow)

        # output: image (scroll) or text
        self.out = QStackedWidget()
        self.img_scroll = QScrollArea()
        self.img_scroll.setWidgetResizable(True)
        self.img_label = QLabel("(output appears here)")
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_scroll.setWidget(self.img_label)
        self.out.addWidget(self.img_scroll)                 # 0 image
        self.text_out = QTextEdit()
        self.text_out.setReadOnly(True)
        self.text_out.setStyleSheet("QTextEdit { background:#ffffff; color:#1a1a1a; }")
        self.out.addWidget(self.text_out)                   # 1 text
        root.addWidget(self.out, 1)

        self.status = QLabel("")
        root.addWidget(self.status)

    def _labeled(self, form, label, widget):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(widget, 1)
        form.addLayout(row)

    def _build_image_form(self):
        w = QWidget()
        f = QVBoxLayout(w)
        self.i_prompt = QLineEdit()
        self.i_prompt.setPlaceholderText("prompt — what to generate")
        self._labeled(f, "Prompt:", self.i_prompt)
        self.i_negative = QLineEdit()
        self.i_negative.setPlaceholderText("negative prompt (optional)")
        self._labeled(f, "Negative:", self.i_negative)
        row = QHBoxLayout()
        self.i_steps = QSpinBox(); self.i_steps.setRange(1, 150); self.i_steps.setValue(20)
        self.i_guidance = QDoubleSpinBox(); self.i_guidance.setRange(0.0, 30.0)
        self.i_guidance.setSingleStep(0.5); self.i_guidance.setValue(4.0)
        self.i_width = QSpinBox(); self.i_width.setRange(128, 2048)
        self.i_width.setSingleStep(64); self.i_width.setValue(768)
        self.i_height = QSpinBox(); self.i_height.setRange(128, 2048)
        self.i_height.setSingleStep(64); self.i_height.setValue(768)
        self.i_seed = QSpinBox(); self.i_seed.setRange(-1, 2147483647); self.i_seed.setValue(-1)
        for lbl, wid in (("steps", self.i_steps), ("guidance", self.i_guidance),
                         ("W", self.i_width), ("H", self.i_height), ("seed", self.i_seed)):
            row.addWidget(QLabel(lbl)); row.addWidget(wid)
        row.addStretch(1)
        f.addLayout(row)
        return w

    def _build_video_form(self):
        w = QWidget()
        f = QVBoxLayout(w)
        self.v_prompt = QLineEdit()
        self.v_prompt.setPlaceholderText("prompt — the scene to animate")
        self._labeled(f, "Prompt:", self.v_prompt)
        row = QHBoxLayout()
        self.v_frames = QSpinBox(); self.v_frames.setRange(2, 120); self.v_frames.setValue(8)
        self.v_fps = QSpinBox(); self.v_fps.setRange(1, 60); self.v_fps.setValue(8)
        self.v_steps = QSpinBox(); self.v_steps.setRange(1, 150); self.v_steps.setValue(20)
        self.v_guidance = QDoubleSpinBox(); self.v_guidance.setRange(0.0, 30.0)
        self.v_guidance.setSingleStep(0.5); self.v_guidance.setValue(4.0)
        self.v_width = QSpinBox(); self.v_width.setRange(128, 1536)
        self.v_width.setSingleStep(64); self.v_width.setValue(512)
        self.v_height = QSpinBox(); self.v_height.setRange(128, 1536)
        self.v_height.setSingleStep(64); self.v_height.setValue(512)
        for lbl, wid in (("frames", self.v_frames), ("fps", self.v_fps),
                         ("steps", self.v_steps), ("guidance", self.v_guidance),
                         ("W", self.v_width), ("H", self.v_height)):
            row.addWidget(QLabel(lbl)); row.addWidget(wid)
        row.addStretch(1)
        f.addLayout(row)
        return w

    def _build_text_form(self):
        w = QWidget()
        f = QVBoxLayout(w)
        f.addWidget(QLabel("Text to embed:"))
        self.t_text = QPlainTextEdit()
        self.t_text.setPlaceholderText("text — the vector / analysis is computed for this")
        f.addWidget(self.t_text)
        return w

    def _build_file_form(self, which):
        w = QWidget()
        f = QVBoxLayout(w)
        row = QHBoxLayout()
        edit = QLineEdit(); edit.setReadOnly(True)
        edit.setPlaceholderText("audio file…" if which == "audio" else "image file…")
        btn = QPushButton("Browse…")
        row.addWidget(edit, 1); row.addWidget(btn)
        f.addLayout(row)
        f.addStretch(1)
        if which == "audio":
            self.a_path = edit
            btn.clicked.connect(lambda: self._pick_file(self.a_path,
                "Audio (*.wav *.mp3 *.m4a *.flac *.ogg *.webm *.mp4 *.mkv)"))
        else:
            self.n_path = edit
            btn.clicked.connect(lambda: self._pick_file(self.n_path,
                "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"))
        return w

    def _pick_file(self, edit, filt):
        path, _ = QFileDialog.getOpenFileName(self, "Choose file", "", filt)
        if path:
            edit.setText(path)

    # ── model selection ──────────────────────────────────────────────────
    def set_model(self, model, modality):
        # Switching models abandons any in-flight job for the previous model.
        if self._job and self._job.isRunning():
            self._job.requestInterruption()
        self._modality = modality
        self._model_task = model.get("primary_task")
        mk = model.get("model_key")
        pt = self._model_task or "unknown"
        self.inputs.setCurrentIndex(self._page.get(modality, 5))
        self.run_btn.setText(_RUN_LABEL.get(modality, "Run"))
        self._set_running(False)
        # clear any prior output / save state for the new selection
        self._last_pixmap = None
        self.save_btn.setEnabled(False)
        self.text_out.clear()
        self.img_label.clear()
        self.img_label.setText("(output appears here)")
        self.out.setCurrentIndex(1)
        self.status.setText("")
        note = {
            "image": "text-to-image — enter a prompt and Generate. Result renders below.",
            "video": "video — a prompt is animated into frames + an mp4 (async, slower).",
            "embed": "embeddings — returns the vector (dims, L2 norm, first values).",
            "audio": "speech-to-text — choose an audio file and Transcribe.",
            "analyze": "image analysis — choose an image; result shown as JSON/text or an image.",
        }.get(modality, "no generative panel for this task")
        self.header.setText("%s   ·   task: %s\n%s" % (mk, pt, note))

    # ── run ──────────────────────────────────────────────────────────────
    def _ctx(self):
        return self._get_ctx()

    def _run(self):
        if self._job and self._job.isRunning():
            self.status.setText("A job is already running — cancel it first.")
            return
        base, key, mk = self._ctx()
        if not mk:
            self.status.setText("Select a model first.")
            return
        m = self._modality
        if m in ("image", "video"):
            self._run_job(base, key, mk, m)
        elif m == "embed":
            self._run_embed(base, key, mk)
        elif m == "audio":
            self._run_file(base, key, mk, "transcribe", self.a_path.text())
        elif m == "analyze":
            self._run_file(base, key, mk,
                           _analyze_amenity(self._model_task, mk), self.n_path.text())

    def _run_job(self, base, key, mk, kind):
        if kind == "image":
            spec = {"model_id": mk, "prompt": self.i_prompt.text().strip(),
                    "negative": self.i_negative.text().strip(),
                    "steps": self.i_steps.value(), "guidance": self.i_guidance.value(),
                    "width": self.i_width.value(), "height": self.i_height.value(),
                    "seed": self.i_seed.value()}
            if not spec["prompt"]:
                self.status.setText("Enter a prompt.")
                return
            fn = lambda: enqueue_image(base, key, spec)
        else:
            spec = {"model_id": mk, "prompt": self.v_prompt.text().strip(),
                    "negative": "", "steps": self.v_steps.value(),
                    "guidance": self.v_guidance.value(), "width": self.v_width.value(),
                    "height": self.v_height.value(), "n_frames": self.v_frames.value(),
                    "fps": self.v_fps.value()}
            if not spec["prompt"]:
                self.status.setText("Enter a prompt.")
                return
            fn = lambda: enqueue_scene(base, key, spec)
        self._set_running(True)
        self.status.setText("Submitting job…")
        self._job = JobThread(base, key, fn, self)
        self._job.progress.connect(lambda s: self.status.setText("Job: %s" % s))
        self._job.done.connect(lambda r: self._on_job_done(base, key, r))
        self._job.error.connect(self._on_run_error)
        self._track(self._job)
        self._job.start()

    def _on_job_done(self, base, key, job):
        if self._closing:
            return
        # The final job dict is {job_id, status, progress, result:{...}} — the
        # error/outputs/movie live in the nested `result`.
        result = job.get("result") if isinstance(job.get("result"), dict) else job
        status = str(job.get("status") or "").lower()
        err = job_error(result)
        failed = bool(err) or status in _FAIL or (
            isinstance(result, dict) and result.get("ok") is False)
        if failed:
            self._set_running(False)
            self._show_text("Generation failed:\n%s"
                            % (err or json.dumps(result, indent=2)[:1500]))
            self.status.setText("Failed.")
            return
        # Video: the deliverable is the assembled mp4 (movie), not a single frame.
        movie = None
        mv = result.get("movie")
        if isinstance(mv, dict):
            movie = mv.get("uri") or mv.get("url") or mv.get("path")
        elif isinstance(mv, str):
            movie = mv
        uris = output_uris(result)
        if self._modality == "video" and movie:
            self._set_running(False)
            self._show_text("Video ready (mp4):\n%s\n\nFetch: GET /api/video/media?handle=%s"
                            % (movie, movie))
            self.status.setText("Done — video.")
            return
        if not uris:
            self._set_running(False)
            self._show_text("Job finished but returned no outputs:\n%s"
                            % json.dumps(result, indent=2)[:2000])
            self.status.setText("Done (no output).")
            return
        # fetch the first output; if it's an image render it, else show the path.
        uri = uris[0]
        self.status.setText("Fetching result…")
        t = _Work(lambda: fetch_media(base, key, uri), self)

        def after(ok, data):
            if self._closing:
                return
            self._set_running(False)
            if not ok:
                self._show_text("Generated %d output(s); first = %s\n(could not fetch: %s)"
                                % (len(uris), uri, data))
                return
            pm = QPixmap()
            if isinstance(data, (bytes, bytearray)) and pm.loadFromData(data):
                self._show_image(pm)
                self.status.setText("Done — %d output(s)." % len(uris))
            else:
                kind = "video/mp4" if self._modality == "video" else "a non-image format"
                self._show_text("Output is %s:\n%s\nFetch via GET /api/video/media?handle=%s"
                                % (kind, uri, uri))
                self.status.setText("Done — %d output(s)." % len(uris))
        t.done.connect(after)
        self._track(t)
        t.start()

    def _run_embed(self, base, key, mk):
        text = self.t_text.toPlainText().strip()
        if not text:
            self.status.setText("Enter some text.")
            return
        self._set_running(True)
        self.status.setText("Embedding…")
        payload = {"text": text, "model_key": mk}
        t = _Work(lambda: post_json(base, "/api/ml/embed", payload, key), self)
        t.done.connect(self._on_embed_done)
        self._track(t)
        t.start()

    def _on_embed_done(self, ok, res):
        if self._closing:
            return
        self._set_running(False)
        if not ok:
            self._show_text("Embed failed:\n%s" % res)
            self.status.setText("Failed.")
            return
        embs = res.get("embeddings") or []
        vec = embs[0] if embs and isinstance(embs[0], list) else (embs if embs else [])
        if not vec:
            self._show_text(json.dumps(res, indent=2)[:2000])
            self.status.setText("Done.")
            return
        norm = sum(x * x for x in vec) ** 0.5
        head = ", ".join("%.4f" % x for x in vec[:12])
        self._show_text("model: %s\ndims: %d\nL2 norm: %.4f\nfirst 12: [%s, …]"
                        % (res.get("model_key") or "?", len(vec), norm, head))
        self.status.setText("Done — %d-dim vector." % len(vec))

    def _run_file(self, base, key, mk, amenity, path):
        if not path or not os.path.isfile(path):
            self.status.setText("Choose a file first.")
            return
        self._set_running(True)
        self.status.setText("Uploading + running %s…" % amenity)
        fields = {"model_key": mk}
        t = _Work(lambda: post_multipart(base, "/api/ml/%s" % amenity, path, fields, key), self)
        t.done.connect(lambda ok, r: self._on_ml_done(ok, r, base, key))
        self._track(t)
        t.start()

    def _on_ml_done(self, ok, res, base, key):
        if self._closing:
            return
        self._set_running(False)
        if not ok:
            self._show_text("Request failed:\n%s" % res)
            self.status.setText("Failed.")
            return
        if isinstance(res, dict) and res.get("ok") is False:
            err = job_error(res) or res.get("error") or json.dumps(res)
            self._show_text("Error: %s" % err)
            self.status.setText("Failed.")
            return
        # transcription / text results
        text = res.get("text") if isinstance(res, dict) else None
        if text:
            self._show_text(text)
            self.status.setText("Done.")
            return
        # some analysis tasks return an image ref (e.g. depth map / segmentation)
        uris = output_uris(res) if isinstance(res, dict) else []
        if uris:
            t = _Work(lambda: fetch_media(base, key, uris[0]), self)

            def after(ok2, data):
                pm = QPixmap()
                if ok2 and isinstance(data, (bytes, bytearray)) and pm.loadFromData(data):
                    self._show_image(pm)
                else:
                    self._show_text(json.dumps(res, indent=2)[:3000])
                self.status.setText("Done.")
            t.done.connect(after)
            self._track(t)
            t.start()
            return
        self._show_text(json.dumps(res, indent=2)[:3000])
        self.status.setText("Done.")

    # ── output helpers ───────────────────────────────────────────────────
    def _show_image(self, pixmap):
        self._last_pixmap = pixmap
        self.img_label.setPixmap(pixmap)
        self.img_label.resize(pixmap.size())
        self.out.setCurrentIndex(0)
        self.save_btn.setEnabled(True)

    def _show_text(self, text):
        self.text_out.setPlainText(text)
        self.out.setCurrentIndex(1)
        self.save_btn.setEnabled(False)

    def _save_image(self):
        if self._last_pixmap is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save image", "generated.png",
                                              "PNG (*.png);;JPEG (*.jpg)")
        if path:
            self._last_pixmap.save(path)
            self.status.setText("Saved to %s" % path)

    def _set_running(self, on):
        # Only re-enable Run for a modality that actually has a run action.
        self.run_btn.setEnabled((not on) and self._modality in _RUN_LABEL)
        self.cancel_btn.setEnabled(on and self._modality in ("image", "video"))

    def _cancel(self):
        if self._job and self._job.isRunning():
            self._job.requestInterruption()
            self.status.setText("Cancelling…")

    def _on_run_error(self, msg):
        if self._closing:
            return
        self._set_running(False)
        self._show_text("Error: %s" % msg)
        self.status.setText("Error: %s" % msg)

    # ── thread lifecycle ─────────────────────────────────────────────────
    def _track(self, thread):
        self._threads.append(thread)
        thread.finished.connect(lambda: self._drop(thread))

    def _drop(self, thread):
        if thread in self._threads:
            self._threads.remove(thread)

    def shutdown(self):
        self._closing = True                     # blocks slots spawning new threads
        for t in list(self._threads):
            try:
                t.blockSignals(True)
                if isinstance(t, JobThread):
                    t.requestInterruption()
            except RuntimeError:
                pass
        # Several passes so a thread spawned by an in-flight signal handler (the
        # post-job media fetch) is also drained rather than outliving the widget.
        for _ in range(4):
            for t in list(self._threads):
                try:
                    t.wait(1000)
                except RuntimeError:
                    pass
            if not self._threads:
                break


_TASK_AMENITY = {"depth-estimation": "depth", "object-detection": "detect",
                 "image-classification": "classify", "image-segmentation": "segment"}


def _analyze_amenity(task, model_key=""):
    """The fixed /ml amenity for an image-analysis model — by task (the reliable
    signal), falling back to a key heuristic."""
    if task in _TASK_AMENITY:
        return _TASK_AMENITY[task]
    k = (model_key or "").lower()
    if "depth" in k:
        return "depth"
    if "detr" in k or "detect" in k:
        return "detect"
    if "seg" in k:
        return "segment"
    return "classify"
