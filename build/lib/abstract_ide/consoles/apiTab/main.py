
from __future__ import annotations
import sys
import json
import logging
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
    QMessageBox, QMainWindow, QTableWidgetSelectionRange,QCheckBox
)
from PyQt6.QtWidgets import QSizePolicy, QSplitter
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


MIME_TYPES: Dict[str, Dict[str, str]] = {
    "json": {"json": "application/json"},
    "form": {"urlencoded": "application/x-www-form-urlencoded"},
    "text": {"plain": "text/plain"},
}
DEFAULT_BASES: Tuple[Tuple[str, str], ...] = (
    ("https://abstractendeavors.com", "abstractendeavors"),
    ("https://clownworld.biz", "clownworld"),
    ("https://typicallyoutliers.com", "typicallyoutliers"),
    ("https://thedailydialectics.com", "thedailydialectics"),
    ("http://127.0.0.1:5000", "Local Flask"),
    ("http://localhost:8000", "Local Dev"),
)
DEFAULT_HEADERS: Tuple[Tuple[str, str], ...] = (
    ("Content-Type", "application/json"),
    ("Accept", "application/json"),
    ("Authorization", "Bearer "),
)
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
        self.endpoints_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.endpoints_table)


        # Method override
        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("Override Method:"))
        self.method_box = QComboBox(self)
        self.method_box.addItems(["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
        mrow.addWidget(self.method_box)
        root.addLayout(mrow)
        brow = QHBoxLayout()
        self.fetch_btn = QPushButton(self._fetch_label(), self)
        self.prefill_btn = QPushButton("Prefill from Help", self)   # NEW
        self.help_toggle = QCheckBox("Send help=1 on requests")     # Optional

        self.send_btn = QPushButton("▶ Send", self)
        self.abort_btn = QPushButton("■ Abort", self)
        self.abort_btn.setEnabled(False)

        brow.addWidget(self.fetch_btn)
        brow.addWidget(self.fetch_btn)
        brow.addWidget(self.prefill_btn)          # NEW
        brow.addWidget(self.help_toggle)          # Optional
        brow.addStretch(1)
        # Buttons


        brow.addWidget(self.send_btn)
        brow.addWidget(self.abort_btn)
        root.addLayout(brow)
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
        self.headers_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Response + Logs inside a splitter so user can resize
        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Vertical)



        # Body / query params
        root.addWidget(QLabel("Body / Query Params (key → value):"))
        self.body_table = QTableWidget(1, 2, self)
        self.body_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.body_table.setFixedHeight(220)
        self.body_table.setItem(0, 0, QTableWidgetItem(""))
        self.body_table.setItem(0, 1, QTableWidgetItem(""))
        self.body_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.body_table)



        # Response + Logs
        root.addWidget(QLabel("Response:"))
        self.response_out = QTextEdit(self)
        self.response_out.setReadOnly(True)
        self.response_out.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root.addWidget(self.response_out)

        root.addWidget(QLabel("Logs:"))
        self.log_out = QTextEdit(self)
        self.log_out.setReadOnly(True)
        self.log_out.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.log_out)

        splitter.addWidget(self.response_out)
        splitter.addWidget(self.log_out)
        splitter.setStretchFactor(0, 3)  # response 3x bigger
        splitter.setStretchFactor(1, 1)  # logs smaller

        root.addWidget(QLabel("Response + Logs:"))
        root.addWidget(splitter)
    def _wire(self):
        self.prefix_in.textChanged.connect(self._on_prefix_changed)
        self.fetch_btn.clicked.connect(self.fetch_endpoints)
        self.send_btn.clicked.connect(self.send_request)
        self.abort_btn.clicked.connect(self.abort_request)
        self.headers_table.cellChanged.connect(self._maybe_add_header_row)
        self.body_table.cellChanged.connect(self._maybe_add_body_row)
        self.detect_btn.clicked.connect(self.detect_prefix)
        self.prefill_btn.clicked.connect(self.prefill_help)  # NEW
    # --------------------------------------------------------------- helpers ---
    def _log(self, msg: str, level: str = "info"):
        self.log_out.append(msg)
        getattr(logger, level, logger.info)(msg)
    def _clear_body_and_insert(self, rows: list[tuple[str, str]]):
        self.body_table.blockSignals(True)
        self.body_table.setRowCount(0)
        for k, v in rows:
            r = self.body_table.rowCount()
            self.body_table.insertRow(r)
            self.body_table.setItem(r, 0, QTableWidgetItem(k))
            self.body_table.setItem(r, 1, QTableWidgetItem(v))
        # trailing blank row
        r = self.body_table.rowCount()
        self.body_table.insertRow(r)
        self.body_table.setItem(r, 0, QTableWidgetItem(""))
        self.body_table.setItem(r, 1, QTableWidgetItem(""))
        self.body_table.blockSignals(False)
    def prefill_help(self):
        ep = self._selected_endpoint_path()
        if not ep:
            QMessageBox.warning(self, "No endpoint", "Select an endpoint row first.")
            return
        try:
            # append ?help=1 to the endpoint path for schema
            # (your server could also accept POST {"help":true}; adjust if needed)
            help_ep = ep
            if "?" in help_ep:
                help_ep += "&help=1"
            else:
                help_ep += "?help=1"

            url = self._build_url(help_ep)
        except Exception as e:
            QMessageBox.warning(self, "Invalid URL", str(e))
            return

        req = QNetworkRequest(QUrl(url))
        self._log(f"→ GET {url} (prefill help)")
        reply = self._nam.get(req)
        self._bind_common(reply, f"GET {url}")

        def after():
            if reply.error() != QNetworkReply.NetworkError.NoError:
                return
            raw = bytes(reply.readAll())
            try:
                data = json.loads(raw.decode(errors="replace"))
            except Exception:
                return
            if isinstance(data, dict):
                # show doc for context (optional)
                self._maybe_show_doc(data)
                rows = self._rows_from_help_schema(data)
                if rows:
                    self._clear_body_and_insert(rows)
                    self._log("✓ Prefilled params from help")
        reply.finished.connect(after)
    def _selected_endpoint_path(self) -> str | None:
        sel = self.endpoints_table.selectionModel().selectedRows()
        if not sel:
            return None
        path = self.endpoints_table.item(sel[0].row(), 0)
        return path.text().strip() if path else None

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
    def _maybe_show_doc(self, obj: dict):
        doc = None
        if "doc" in obj and isinstance(obj["doc"], str):
            doc = obj["doc"]
        elif len(obj) == 1 and isinstance(next(iter(obj.values())), dict):
            inner = next(iter(obj.values()))
            doc = inner.get("doc")
        if doc:
            self.response_out.setPlainText(doc.strip())
    def _rows_from_help_schema(self, obj: dict) -> list[tuple[str, str]]:
        """
        Accepts formats like:
        {
          "analyze_visible_surface": {
            "doc": "...",
            "params": [{"name":"altitude_step","default":200.0}, ...]
          }
        }
        or directly {"doc": ..., "params":[...]}
        """
        # unwrap if top-level is {funcName: {...}}
        if "params" not in obj and len(obj) == 1 and isinstance(next(iter(obj.values())), dict):
            obj = next(iter(obj.values()))

        rows: list[tuple[str, str]] = []
        params = obj.get("params") or []
        for p in params:
            name = str(p.get("name", "")).strip()
            if not name:
                continue
            default = p.get("default", "")
            # render default as string safely
            if isinstance(default, (dict, list)):
                val = json.dumps(default)
            elif default is None:
                val = ""
            else:
                val = str(default)
            rows.append((name, val))
        return rows
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

    def _bind_common(self, reply: QNetworkReply, label: str, after=None):
        """
        Bind common handlers; optionally run `after(parsed_json)` exactly once
        after the reply is fully read. `after` receives:
           - parsed_obj (dict/list/None) from JSON parse (None if not JSON)
           - raw_text (str) full decoded payload
        """
        self._inflight = reply
        # stash the optional callback on the reply itself
        reply.setProperty(b"_after_cb", after)
        reply.setProperty(b"_label", label)
        reply.finished.connect(lambda: self._on_finished(reply))
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

    def _on_finished(self, reply: QNetworkReply):
        self._stop_timeout()
        label = reply.property(b"_label") or ""
        after = reply.property(b"_after_cb")

        if reply.isFinished() and reply.error() == QNetworkReply.NetworkError.NoError:
            # read payload ONCE
            data = bytes(reply.readAll())
            text = data.decode(errors="replace")

            # try parse JSON (don’t throw)
            parsed = None
            try:
                parsed = json.loads(text)
                pretty = json.dumps(parsed, indent=2)
                self.response_out.setPlainText(pretty)
            except Exception:
                self.response_out.setPlainText(text)

            self._log(f"✔ {label}")

            # if a callback was registered, hand over parsed + raw text
            if callable(after):
                try:
                    after(parsed, text)
                except Exception as e:
                    self._log(f"after() callback error: {e}", "error")
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
    def fetch_endpoints(self):
        """GET {base}{prefix}/endpoints -> list[[path, methods], ...] and populate table."""
        try:
            url = self._build_url("/endpoints")
        except Exception as e:
            QMessageBox.warning(self, "Invalid URL", str(e))
            return

        req = QNetworkRequest(QUrl(url))
        self._log(f"→ GET {url}")
        reply = self._nam.get(req)

        # define how to populate when the JSON arrives
        def _after(parsed, _raw_text):
            if isinstance(parsed, list):
                self._populate_endpoints(parsed)
            elif isinstance(parsed, dict) and "endpoints" in parsed and isinstance(parsed["endpoints"], list):
                self._populate_endpoints(parsed["endpoints"])
            # else: leave the response text as-is, no table update

        # bind with after-callback so body is read only once
        self._bind_common(reply, f"GET {url}", after=_after)

    # ------------------------------------------------------------- actions ----
    # ── network actions (sync via abstract_apis) ─────────────────────────
    def fetch_remote_endpoints(self):
        base = self.base_combo.currentText().rstrip('/')
        url = f"{base}/api/endpoints"
        self.log_output.clear()
        logging.info(f"Fetching remote endpoints from {url}")
        try:
            data = getRequest(url=url)
            if isinstance(data, list):
                self._populate_endpoints(data)
                logging.info("✔ Remote endpoints loaded")
            else:
                logging.warning("/api/endpoints returned non-list, ignoring")
        except Exception as e:
            logging.error(f"Failed to fetch endpoints: {e}")
            QMessageBox.warning(self, "Fetch Error", str(e))

    def _populate_endpoints(self, lst):
        self.endpoints_table.clearContents()
        self.endpoints_table.setRowCount(len(lst))
        for i, item in enumerate(lst):
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                path, methods = item[0], item[1]
            elif isinstance(item, dict):
                path, methods = item.get("path", ""), item.get("methods", "")
            else:
                path, methods = str(item), ""
            self.endpoints_table.setItem(i, 0, QTableWidgetItem(path))
            self.endpoints_table.setItem(i, 1, QTableWidgetItem(methods))

    def on_endpoint_selected(self, row: int, _col: int):
        ep = self.endpoints_table.item(row, 0).text()
        cfg = self.config_cache.get(ep, {})
        # restore method
        if 'method' in cfg:
            self.method_box.setCurrentText(cfg['method'])
        # restore headers
        for r in range(self.headers_table.rowCount()):
            chk = self.headers_table.item(r, 0)
            key_item = self.headers_table.item(r, 1)
            if not chk or not key_item:
                continue
            k = key_item.text()
            if k in cfg.get('headers', {}):
                chk.setCheckState(Qt.CheckState.Checked)
                self.headers_table.setItem(r, 2, QTableWidgetItem(cfg['headers'][k]))
            else:
                chk.setCheckState(Qt.CheckState.Unchecked)
        # restore params
        self.body_table.blockSignals(True)
        self.body_table.setRowCount(0)
        for k, v in cfg.get('params', {}).items():
            idx = self.body_table.rowCount()
            self.body_table.insertRow(idx)
            self.body_table.setItem(idx, 0, QTableWidgetItem(k))
            self.body_table.setItem(idx, 1, QTableWidgetItem(v))
        # ensure one blank editable row
        idx = self.body_table.rowCount()
        self.body_table.insertRow(idx)
        self.body_table.setItem(idx, 0, QTableWidgetItem(""))
        self.body_table.setItem(idx, 1, QTableWidgetItem(""))
        self.body_table.blockSignals(False)

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
        if self.help_toggle.isChecked():
            kv = dict(kv)  # copy
            kv["help"] = 1
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
            req = QNetworkRequest(QUrl(self._build_url(ep)))
            req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            reply = self._nam.post(req, QByteArray(json.dumps({"help": True}).encode()))
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


