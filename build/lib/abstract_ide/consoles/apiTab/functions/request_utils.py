from ..imports import *
from .http_helpers import canonicalize_slash
from abstract_gui.QT6.imports import *
from PySide6.QtNetwork import QNetworkRequest

# === imports (be explicit to avoid mixed-bindings) ===
from PySide6.QtCore import QUrl, QUrlQuery, QByteArray
from PySide6.QtNetwork import QNetworkRequest, QNetworkAccessManager

# Optional: quick sanity guard you can keep during migration
def _assert_pyside6(obj, name="object"):
    mod = getattr(type(obj), "__module__", "")
    if not mod.startswith("PySide6."):
        raise TypeError(f"{name} from wrong module: {mod} (expected PySide6.*)")

def _mk_request(url_str: str, headers: dict[str, str]) -> QNetworkRequest:
    # Use QUrl.fromUserInput for robustness with user-entered URLs
    u = QUrl.fromUserInput(url_str)
    _assert_pyside6(u, "QUrl")
    req = QNetworkRequest(u)

    # Raw headers must be QByteArray
    for k, v in headers.items():
        if k and v is not None:
            req.setRawHeader(QByteArray(k.encode()), QByteArray(str(v).encode()))
    return req

def _apply_query(u: QUrl, params: dict) -> QUrl:
    if not params:
        return u
    q = QUrlQuery(u)
    for k, v in params.items():
        q.addQueryItem(str(k), str(v))
    u.setQuery(q)
    return u

def send_request(self):
    # --- selection & inputs ---
    sel = self.endpoints_table.selectionModel().selectedRows()
    if not sel:
        QMessageBox.warning(self, "No endpoint", "Select an endpoint row first.")
        return
    ep = self.endpoints_table.item(sel[0].row(), 0).text().strip()
    if not ep:
        QMessageBox.warning(self, "Invalid endpoint", "Empty endpoint path.")
        return

    headers = self._collect_headers()      # dict[str, str]
    kv      = self._collect_kv(self.body_table)  # dict
    method  = self.method_box.currentText().upper()

    try:
        base_url = self._build_url(ep)  # string
    except Exception as e:
        QMessageBox.warning(self, "Invalid URL", str(e))
        return

    # Ensure we’re using the proper binding for NAM
    if not hasattr(self, "_nam") or self._nam is None:
        self._nam = QNetworkAccessManager(self)

    # --- Build request (start with base url) ---
    req = _mk_request(base_url, headers)

    # --- Body handling ---
    ctype = (headers.get("Content-Type") or "").lower()
    body_bytes: QByteArray | None = None

    if method in ("POST", "PUT", "PATCH", "DELETE"):
        if "application/json" in ctype:
            body_bytes = QByteArray(json.dumps(kv).encode())
        elif "application/x-www-form-urlencoded" in ctype:
            body_bytes = QByteArray(urlencode(kv).encode())
        elif "text/plain" in ctype:
            body_bytes = QByteArray("\n".join(f"{k}={v}" for k, v in kv.items()).encode())
        else:
            # If a body exists but no explicit content-type, default to JSON
            if kv and not ctype:
                req.setRawHeader(b"Content-Type", b"application/json")
                body_bytes = QByteArray(json.dumps(kv).encode())

    # --- Dispatch (attach query params for GET) ---
    label = f"{method} {base_url}"
    self.response_output.clear()
    self._log(f"→ {label} | headers={headers} | params={kv}")

    if method == "GET":
        if kv:
            u = QUrl(req.url())          # copy current URL
            u = _apply_query(u, kv)      # append ?key=val…
            req.setUrl(u)
        reply = self._nam.get(req)

    elif method == "POST":
        reply = self._nam.post(req, body_bytes or QByteArray())

    elif method == "PUT":
        reply = self._nam.put(req, body_bytes or QByteArray())

    elif method == "PATCH":
        reply = self._nam.sendCustomRequest(req, QByteArray(b"PATCH"), body_bytes or QByteArray())

    elif method == "DELETE":
        if body_bytes:
            reply = self._nam.sendCustomRequest(req, QByteArray(b"DELETE"), body_bytes)
        else:
            reply = self._nam.deleteResource(req)

    else:
        QMessageBox.information(self, "Unsupported", f"Method {method} not supported.")
        return

    self._bind_common(reply, label)
def _on_send_response(self, txt: str, log_msg: str):
    try:
        self.response_output.setPlainText(txt)
        logging.info(log_msg)
    except RuntimeError as e:
        logging.error(f"_on_send_response RuntimeError: {e}")
    finally:
        self._thread = None

def _on_send_error(self, err: str):
    try:
        self.response_output.setPlainText(err)
        logging.error(err)
        QMessageBox.warning(self, "Request Error", err)
    except RuntimeError as e:
        logging.error(f"_on_send_error RuntimeError: {e}")
    finally:
        self._thread = None
