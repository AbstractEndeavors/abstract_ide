from __future__ import annotations

# ── explicit Qt imports for critical types to avoid binding mixups ────────────
from PySide6.QtCore import QObject, QThread, Signal as pyqtSignal, Qt
from PySide6.QtWidgets import (
    QComboBox, QListView, QSizePolicy, QMessageBox, QTextEdit
)

# keep your abstract imports; but avoid re-exported QtCore/QUrl/etc here
from abstract_gui.QT6.imports import *  # noqa: F401,F403 (safe for non-critical)
from abstract_apis import *  # getRequest, postRequest, MIME_TYPES

import json
import logging
from urllib.parse import urlencode

# ─── Configuration ────────────────────────────────────────────────────────────
PREDEFINED_BASE_URLS: list[tuple[str, str]] = [
    ("https://abstractendeavors.com", "/api"),
    ("https://clownworld.biz",        "/media"),
    ("https://typicallyoutliers.com", "/api"),
    ("https://thedailydialectics.com","/api"),
]

def _norm_prefix(p: str | None) -> str:
    p = (p or "/api").strip()
    if not p.startswith("/"): p = "/" + p
    return p.rstrip("/")

PREDEFINED_HEADERS = [
    ("Content-Type", "application/json"),
    ("Accept",       "application/json"),
    ("Authorization","Bearer "),
]
MIME_TYPES_HEADERS = MIME_TYPES  # from abstract_apis

# ─── Logging ─────────────────────────────────────────────────────────────────
try:
    from abstract_utilities import get_logFile  # preferred if available
except Exception:
    def get_logFile(name: str):
        logger = logging.getLogger(name)
        if not logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"
            ))
            logger.addHandler(h)
            logger.setLevel(logging.INFO)
        return logger

logger = get_logFile(__name__)

class QTextEditLogger(logging.Handler):
    """Pipe logs into a QTextEdit."""
    def __init__(self, widget: QTextEdit):
        super().__init__()
        self.widget = widget
        self.widget.setReadOnly(True)
        self.api_prefix = "/api"  # default; updated by detect
    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        # avoid reentrancy issues
        self.widget.append(msg)
        self.widget.ensureCursorVisible()

# ─── Widgets ─────────────────────────────────────────────────────────────────
class BoundedCombo(QComboBox):
    def __init__(self, parent=None, *, editable=False):
        super().__init__(parent)
        self.setEditable(editable)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        lv = QListView(self)
        lv.setTextElideMode(Qt.TextElideMode.ElideRight)
        lv.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setView(lv)

    def showPopup(self):
        super().showPopup()
        v = self.view()
        v.setMinimumWidth(self.width())
        v.setMaximumWidth(self.width())

# ─── URL helpers ─────────────────────────────────────────────────────────────
def build_base(base: str, prefix: str | None) -> str:
    """Join base + normalized prefix without double slashes."""
    prefix = _norm_prefix(prefix)
    return base.rstrip("/") + prefix

def build_url(base: str, prefix: str | None, path: str) -> str:
    """Join base + prefix + path (path may be with/without leading slash)."""
    root = build_base(base, prefix)
    path = (path or "").strip()
    if not path:
        return root
    if not path.startswith("/"):
        path = "/" + path
    return root + path

# ─── Threaded worker (unified) ───────────────────────────────────────────────
class RequestWorker(QObject):
    response_signal = pyqtSignal(str, str)  # (txt, log_msg)
    error_signal    = pyqtSignal(str)
    finished        = pyqtSignal()

    def __init__(self, *, method: str, url: str, headers: dict, params: dict,
                 timeout: float = 15.0, is_detect: bool = False):
        super().__init__()
        self.method   = (method or "GET").upper()
        self.url      = url
        self.headers  = headers or {}
        self.params   = params or {}
        self.timeout  = timeout
        self.is_detect = is_detect

    def _detect_prefix(self) -> str:
        """Probe common config endpoints to infer API prefix."""
        candidates = [f"{self.url}/config", f"{self.url}/__config", f"{self.url}/_meta"]
        for u in candidates:
            try:
                r = getRequest(url=u, headers=self.headers, timeout=self.timeout)
                if isinstance(r, dict):
                    val = r.get("static_url_path") or r.get("api_prefix")
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            except Exception:
                continue
        return "/api"

    def run(self):
        try:
            if self.is_detect:
                prefix = self._detect_prefix()
                self.response_signal.emit(prefix, f"API prefix detected: {prefix}")
                return
            # regular request
            if self.method == "GET":
                res = getRequest(url=self.url, headers=self.headers, data=self.params, timeout=self.timeout)
            elif self.method in ("POST", "PUT", "PATCH", "DELETE"):
                # keep your postRequest wrapper for non-GET; if you have put/patch helpers, switch here
                res = postRequest(url=self.url, headers=self.headers, data=self.params, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {self.method}")

            # normalize to text for UI
            if isinstance(res, (dict, list)):
                txt = json.dumps(res, indent=4)
                # If you previously warned about non-list but now accept dicts:
                if not isinstance(res, list):
                    logger.info("%s returned non-list (%s).", self.url, type(res).__name__)
            else:
                txt = str(res)

            self.response_signal.emit(txt, f"✔ {self.method} {self.url}")
        except Exception as ex:
            self.error_signal.emit(f"✖ Error: {ex}")
        finally:
            self.finished.emit()

def run_worker(worker: RequestWorker, on_success, on_failure):
    """Spin a QThread for the worker; wire signals; return (thread, worker)."""
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    worker.response_signal.connect(on_success)
    worker.error_signal.connect(on_failure)

    thread.start()
    return thread, worker

# ─── Example glue you can call from your widget ──────────────────────────────
def start_detect_prefix(self, base: str):
    """Detect api prefix for a given base domain; store thread to avoid GC."""
    w = RequestWorker(method="GET", url=base.rstrip("/"), headers={}, params={}, is_detect=True)
    def ok(txt: str, log_msg: str):
        logger.info(log_msg)
        # update any UI state that holds the prefix
        self.api_prefix = _norm_prefix(txt)
    def bad(err: str):
        logger.error(err)
        self.api_prefix = "/api"

    t, _ = run_worker(w, ok, bad)
    # store to prevent premature GC
    if not hasattr(self, "_threads"): self._threads = []
    self._threads.append(t)

def start_send(self, base: str, prefix: str, path: str, method: str,
               headers: dict, params: dict):
    """Send one request via worker. Keeps UI responsive."""
    url = build_url(base, prefix, path)
    # For GET, you can optionally encode params into the URL here instead of via data
    if method.upper() == "GET" and params:
        qs = urlencode(params, doseq=True)
        url = url + ("&" if "?" in url else "?") + qs

    w = RequestWorker(method=method, url=url, headers=headers, params=params, is_detect=False)

    def ok(txt: str, log_msg: str):
        try:
            self.response_out.setPlainText(txt)
        except Exception:
            pass
        logger.info(log_msg)

    def bad(err: str):
        try:
            self.response_out.setPlainText(err)
        except Exception:
            pass
        logger.error(err)
        try:
            QMessageBox.warning(self, "Request Error", err)
        except Exception:
            pass

    t, _ = run_worker(w, ok, bad)
    if not hasattr(self, "_threads"): self._threads = []
    self._threads.append(t)
