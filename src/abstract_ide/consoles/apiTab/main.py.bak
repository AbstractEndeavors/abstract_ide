
from __future__ import annotations
from abstract_gui import startConsole
# apiTab_async.py
# A brand-new non-blocking API console using QNetworkAccessManager (Qt-native async).
# No threads, no blocking I/O. Includes timeout + abort support.
import json
from typing import Optional, Dict, Tuple
from urllib.parse import urlencode
# --- Qt imports (PyQt6) -------------------------------------------------------
from PyQt6.QtCore import Qt, QUrl, QTimer, QByteArray
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QMessageBox, QMainWindow, QTableWidgetSelectionRange
)

# --- Optional: pull user’s helpers if present ---------------------------------
try:
    # Your project constants/utilities (if available)
    from abstract_utilities import get_logFile  # noqa
except Exception:  # pragma: no cover - safe fallback
    import logging
    def get_logFile(name: str):
        logger = logging.getLogger(name)
        if not logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S'))
            logger.addHandler(h)
            logger.setLevel(logging.INFO)
        return logger

logger = get_logFile(__name__)

# --- Reasonable defaults if your constants aren’t imported ---------------------
# You can replace these with your PREDEFINED_* from abstract_* if you prefer.
DEFAULT_BASES: Tuple[Tuple[str, str], ...] = (
    ("http://127.0.0.1:5000", "Local Flask"),
    ("http://localhost:8000", "Local Dev"),
)
DEFAULT_HEADERS: Tuple[Tuple[str, str], ...] = (
    ("Accept", "application/json"),
    ("Content-Type", "application/json"),
)
MIME_TYPES: Dict[str, Dict[str, str]] = {
    "json": {"json": "application/json"},
    "form": {"urlencoded": "application/x-www-form-urlencoded"},
    "text": {"plain": "text/plain"},
}

# ------------------------------------------------------------------------------
# Widget
# ------------------------------------------------------------------------------
class apiTab(QWidget):
    TIMEOUT_MS = 15000  # 15s timeout

    def __init__(self, *, bases: Optional[Tuple[Tuple[str, str], ...]] = None,
                 default_prefix: str = "/api"):
        super().__init__()
        self.setWindowTitle("API Console (async, non-blocking)")
 

        self._bases = bases or DEFAULT_BASES
        self._api_prefix = default_prefix if default_prefix.startswith("/") else f"/{default_prefix}"
        self._nam = QNetworkAccessManager(self)
        self._inflight: Optional[QNetworkReply] = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

        self._build_ui()
        self._wire()

    # ------------------------------------------------------------------ UI ----
    def _build_ui(self):
        root = QVBoxLayout(self)

        # Base URL
        root.addWidget(QLabel("Base URL:"))
        self.base_combo = QComboBox(self)
        self.base_combo.setEditable(True)
        self.base_combo.addItems([b for b, _label in self._bases])
        self.base_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        root.addWidget(self.base_combo)

        # Prefix row
        row = QHBoxLayout()
        row.addWidget(QLabel("API Prefix:"))
        self.prefix_in = QLineEdit(self._api_prefix, self)
        self.prefix_in.setPlaceholderText("/api")
        self.prefix_in.setClearButtonEnabled(True)
        row.addWidget(self.prefix_in)

        self.detect_btn = QPushButton("Detect", self)
        row.addWidget(self.detect_btn)
        root.addLayout(row)

        # Endpoints
        root.addWidget(QLabel("Endpoints (select one row):"))
        self.endpoints_table = QTableWidget(0, 2, self)
        self.endpoints_table.setHorizontalHeaderLabels(["Endpoint Path", "Methods"])
        self.endpoints_table.horizontalHeader().setStretchLastSection(True)
        self.endpoints_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.endpoints_table.setFixedHeight(220)
        root.addWidget(self.endpoints_table)

        # Method override
        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("Override Method:"))
        self.method_box = QComboBox(self)
        self.method_box.addItems(["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
        mrow.addWidget(self.method_box)
        root.addLayout(mrow)

        # Headers
        root.addWidget(QLabel("Headers (check to include; blank key+value inserts new row):"))
        self.headers_table = QTableWidget(len(DEFAULT_HEADERS) + 1, 3, self)
        self.headers_table.setHorizontalHeaderLabels(["Use", "Key", "Value"])
        self.headers_table.setFixedHeight(220)
        root.addWidget(self.headers_table)

        for i, (k, v) in enumerate(DEFAULT_HEADERS):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked)
            self.headers_table.setItem(i, 0, chk)
            self.headers_table.setItem(i, 1, QTableWidgetItem(k))
            self.headers_table.setItem(i, 2, QTableWidgetItem(v))

        # trailing empty row
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        chk.setCheckState(Qt.CheckState.Unchecked)
        last = self.headers_table.rowCount() - 1
        self.headers_table.setItem(last, 0, chk)
        self.headers_table.setItem(last, 1, QTableWidgetItem(""))
        self.headers_table.setItem(last, 2, QTableWidgetItem(""))

        # Body / query params
        root.addWidget(QLabel("Body / Query Params (key → value):"))
        self.body_table = QTableWidget(1, 2, self)
        self.body_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.body_table.setFixedHeight(220)
        self.body_table.setItem(0, 0, QTableWidgetItem(""))
        self.body_table.setItem(0, 1, QTableWidgetItem(""))
        root.addWidget(self.body_table)

        # Buttons
        brow = QHBoxLayout()
        self.fetch_btn = QPushButton(self._fetch_label(), self)
        self.send_btn = QPushButton("▶ Send", self)
        self.abort_btn = QPushButton("■ Abort", self)
        self.abort_btn.setEnabled(False)
        brow.addWidget(self.fetch_btn)
        brow.addStretch(1)
        brow.addWidget(self.send_btn)
        brow.addWidget(self.abort_btn)
        root.addLayout(brow)

        # Response + Logs
        root.addWidget(QLabel("Response:"))
        self.response_out = QTextEdit(self)
        self.response_out.setReadOnly(True)
        self.response_out.setFixedHeight(260)
        root.addWidget(self.response_out)

        root.addWidget(QLabel("Logs:"))
        self.log_out = QTextEdit(self)
        self.log_out.setReadOnly(True)
        self.log_out.setFixedHeight(160)
        root.addWidget(self.log_out)

    def _wire(self):
        self.prefix_in.textChanged.connect(self._on_prefix_changed)
        self.fetch_btn.clicked.connect(self.fetch_endpoints)
        self.send_btn.clicked.connect(self.send_request)
        self.abort_btn.clicked.connect(self.abort_request)
        self.headers_table.cellChanged.connect(self._maybe_add_header_row)
        self.body_table.cellChanged.connect(self._maybe_add_body_row)
        self.detect_btn.clicked.connect(self.detect_prefix)

    # --------------------------------------------------------------- helpers ---
    def _log(self, msg: str, level: str = "info"):
        self.log_out.append(msg)
        getattr(logger, level, logger.info)(msg)

    def _fetch_label(self) -> str:
        p = (self.prefix_in.text().strip() or "/api")
        if not p.startswith("/"):
            p = "/" + p
        return f"Fetch {p}/endpoints"

    def _on_prefix_changed(self, _txt: str):
        self.fetch_btn.setText(self._fetch_label())

    def _normalized_prefix(self) -> str:
        p = (self.prefix_in.text().strip() or "/api")
        return p if p.startswith("/") else "/" + p

    def _maybe_add_header_row(self, row: int, _col: int):
        last = self.headers_table.rowCount() - 1
        if row != last:
            return
        key_item = self.headers_table.item(row, 1)
        val_item = self.headers_table.item(row, 2)
        if (key_item and key_item.text().strip()) or (val_item and val_item.text().strip()):
            self.headers_table.blockSignals(True)
            self.headers_table.insertRow(last + 1)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            self.headers_table.setItem(last + 1, 0, chk)
            self.headers_table.setItem(last + 1, 1, QTableWidgetItem(""))
            self.headers_table.setItem(last + 1, 2, QTableWidgetItem(""))
            self.headers_table.blockSignals(False)

    def _maybe_add_body_row(self, row: int, _col: int):
        last = self.body_table.rowCount() - 1
        key_item = self.body_table.item(row, 0)
        val_item = self.body_table.item(row, 1)
        if row == last and ((key_item and key_item.text().strip()) or (val_item and val_item.text().strip())):
            self.body_table.blockSignals(True)
            self.body_table.insertRow(last + 1)
            self.body_table.setItem(last + 1, 0, QTableWidgetItem(""))
            self.body_table.setItem(last + 1, 1, QTableWidgetItem(""))
            self.body_table.blockSignals(False)

    def _collect_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        for r in range(self.headers_table.rowCount()):
            chk = self.headers_table.item(r, 0)
            if not chk or chk.checkState() != Qt.CheckState.Checked:
                continue
            key_item = self.headers_table.item(r, 1)
            val_item = self.headers_table.item(r, 2)
            key = key_item.text().strip() if key_item else ""
            val = val_item.text().strip() if val_item else ""
            if val and not key:
                key = "Content-Type"
                if key_item is None:
                    self.headers_table.setItem(r, 1, QTableWidgetItem(key))
                else:
                    key_item.setText(key)
            if key:
                headers[key] = val
        return headers

    def _collect_kv(self, table: QTableWidget) -> Dict[str, str]:
        data: Dict[str, str] = {}
        for r in range(table.rowCount()):
            k = table.item(r, 0)
            if not k or not k.text().strip():
                continue
            v = table.item(r, 1)
            data[k.text().strip()] = v.text().strip() if v else ""
        return data

    def _build_url(self, ep: str) -> str:
        base = (self.base_combo.currentText().strip().rstrip('/'))
        if not base:
            raise ValueError("Base URL is empty.")
        pref = self._normalized_prefix().rstrip('/')
        ep = ep.strip()
        ep = ep if ep.startswith('/') else '/' + ep
        return f"{base}{pref}{ep}"

    # ---------------------------------------------------------- network flow ---
    def _start_timeout(self):
        self._timer.start(self.TIMEOUT_MS)
        self.abort_btn.setEnabled(True)
        QApplication.setOverrideCursor(Qt.CursorShape.BusyCursor)

    def _stop_timeout(self):
        self._timer.stop()
        self.abort_btn.setEnabled(False)
        QApplication.restoreOverrideCursor()

    def _bind_common(self, reply: QNetworkReply, label: str):
        self._inflight = reply
        reply.finished.connect(lambda: self._on_finished(reply, label))
        reply.errorOccurred.connect(lambda _err: self._on_error(reply, label))
        self._start_timeout()

    def _on_timeout(self):
        if self._inflight:
            self._log("⏳ Request timed out; aborting.", "warning")
            self._inflight.abort()
        self._stop_timeout()

    def abort_request(self):
        if self._inflight:
            self._log("■ Abort requested by user.", "warning")
            self._inflight.abort()

    def _on_finished(self, reply: QNetworkReply, label: str):
        self._stop_timeout()
        if reply.isFinished() and reply.error() == QNetworkReply.NetworkError.NoError:
            data = bytes(reply.readAll())
            text = data.decode(errors="replace")
            # try pretty JSON
            try:
                obj = json.loads(text)
                text = json.dumps(obj, indent=2)
            except Exception:
                pass
            self.response_out.setPlainText(text)
            self._log(f"✔ {label}")
        reply.deleteLater()
        self._inflight = None

    def _on_error(self, reply: QNetworkReply, label: str):
        self._stop_timeout()
        err = reply.error()
        msg = reply.errorString()
        self.response_out.setPlainText(f"✖ {label}\n{err}: {msg}")
        self._log(f"✖ {label} — {err}: {msg}", "error")
        reply.deleteLater()
        self._inflight = None

    # ------------------------------------------------------------- actions ----
    def fetch_endpoints(self):
        """GET {base}{prefix}/endpoints -> list[[path, methods], ...]"""
        try:
            url = self._build_url("/endpoints")
        except Exception as e:
            QMessageBox.warning(self, "Invalid URL", str(e))
            return

        req = QNetworkRequest(QUrl(url))
        self._log(f"→ GET {url}")
        reply = self._nam.get(req)
        self._bind_common(reply, f"GET {url}")

        # Also populate table when finished (if parseable)
        def after():
            if reply.error() != QNetworkReply.NetworkError.NoError:
                return
            raw = bytes(reply.readAll())
            try:
                data = json.loads(raw.decode(errors="replace"))
            except Exception:
                return
            if isinstance(data, list):
                self._populate_endpoints(data)

        reply.finished.connect(after)

    def _populate_endpoints(self, lst):
        self.endpoints_table.setRowCount(0)
        for i, item in enumerate(lst):
            # Accept either ("path", "METHODS") or {"path":..., "methods":...}
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                path, methods = item[0], item[1]
            elif isinstance(item, dict):
                path, methods = item.get("path", ""), item.get("methods", "")
            else:
                continue
            r = self.endpoints_table.rowCount()
            self.endpoints_table.insertRow(r)
            self.endpoints_table.setItem(r, 0, QTableWidgetItem(str(path)))
            self.endpoints_table.setItem(r, 1, QTableWidgetItem(str(methods)))

        # Select first row automatically to speed testing
        if self.endpoints_table.rowCount():
            self.endpoints_table.setRangeSelected(
                QTableWidgetSelectionRange(0, 0, 0, 1), True
            )

    def send_request(self):
        sel = self.endpoints_table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.warning(self, "No endpoint", "Select an endpoint row first.")
            return
        ep = self.endpoints_table.item(sel[0].row(), 0).text().strip()
        if not ep:
            QMessageBox.warning(self, "Invalid endpoint", "Empty endpoint path.")
            return

        headers = self._collect_headers()
        kv = self._collect_kv(self.body_table)
        method = self.method_box.currentText().upper()

        try:
            url = self._build_url(ep)
        except Exception as e:
            QMessageBox.warning(self, "Invalid URL", str(e))
            return

        req = QNetworkRequest(QUrl(url))
        for k, v in headers.items():
            req.setRawHeader(QByteArray(k.encode()), QByteArray(v.encode()))

        self.response_out.clear()
        label = f"{method} {url}"
        self._log(f"→ {label} | headers={headers} | params={kv}")

        # Body formatting by header
        ctype = headers.get("Content-Type", "").lower()
        body_bytes: Optional[QByteArray] = None
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            if "application/json" in ctype:
                body_bytes = QByteArray(json.dumps(kv).encode())
            elif "application/x-www-form-urlencoded" in ctype:
                body_bytes = QByteArray(urlencode(kv).encode())
            elif "text/plain" in ctype:
                body_bytes = QByteArray("\n".join(f"{k}={v}" for k, v in kv.items()).encode())
            else:
                # default to JSON if body exists without content-type
                if kv and not ctype:
                    req.setRawHeader(b"Content-Type", b"application/json")
                    body_bytes = QByteArray(json.dumps(kv).encode())

        # Dispatch
        if method == "GET":
            # For GET, append query string
            if kv:
                u = QUrl(url)
                q = u.query()
                q_extra = urlencode(kv)
                u.setQuery(q + ("&" if q else "") + q_extra)
                req.setUrl(u)
            reply = self._nam.get(req)
        elif method == "POST":
            reply = self._nam.post(req, body_bytes or QByteArray())
        elif method == "PUT":
            reply = self._nam.put(req, body_bytes or QByteArray())
        elif method == "PATCH":
            # Qt lacks native PATCH helper; use custom verb
            reply = self._nam.sendCustomRequest(req, QByteArray(b"PATCH"), body_bytes or QByteArray())
        elif method == "DELETE":
            # DELETE may carry a body; Qt supports sendCustomRequest
            if body_bytes:
                reply = self._nam.sendCustomRequest(req, QByteArray(b"DELETE"), body_bytes)
            else:
                reply = self._nam.deleteResource(req)
        else:
            QMessageBox.information(self, "Unsupported", f"Method {method} not supported.")
            return

        self._bind_common(reply, label)

    def detect_prefix(self):
        """Try /config, /__config, /_meta for {'static_url_path' or 'api_prefix'}."""
        base = self.base_combo.currentText().strip().rstrip("/")
        if not base:
            QMessageBox.warning(self, "Invalid base URL", "Provide a base URL first.")
            return
        candidates = [f"{base}/config", f"{base}/__config", f"{base}/_meta"]
        self._log(f"→ Detecting prefix from {candidates}")

        # simple chain: issue the first; on finish try next if not found
        self._detect_chain = list(candidates)  # keep state
        self._detect_try_next()

    def _detect_try_next(self):
        if not self._detect_chain:
            self._log("⚠ No prefix detected; using /api", "warning")
            self.prefix_in.setText("/api")
            return
        url = self._detect_chain.pop(0)
        req = QNetworkRequest(QUrl(url))
        reply = self._nam.get(req)
        self._bind_common(reply, f"GET {url}")

        def after():
            if reply.error() == QNetworkReply.NetworkError.NoError:
                raw = bytes(reply.readAll())
                try:
                    j = json.loads(raw.decode(errors="replace"))
                except Exception:
                    self._detect_try_next()
                    return
                val = j.get("static_url_path") or j.get("api_prefix")
                if isinstance(val, str) and val.strip():
                    p = val.strip()
                    if not p.startswith("/"):
                        p = "/" + p
                    self.prefix_in.setText(p)
                    self._log(f"✓ Detected prefix: {p}")
                    return
            self._detect_try_next()

        reply.finished.connect(after)

    # ---------------------------------------------------------- lifecycle -----
    def closeEvent(self, event: QCloseEvent) -> None:
        if self._inflight and self._inflight.isRunning():
            self._inflight.abort()
        event.accept()



