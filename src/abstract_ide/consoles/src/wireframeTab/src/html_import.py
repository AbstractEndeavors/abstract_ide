#!/usr/bin/env python3
"""
html_import — turn a real HTML page into a to-scale wireframe.

The accurate path: don't ask an LLM to guess coordinates — RENDER the HTML and
read each element's true bounding box (getBoundingClientRect), which is exact.
Tags map to wireframe roles; element text becomes the label. The same
extraction JS runs under either backend:

  * QtWebEngine (product)  — no external browser, part of the Qt stack.
  * playwright/chromium (tests) — the identical Chromium engine, so validating
    the pipeline here proves the JS + geometry + shape building.

Both return the same list of {tag, x, y, w, h, text}; boxes_to_shapes() scales
that to the canvas and snaps to the grid.
"""

# Layout-significant + interactive tags, and how each maps to a wireframe role.
TAG_ROLE = {
    "header": "nav", "nav": "nav", "footer": "nav",
    "aside": "sidebar",
    "main": "container", "section": "container", "article": "container",
    "form": "container", "div": "container",
    "button": "button", "a": "button",
    "input": "input", "textarea": "input", "select": "input",
    "img": "image", "picture": "image", "svg": "image", "video": "image",
    "ul": "list", "ol": "list", "table": "list",
    "h1": "text", "h2": "text", "h3": "text", "p": "text", "label": "text",
}

# One expression that returns the boxes; works with QtWebEngine.runJavaScript
# and playwright.evaluate alike.
EXTRACT_JS = r"""(() => {
  const tags = ['header','nav','aside','main','section','article','footer','form',
                'ul','ol','table','button','a','input','textarea','select',
                'img','picture','svg','video','h1','h2','h3','p','label'];
  const out = [], seen = new Set();
  for (const el of document.querySelectorAll(tags.join(','))) {
    const r = el.getBoundingClientRect();
    if (r.width < 24 || r.height < 12) continue;
    const key = el.tagName + '|' + Math.round(r.x) + '|' + Math.round(r.y)
              + '|' + Math.round(r.width) + '|' + Math.round(r.height);
    if (seen.has(key)) continue;
    seen.add(key);
    let text = (el.innerText || el.getAttribute('aria-label') ||
                el.getAttribute('alt') || el.getAttribute('placeholder') || '')
               .replace(/\s+/g, ' ').trim();
    out.push({tag: el.tagName.toLowerCase(),
              x: r.x + window.scrollX, y: r.y + window.scrollY,
              w: r.width, h: r.height, text: text.slice(0, 40)});
  }
  return out;
})()"""


def boxes_to_shapes(boxes, viewport, canvas, grid, max_shapes=60):
    """Extracted boxes -> wireframe shape dicts, scaled to fit the canvas and
    snapped to the grid. Bigger regions get a lower z so they sit behind."""
    boxes = [b for b in boxes if b.get("w", 0) >= 24 and b.get("h", 0) >= 12]
    if not boxes:
        return []
    max_x = max(b["x"] + b["w"] for b in boxes)
    max_y = max(b["y"] + b["h"] for b in boxes)
    cw, ch = canvas
    scale = min(cw / max(max_x, 1), ch / max(max_y, 1), 1.0)
    boxes = sorted(boxes, key=lambda b: -(b["w"] * b["h"]))[:max_shapes]

    def snap(v):
        return int(round(v / grid) * grid)

    shapes = []
    for i, b in enumerate(boxes):
        role = TAG_ROLE.get(b.get("tag", ""), "container")
        label = (b.get("text") or b.get("tag") or "").strip()[:40] or b.get("tag", "box")
        shapes.append({
            "x": snap(b["x"] * scale), "y": snap(b["y"] * scale),
            "w": max(grid, snap(b["w"] * scale)), "h": max(grid, snap(b["h"] * scale)),
            "role": role, "label": label, "z": i,
        })
    return shapes


def render_qtwebengine(source, viewport, on_done, on_error, is_file=True):
    """Render HTML with QtWebEngine and hand the extracted boxes to on_done.
    Returns the QWebEngineView, which the caller MUST keep referenced until
    on_done fires (Qt would otherwise GC it mid-render). Lazy import so the tab
    (and the whole IDE) still loads if PyQt6-WebEngine isn't installed."""
    from PyQt6.QtCore import QUrl, QTimer
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    view = QWebEngineView()
    view.resize(viewport[0], viewport[1])
    page = view.page()
    state = {"done": False}

    def finish(result):
        if state["done"]:
            return
        state["done"] = True
        try:
            on_done(result or [])
        finally:
            view.deleteLater()

    def loaded(ok):
        if state["done"]:
            return
        if not ok:
            state["done"] = True
            on_error("HTML failed to render")
            view.deleteLater()
            return
        # small settle delay so late layout/fonts are reflected
        QTimer.singleShot(350, lambda: page.runJavaScript(EXTRACT_JS, finish))

    page.loadFinished.connect(loaded)
    if is_file:
        view.load(QUrl.fromLocalFile(source))   # resolves relative CSS/img/JS
    else:
        view.setHtml(source)
    return view


def render_playwright(source, viewport, is_file=True):
    """Synchronous render via playwright/chromium — used by tests only."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        if is_file:
            page.goto("file://" + source)
        else:
            page.set_content(source)
        boxes = page.evaluate(EXTRACT_JS)
        browser.close()
    return boxes
