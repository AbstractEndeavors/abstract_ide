#!/usr/bin/env python3
"""
hugpyTab — a client/proxy for the hugpy fleet (dev.hugpy.ai), embedded as an
ideConsole tab. It replicates the model-chat experience of dev.hugpy.ai/console
so you can pick any served model and test what it can actually do, with the
inputs a model's task expects wired to the endpoint that model delegates to.

Panes:
  * Catalog (left) — every model from /api/models with its primary_task, size,
    a vision flag and its LIVE serving state (cross-referenced against
    /api/llm/serving and the workers' currently-loaded models). Filter by
    task/name.
  * Chat (right)  — task-aware workbench. text-generation / summarization models
    get a plain chat box; vision (image-text-to-text, mmproj>0) models add an
    image attachment. Both stream via the OpenAI-compatible /v1/chat/completions.
    Non-chat generative models (text-to-image, video, asr, …) are labeled and
    deferred — use the Schema tab to hit their endpoints directly for now.
  * Fleet (right) — worker health (/api/llm/workers), the serving table
    (/api/llm/serving) and slots (/api/llm/slots), plus a "warm" button that
    POSTs /api/llm/slots/load {model_key} to bring a cold model online.
  * Schema (right) — the full /endpoints?format=json route table wired into an
    embedded general REST client so any endpoint can be fired.

Provider-neutral: the endpoint/key resolve exactly like the Services tab, and no
credential is hardcoded (this package publishes to PyPI). The OpenAI-compatible
client (resolve_routes / llm_stream / config) and the image→data-url helper are
reused from the sibling tabs rather than duplicated.
"""
import json
import os
import urllib.request

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QSpinBox, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

# Reuse the Services tab's provider-neutral OpenAI-compatible client + config
# (3-dot relative import = consoles.src.servicesTab.src.main).
from ...servicesTab.src.main import (
    LLM_API_CHOICES, LLM_API_DEFAULT, LLM_API_KEY_DEFAULT, LLM_MAX_TOKENS,
    _origin, llm_stream, think_suffix,
)
from .generate import GeneratePanel

# ──────────────────────────── model classification ─────────────────────────
# The model's task metadata is what associates it with the right inputs and the
# right endpoint. A chat-capable model (text or vision) drives the Chat pane;
# everything else is a generative modality handled elsewhere.
CHAT_LIKE = {"text-generation", "text2text-generation", "text-summarization",
             "image-text-to-text"}
VISION_TASKS = {"image-text-to-text"}

# Serving-state cell colours.
_GREEN = QColor(205, 240, 205)
_ORANGE = QColor(250, 232, 190)
_GRAY = QColor(238, 238, 238)
_RED = QColor(245, 205, 205)


def _tasks(m):
    ts = set(t for t in (m.get("tasks") or []) if t)
    if m.get("primary_task"):
        ts.add(m["primary_task"])
    return ts


def is_vision(m):
    """A model that accepts an image alongside text (has an image projector)."""
    return (m.get("mmproj_bytes") or 0) > 0 or bool(_tasks(m) & VISION_TASKS)


def is_chat(m):
    """Chat-capable: a text/vision task, or no task metadata (plain llama-server)."""
    ts = _tasks(m)
    return (not ts) or bool(ts & CHAT_LIKE)


def primary_task(m):
    if m.get("primary_task"):
        return m["primary_task"]
    ts = sorted(_tasks(m))
    return ts[0] if ts else "unknown"


# Non-chat modality routing — which generative panel a model's task maps to.
IMAGE_TASKS = {"text-to-image", "image-to-image"}
VIDEO_TASKS = {"image-to-video", "video-generation"}
EMBED_TASKS = {"feature-extraction", "sentence-similarity"}
AUDIO_TASKS = {"automatic-speech-recognition"}
ANALYZE_TASKS = {"depth-estimation", "object-detection",
                 "image-classification", "image-segmentation"}


def modality(m):
    """Which workbench a model drives: chat, or a generative/analysis panel."""
    if is_chat(m):
        return "chat"
    pt = primary_task(m)
    if pt in IMAGE_TASKS:
        return "image"
    if pt in VIDEO_TASKS:
        return "video"
    if pt in EMBED_TASKS:
        return "embed"
    if pt in AUDIO_TASKS:
        return "audio"
    if pt in ANALYZE_TASKS:
        return "analyze"
    return "other"


def _fmt_gb(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    return "%.1f GB" % (n / 1e9) if n >= 1e9 else "%.0f MB" % (n / 1e6)


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _norm(base):
    """A hand-typed bare host (no scheme) would make urllib raise 'unknown url
    type' — default it to http:// so it degrades to a normal connection."""
    base = (base or "").strip()
    if base and "://" not in base:
        base = "http://" + base
    return base


# ────────────────────────────── HTTP helpers ───────────────────────────────
# Plain urllib so the module is importable and unit-testable headless. The base
# may be a bare host or an /api/v1 URL — _origin() reduces it to scheme://host
# and we append the fleet's absolute API paths.
def _req(base, path, key="", method="GET", payload=None, timeout=15):
    url = _origin(base) + path
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer %s" % key
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode(errors="replace")
    return json.loads(raw) if raw.strip() else {}


def _list_from(base, paths, key="", list_keys=("models", "data", "workers", "serving")):
    for path in paths:
        try:
            d = _req(base, path, key)
        except Exception:
            continue
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            for lk in list_keys:
                if isinstance(d.get(lk), list):
                    return d[lk]
    return []


def list_models_full(base, key=""):
    """The rich model catalog — primary_task, tasks, mmproj_bytes, size_bytes…"""
    return _list_from(base, ("/api/models", "/models"), key, ("models", "data"))


def list_serving(base, key=""):
    """Serving/placement config per model (mode swap/static, always_on, ttl…)."""
    return _list_from(base, ("/api/llm/serving", "/llm/serving"), key, ("serving", "data"))


def list_workers(base, key=""):
    """Fleet workers with health, GPU/VRAM, and currently-loaded models."""
    return _list_from(base, ("/api/llm/workers", "/llm/workers"), key, ("workers", "data"))


def list_slots(base, key=""):
    for path in ("/api/llm/slots", "/llm/slots"):
        try:
            d = _req(base, path, key)
            if isinstance(d, dict):
                return d
        except Exception:
            continue
    return {}


def load_slot(base, key, model_key):
    """Warm a model into a GPU slot (POST /api/llm/slots/load {model_key})."""
    return _req(base, "/api/llm/slots/load", key, method="POST",
                payload={"model_key": model_key}, timeout=30)


def list_routes(base, key=""):
    """The full API route table for the Schema tester."""
    origin = _origin(base)
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer %s" % key
    for url in (origin + "/endpoints?format=json",
                origin + "/api/endpoints?format=json"):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                d = json.loads(resp.read().decode(errors="replace"))
            if isinstance(d, list):
                return d
        except Exception:
            continue
    return []


def warm_keys(workers):
    """model_keys currently loaded on any worker (loaded_models + allocations)."""
    s = set()
    for w in workers or []:
        for lm in (w.get("loaded_models") or []):
            k = lm.get("model_key") if isinstance(lm, dict) else lm
            if k:
                s.add(k)
        for a in (w.get("allocations") or []):
            if isinstance(a, dict) and a.get("model_key"):
                s.add(a["model_key"])
    return s


# ─────────────────────────────── threads ───────────────────────────────────
class _Fetch(QThread):
    """Run fn() off the GUI thread; emit (ok, result-or-error-message)."""
    done = pyqtSignal(bool, object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.done.emit(True, self._fn())
        except Exception as exc:  # surface any failure to the UI, never crash
            self.done.emit(False, str(exc))


class ChatThread(QThread):
    """Stream an OpenAI-compatible chat completion; emit content deltas."""
    chunk = pyqtSignal(str)
    finished_ok = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, base, key, model, messages, temperature, max_tokens, parent=None):
        super().__init__(parent)
        self._base, self._key, self._model = base, key, model
        self._messages = messages
        self._temp, self._max = temperature, max_tokens

    def run(self):
        # Hold the generator so we can close it deterministically — that exits
        # llm_stream's `with urlopen(...)` block and releases the socket as soon
        # as run() returns, instead of waiting for GC. (A read already blocked on
        # a silent socket still can't be aborted from here — Stop takes effect at
        # the next streamed line; a warm model's first token is near-instant.)
        gen = llm_stream(self._base, self._messages, api_key=self._key,
                         model=self._model, temperature=self._temp,
                         max_tokens=self._max)
        try:
            for piece in gen:
                if self.isInterruptionRequested():
                    break
                self.chunk.emit(piece)
            self.finished_ok.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            try:
                gen.close()
            except Exception:
                pass


# ──────────────────────────────── the tab ──────────────────────────────────
class hugpyTab(QWidget):
    def __init__(self, parent=None, **_ignored):
        super().__init__(parent)
        self._models = []
        self._serving = {}       # model_key -> serving entry
        self._warm = set()       # model_keys currently loaded on a worker
        self._by_key = {}        # model_key -> model dict
        self._sel = None         # selected model dict
        self._image_data_url = None
        self._messages = []      # chat history for the current model
        self._assistant_text = ""
        self._threads = []       # keep QThread refs alive
        self._chat = None
        self._interrupted = False
        self._all_routes = []
        self._routes_loaded = False
        self._build_ui()
        self._refresh_catalog()

    # ── construction ─────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Endpoint:"))
        self.endpoint = QComboBox()
        self.endpoint.setEditable(True)
        self.endpoint.addItems(LLM_API_CHOICES)
        self.endpoint.setCurrentText(LLM_API_DEFAULT)
        self.endpoint.setMinimumWidth(260)
        bar.addWidget(self.endpoint, 1)
        bar.addWidget(QLabel("Key:"))
        self.key = QLineEdit(LLM_API_KEY_DEFAULT)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Bearer (optional)")
        self.key.setMaximumWidth(150)
        bar.addWidget(self.key)
        self.refresh_btn = QPushButton("↻ Refresh")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        bar.addWidget(self.refresh_btn)
        root.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._build_catalog())
        self.tabs = QTabWidget()
        self._chat_tab = self._build_chat()
        self.gen_panel = GeneratePanel(get_ctx=lambda: (
            self._base(), self._key(),
            self._sel.get("model_key") if self._sel else None))
        self._fleet_tab = self._build_fleet()
        self._schema_tab = self._build_schema()
        self.tabs.addTab(self._chat_tab, "Chat")
        self.tabs.addTab(self.gen_panel, "Generate")
        self.tabs.addTab(self._fleet_tab, "Fleet")
        self.tabs.addTab(self._schema_tab, "Schema")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        split.addWidget(self.tabs)
        split.setSizes([360, 740])
        root.addWidget(split, 1)

        self.status = QLabel("Ready.")
        root.addWidget(self.status)

    def _build_catalog(self):
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel("Models"))
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("filter by name…")
        self.filter.textChanged.connect(self._apply_filter)
        lay.addWidget(self.filter)
        self.task_filter = QComboBox()
        self.task_filter.addItem("All tasks")
        self.task_filter.currentTextChanged.connect(self._apply_filter)
        lay.addWidget(self.task_filter)
        self.catalog = QTableWidget(0, 4)
        self.catalog.setHorizontalHeaderLabels(["Model", "Task", "Size", "Serving"])
        self.catalog.verticalHeader().setVisible(False)
        self.catalog.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.catalog.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.catalog.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.catalog.horizontalHeader().setStretchLastSection(True)
        self.catalog.setColumnWidth(0, 190)
        self.catalog.setColumnWidth(1, 130)
        self.catalog.setColumnWidth(2, 70)
        self.catalog.itemSelectionChanged.connect(self._on_select)
        lay.addWidget(self.catalog, 1)
        self.catalog_count = QLabel("—")
        lay.addWidget(self.catalog_count)
        return wrap

    def _build_chat(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.chat_header = QLabel("Select a model from the catalog to begin.")
        self.chat_header.setWordWrap(True)
        self.chat_header.setStyleSheet("font-weight:bold;")
        lay.addWidget(self.chat_header)

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        # Dark text on white — the same contrast fix the Services chat needed so
        # output is never white-on-white under a dark app theme.
        self.transcript.setStyleSheet("QTextEdit { background:#ffffff; color:#1a1a1a; }")
        lay.addWidget(self.transcript, 1)

        prow = QHBoxLayout()
        prow.addWidget(QLabel("System:"))
        self.system = QLineEdit()
        self.system.setPlaceholderText("optional system prompt")
        prow.addWidget(self.system, 1)
        prow.addWidget(QLabel("max_tokens:"))
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(16, 32768)
        self.max_tokens.setSingleStep(128)
        self.max_tokens.setValue(int(LLM_MAX_TOKENS))
        prow.addWidget(self.max_tokens)
        prow.addWidget(QLabel("temp:"))
        self.temp = QDoubleSpinBox()
        self.temp.setRange(0.0, 2.0)
        self.temp.setSingleStep(0.1)
        self.temp.setValue(0.2)
        prow.addWidget(self.temp)
        self.deep = QCheckBox("Deep")
        self.deep.setChecked(True)
        self.deep.setToolTip("Deep = full reasoning; off appends /no_think for a fast direct answer")
        prow.addWidget(self.deep)
        lay.addLayout(prow)

        irow = QHBoxLayout()
        self.attach_btn = QPushButton("Image…")
        self.attach_btn.setToolTip("Attach an image (vision models only)")
        self.attach_btn.clicked.connect(self._attach_image)
        self.attach_btn.setVisible(False)
        irow.addWidget(self.attach_btn)
        self.attach_label = QLabel("")
        irow.addWidget(self.attach_label)
        self.prompt = QLineEdit()
        self.prompt.setPlaceholderText("Type a message and press Enter…")
        self.prompt.returnPressed.connect(self._send)
        irow.addWidget(self.prompt, 1)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send)
        irow.addWidget(self.send_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setEnabled(False)
        irow.addWidget(self.stop_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_chat)
        irow.addWidget(self.clear_btn)
        lay.addLayout(irow)
        self._set_chat_enabled(False)
        return w

    def _build_fleet(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        b = QPushButton("↻ Refresh fleet")
        b.clicked.connect(self._refresh_fleet)
        row.addWidget(b)
        self.warm_btn = QPushButton("Warm selected model")
        self.warm_btn.setToolTip("POST /api/llm/slots/load — bring the selected model online")
        self.warm_btn.clicked.connect(self._warm_selected)
        row.addWidget(self.warm_btn)
        row.addStretch(1)
        self.slots_label = QLabel("—")
        row.addWidget(self.slots_label)
        lay.addLayout(row)

        lay.addWidget(QLabel("Workers"))
        self.workers = QTableWidget(0, 7)
        self.workers.setHorizontalHeaderLabels(
            ["Worker", "Role", "Status", "GPU", "VRAM used/total", "Loaded models", "Healthy"])
        self.workers.verticalHeader().setVisible(False)
        self.workers.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.workers.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.workers, 1)

        lay.addWidget(QLabel("Serving"))
        self.serving_tbl = QTableWidget(0, 6)
        self.serving_tbl.setHorizontalHeaderLabels(
            ["Model", "Mode", "Always-on", "Endpoint", "Ctx", "TTL(s)"])
        self.serving_tbl.verticalHeader().setVisible(False)
        self.serving_tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.serving_tbl.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.serving_tbl, 1)
        return w

    def _build_schema(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel("Full API route table from /endpoints — click a route to load "
                      "it into the client, fill any <path> params + body, then Send.")
        note.setWordWrap(True)
        lay.addWidget(note)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.route_filter = QLineEdit()
        self.route_filter.setPlaceholderText("filter routes…")
        self.route_filter.textChanged.connect(self._apply_route_filter)
        ll.addWidget(self.route_filter)
        self.routes = QListWidget()
        self.routes.itemClicked.connect(self._route_clicked)
        ll.addWidget(self.routes, 1)
        rb = QPushButton("↻ Load routes")
        rb.clicked.connect(self._refresh_routes)
        ll.addWidget(rb)
        split.addWidget(left)
        # Embed the general REST client (sibling tab) rather than reimplement it.
        from ...apiConsole import apiConsole
        self.api = apiConsole()
        split.addWidget(self.api)
        split.setSizes([300, 780])
        lay.addWidget(split, 1)
        return w

    # ── small helpers ────────────────────────────────────────────────────
    def _base(self):
        return _norm(self.endpoint.currentText().strip() or LLM_API_DEFAULT)

    def _key(self):
        return self.key.text().strip()

    def _track(self, thread):
        self._threads.append(thread)
        thread.finished.connect(lambda: self._drop_thread(thread))
        return thread

    def _drop_thread(self, thread):
        if thread in self._threads:
            self._threads.remove(thread)

    def _on_tab_changed(self, idx):
        w = self.tabs.widget(idx)
        if w is self._fleet_tab and self.workers.rowCount() == 0:
            self._refresh_fleet()
        elif w is self._schema_tab and not self._routes_loaded:
            self._refresh_routes()

    # ── catalog ──────────────────────────────────────────────────────────
    def _on_refresh_clicked(self):
        self._refresh_catalog()
        if self.tabs.currentWidget() is self._fleet_tab:
            self._refresh_fleet()

    def _refresh_catalog(self):
        base, key = self._base(), self._key()
        self.status.setText("Loading model catalog from %s…" % _origin(base))
        self.refresh_btn.setEnabled(False)

        def work():
            models = list_models_full(base, key)
            serving = list_serving(base, key)
            workers = list_workers(base, key)
            return models, serving, warm_keys(workers)

        t = _Fetch(work, self)
        t.done.connect(self._on_catalog)
        self._track(t)
        t.start()

    def _on_catalog(self, ok, result):
        self.refresh_btn.setEnabled(True)
        if not ok:
            self.status.setText("Catalog load failed: %s" % result)
            return
        models, serving, warm = result
        self._models = models or []
        self._serving = {(e.get("key") or e.get("model_name")): e
                         for e in (serving or []) if (e.get("key") or e.get("model_name"))}
        self._warm = warm or set()
        self._by_key = {m.get("model_key"): m for m in self._models if m.get("model_key")}
        tasks = sorted({primary_task(m) for m in self._models})
        cur = self.task_filter.currentText()
        self.task_filter.blockSignals(True)
        self.task_filter.clear()
        self.task_filter.addItem("All tasks")
        self.task_filter.addItems(tasks)
        idx = self.task_filter.findText(cur)
        self.task_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.task_filter.blockSignals(False)
        self._populate_catalog()
        self.status.setText("Loaded %d models (%d warm) from %s" %
                            (len(self._models), len(self._warm), _origin(self._base())))

    def _serving_cell(self, m):
        mk = m.get("model_key")
        if mk in self._warm:
            return ("● warm", _GREEN)
        e = self._serving.get(mk) or self._serving.get(m.get("name"))
        if not e:
            return ("—", _GRAY)
        if e.get("always_on") or e.get("mode") == "static":
            return ("always-on", _GREEN)
        return (str(e.get("mode") or "swap"), _ORANGE)

    def _populate_catalog(self):
        name_f = self.filter.text().strip().lower()
        task_f = self.task_filter.currentText()
        rows = []
        for m in self._models:
            nm = m.get("model_key") or m.get("name") or ""
            if name_f and name_f not in nm.lower():
                continue
            if task_f and task_f != "All tasks" and primary_task(m) != task_f:
                continue
            rows.append(m)
        self.catalog.setRowCount(0)
        self.catalog.setRowCount(len(rows))
        for i, m in enumerate(rows):
            nm = m.get("model_key") or m.get("name") or "?"
            label = ("[V] " + nm) if is_vision(m) else nm
            name_item = QTableWidgetItem(label)
            name_item.setData(Qt.ItemDataRole.UserRole, m.get("model_key"))
            self.catalog.setItem(i, 0, name_item)
            self.catalog.setItem(i, 1, QTableWidgetItem(primary_task(m)))
            self.catalog.setItem(i, 2, QTableWidgetItem(
                _fmt_gb(m.get("size_bytes") or m.get("effective_bytes"))))
            text, color = self._serving_cell(m)
            sv = QTableWidgetItem(text)
            sv.setBackground(color)
            self.catalog.setItem(i, 3, sv)
        self.catalog_count.setText("%d shown / %d total" % (len(rows), len(self._models)))

    def _apply_filter(self, *_):
        self._populate_catalog()

    def _on_select(self):
        items = self.catalog.selectedItems()
        if not items:
            return
        cell = self.catalog.item(items[0].row(), 0)
        mk = cell.data(Qt.ItemDataRole.UserRole) if cell else None
        m = self._by_key.get(mk)
        if not m:
            return
        self._sel = m
        self._messages = []
        self.transcript.clear()
        self._image_data_url = None
        self.attach_label.setText("")
        vision = is_vision(m)
        self.attach_btn.setVisible(vision)
        pt = primary_task(m)
        mod = modality(m)
        if mod == "chat":
            kind = "vision chat (image + text -> text)" if vision else "chat (text -> text)"
            self.chat_header.setText("%s   .   task: %s   .   %s" % (mk, pt, kind))
            self._set_chat_enabled(True)
            self.gen_panel.set_model(m, "other")
            self.tabs.setCurrentWidget(self._chat_tab)
            self.prompt.setFocus()
        else:
            self.chat_header.setText(
                "%s   .   task: %s\nGenerative model — configured in the Generate tab."
                % (mk, pt))
            self._set_chat_enabled(False)
            self.gen_panel.set_model(m, mod)
            self.tabs.setCurrentWidget(self.gen_panel)

    def _set_chat_enabled(self, on):
        self.prompt.setEnabled(on)
        self.send_btn.setEnabled(on)

    # ── chat ─────────────────────────────────────────────────────────────
    def _append_header(self, role):
        color = "#0a7a3a" if role == "You" else "#0b5cad"
        cur = self.transcript.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertHtml("<p style='margin:8px 0 2px 0;'><b style='color:%s;'>%s:</b></p>"
                       % (color, role))
        cur.insertBlock()
        self.transcript.setTextCursor(cur)
        self.transcript.ensureCursorVisible()

    def _append_body(self, text):
        cur = self.transcript.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        # Reset to the default char format so body text doesn't inherit the
        # bold/coloured format left by the role header (or a prior <p> block).
        cur.setCharFormat(QTextCharFormat())
        cur.insertText(text)
        self.transcript.setTextCursor(cur)
        self.transcript.ensureCursorVisible()

    def _send(self):
        if not self._sel or not is_chat(self._sel):
            return
        text = self.prompt.text().strip()
        if not text:
            return
        if self._chat and self._chat.isRunning():
            return
        mk = self._sel.get("model_key")
        suffix = think_suffix(self.deep.isChecked())
        if self._image_data_url:
            img = {"type": "image_url", "image_url": {"url": self._image_data_url}}
            wire = [{"type": "text", "text": text + suffix}, img]
            # History keeps a CLEAN copy (no /no_think suffix); the image stays so
            # follow-up questions still have it in context.
            hist = [{"type": "text", "text": text}, img]
            self._append_header("You")
            self._append_body(text + "   [+ image]")
        else:
            wire = text + suffix
            hist = text
            self._append_header("You")
            self._append_body(text)
        msgs = []
        sysp = self.system.text().strip()
        if sysp:
            msgs.append({"role": "system", "content": sysp})
        msgs.extend(self._messages)
        msgs.append({"role": "user", "content": wire})
        self._messages.append({"role": "user", "content": hist})
        self.prompt.clear()
        self._image_data_url = None
        self.attach_label.setText("")
        self._start_stream(mk, msgs)

    def _start_stream(self, model, messages):
        self._assistant_text = ""
        self._interrupted = False
        self._append_header("Assistant")
        self.send_btn.setEnabled(False)
        self.prompt.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status.setText("Streaming from %s…" % model)
        self._chat = ChatThread(self._base(), self._key(), model, messages,
                                self.temp.value(), self.max_tokens.value(), self)
        self._chat.chunk.connect(self._on_chunk)
        self._chat.finished_ok.connect(self._on_stream_done)
        self._chat.error.connect(self._on_stream_error)
        self._track(self._chat)
        self._chat.start()

    def _on_chunk(self, piece):
        self._assistant_text += piece
        self._append_body(piece)

    def _on_stream_done(self):
        if self._assistant_text:
            self._messages.append({"role": "assistant", "content": self._assistant_text})
        if self._interrupted:
            cur = self.transcript.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            cur.insertHtml("<i style='color:#888888;'> [stopped]</i>")
            self.transcript.setTextCursor(cur)
        self._finish_stream()
        self.status.setText("Stopped." if self._interrupted else "Done.")

    def _on_stream_error(self, msg):
        # Keep the transcript and history in sync: whatever streamed before the
        # error is already on screen, so record it as the assistant turn too.
        if self._assistant_text:
            self._messages.append({"role": "assistant", "content": self._assistant_text})
        cur = self.transcript.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertHtml("<p style='color:#a00000;'>[error: %s]</p>" % _esc(msg))
        self.transcript.setTextCursor(cur)
        self._finish_stream()
        self.status.setText("Stream error: %s" % msg)

    def _finish_stream(self):
        enabled = bool(self._sel) and is_chat(self._sel)
        self.send_btn.setEnabled(enabled)
        self.prompt.setEnabled(enabled)
        self.stop_btn.setEnabled(False)
        if enabled:
            self.prompt.setFocus()

    def _stop(self):
        if self._chat and self._chat.isRunning():
            self._interrupted = True
            self._chat.requestInterruption()
            self.status.setText("Stopping…")

    def _clear_chat(self):
        self._messages = []
        self.transcript.clear()
        self._image_data_url = None
        self.attach_label.setText("")

    def _attach_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Attach image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if not path:
            return
        try:
            from ...wireframeTab.src.vision_import import image_to_data_url
            self._image_data_url = image_to_data_url(path)
            self.attach_label.setText(os.path.basename(path))
        except Exception as exc:
            QMessageBox.warning(self, "Image", "Could not load image: %s" % exc)

    # ── fleet ────────────────────────────────────────────────────────────
    def _refresh_fleet(self):
        base, key = self._base(), self._key()
        self.status.setText("Loading fleet…")

        def work():
            return list_workers(base, key), list_serving(base, key), list_slots(base, key)

        t = _Fetch(work, self)
        t.done.connect(self._on_fleet)
        self._track(t)
        t.start()

    def _on_fleet(self, ok, result):
        if not ok:
            self.status.setText("Fleet load failed: %s" % result)
            return
        workers, serving, slots = result
        self._warm = warm_keys(workers)
        self.workers.setRowCount(0)
        self.workers.setRowCount(len(workers or []))
        for i, w in enumerate(workers or []):
            gpus = w.get("gpus") or []
            gpu = w.get("gpu") or (gpus[0].get("name") if gpus and isinstance(gpus[0], dict) else "") or "—"
            vram = "%s / %s" % (_fmt_gb(w.get("vram_used")), _fmt_gb(w.get("vram_total")))
            loaded = w.get("loaded_models") or []
            loaded_str = ", ".join(
                str(x.get("model_key") if isinstance(x, dict) else x) for x in loaded) or "—"
            status = str(w.get("status") or "—")
            healthy = bool(w.get("version_ok")) or status in ("ok", "healthy", "approved", "ready")
            vals = [w.get("name") or w.get("id") or "?", str(w.get("role") or "—"),
                    status, str(gpu)[:26], vram, loaded_str, "healthy" if healthy else "down"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if c == 6:
                    item.setBackground(_GREEN if healthy else _RED)
                self.workers.setItem(i, c, item)
        self.serving_tbl.setRowCount(0)
        self.serving_tbl.setRowCount(len(serving or []))
        for i, e in enumerate(serving or []):
            vals = [e.get("key") or e.get("model_name") or "?", str(e.get("mode") or "—"),
                    "yes" if e.get("always_on") else "no", str(e.get("endpoint") or "—"),
                    str(e.get("ctx_size") if e.get("ctx_size") is not None else "—"),
                    str(e.get("ttl_seconds") if e.get("ttl_seconds") is not None else "—")]
            for c, v in enumerate(vals):
                self.serving_tbl.setItem(i, c, QTableWidgetItem(v))
        s = slots or {}
        self.slots_label.setText("slots %s/%s · enabled=%s" % (
            len(s.get("slots") or []), s.get("slot_count", "?"), s.get("enabled", "?")))
        if self._models:
            self._populate_catalog()
        self.status.setText("Fleet: %d workers, %d serving entries."
                            % (len(workers or []), len(serving or [])))

    def _warm_selected(self):
        if not self._sel:
            self.status.setText("Select a model in the catalog first.")
            return
        mk = self._sel.get("model_key")
        base, key = self._base(), self._key()
        self.warm_btn.setEnabled(False)
        self.status.setText("Warming %s…" % mk)

        t = _Fetch(lambda: load_slot(base, key, mk), self)

        def on_done(ok, res):
            self.warm_btn.setEnabled(True)
            if not ok:
                self.status.setText("Warm failed: %s" % res)
                return
            if isinstance(res, dict) and (res.get("loaded") is False
                                          or res.get("ok") is False or res.get("error")):
                why = res.get("reason") or res.get("error") or "no free slot"
                self.status.setText("Not loaded: %s" % why)
            else:
                self.status.setText("Warm requested for %s." % mk)
            self._refresh_fleet()

        t.done.connect(on_done)
        self._track(t)
        t.start()

    # ── schema ───────────────────────────────────────────────────────────
    def _refresh_routes(self):
        base, key = self._base(), self._key()
        self.status.setText("Loading routes…")
        t = _Fetch(lambda: list_routes(base, key), self)
        t.done.connect(self._on_routes)
        self._track(t)
        t.start()

    def _on_routes(self, ok, result):
        if not ok:
            self.status.setText("Routes load failed: %s" % result)
            return
        self._all_routes = result or []
        self._routes_loaded = True
        self._render_routes()
        self.status.setText("Loaded %d routes." % len(self._all_routes))

    def _render_routes(self):
        f = self.route_filter.text().strip().lower()
        self.routes.clear()
        for r in self._all_routes:
            methods = r.get("methods") or []
            url = r.get("url") or ""
            if f and f not in url.lower() and f not in ",".join(methods).lower():
                continue
            m0 = methods[0] if methods else "GET"
            it = QListWidgetItem("%-6s %s" % (m0, url))
            it.setData(Qt.ItemDataRole.UserRole, (m0, url))
            self.routes.addItem(it)

    def _apply_route_filter(self, *_):
        self._render_routes()

    def _route_clicked(self, item):
        method, url = item.data(Qt.ItemDataRole.UserRole)
        idx = self.api.method.findText(method)
        if idx >= 0:
            self.api.method.setCurrentIndex(idx)
        self.api.url.setText(_origin(self._base()) + url)
        # Carry the Bearer key over so private/key-gated routes don't 401.
        key = self._key()
        if key:
            try:
                self.api.auth_type.setCurrentText("Bearer")
                self.api.auth_token.setText(key)
            except Exception:
                pass

    def closeEvent(self, event):
        # Don't let a running network/stream thread outlive the widget: silence
        # its signals so a late delivery can't reach a deleted slot, ask any chat
        # stream to stop, and wait briefly. Mirrors servicesTab/agent.py.
        for t in list(self._threads):
            try:
                t.blockSignals(True)
                if isinstance(t, ChatThread):
                    t.requestInterruption()
                t.wait(2000)
            except RuntimeError:
                pass
        self.gen_panel.shutdown()
        event.accept()


def start():
    """Standalone runner for manual testing outside the IDE."""
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = hugpyTab()
    w.resize(1180, 760)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    start()
