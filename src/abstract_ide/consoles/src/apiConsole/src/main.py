#!/usr/bin/env python3
"""
apiConsole — a blank, general-purpose REST client tab.

No presets, no forced /api prefix, no site list: you type a full URL and drive
every part of the request yourself (method, query params, headers, body, auth)
and inspect the full response (status, timing, size, headers, pretty/raw body).
Qt-native async (QNetworkAccessManager) so the UI never blocks; a per-session
history lets you revisit and re-fire calls.
"""
import base64
import json

from PyQt6.QtCore import Qt, QUrl, QUrlQuery, QByteArray, QElapsedTimer
from PyQt6.QtGui import QColor
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QSplitter,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
CONTENT_TYPES = ["", "application/json", "application/x-www-form-urlencoded",
                 "text/plain", "text/xml", "application/xml", "multipart/form-data"]


def _fmt_size(n):
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%.1f KB" % (n / 1024.0)
    return "%.1f MB" % (n / (1024.0 * 1024.0))


def _looks_json(text):
    return text.lstrip()[:1] in ("{", "[")


def _header_value(reply, name_lower):
    for name, value in reply.rawHeaderPairs():
        if bytes(name).lower() == name_lower:
            return bytes(value).decode(errors="replace")
    return ""


class KVTable(QTableWidget):
    """An on/key/value editor with an always-present blank row to type into."""

    def __init__(self):
        super().__init__(0, 3)
        self.setHorizontalHeaderLabels(["", "Key", "Value"])
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 26)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self._add_blank()
        self.cellChanged.connect(self._on_change)

    def _add_blank(self):
        r = self.rowCount()
        self.insertRow(r)
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        chk.setCheckState(Qt.CheckState.Checked)
        self.setItem(r, 0, chk)
        self.setItem(r, 1, QTableWidgetItem(""))
        self.setItem(r, 2, QTableWidgetItem(""))

    def _on_change(self, row, col):
        last = self.rowCount() - 1
        if row == last and col in (1, 2):
            k = self.item(last, 1).text() if self.item(last, 1) else ""
            v = self.item(last, 2).text() if self.item(last, 2) else ""
            if k or v:
                self.blockSignals(True)
                self._add_blank()
                self.blockSignals(False)

    def remove_selected(self):
        for r in sorted({i.row() for i in self.selectedIndexes()}, reverse=True):
            if r != self.rowCount() - 1:
                self.removeRow(r)
        if self.rowCount() == 0:
            self._add_blank()

    def pairs(self):
        out = []
        for r in range(self.rowCount()):
            chk = self.item(r, 0)
            k = self.item(r, 1).text().strip() if self.item(r, 1) else ""
            v = self.item(r, 2).text() if self.item(r, 2) else ""
            if k and chk and chk.checkState() == Qt.CheckState.Checked:
                out.append((k, v))
        return out

    def set_pairs(self, pairs):
        self.blockSignals(True)
        self.setRowCount(0)
        for k, v in pairs:
            r = self.rowCount()
            self.insertRow(r)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked)
            self.setItem(r, 0, chk)
            self.setItem(r, 1, QTableWidgetItem(k))
            self.setItem(r, 2, QTableWidgetItem(v))
        self._add_blank()
        self.blockSignals(False)


class apiConsole(QWidget):
    def __init__(self, parent=None, **_ignored):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._reply = None
        self._timer = QElapsedTimer()
        self._history = []
        self._current = {}
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        self.method = QComboBox(); self.method.addItems(METHODS); self.method.setFixedWidth(90)
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://…   (full URL — no prefix assumed)")
        self.url.returnPressed.connect(self.send)
        self.send_btn = QPushButton("Send"); self.send_btn.clicked.connect(self.send)
        self.abort_btn = QPushButton("Abort"); self.abort_btn.clicked.connect(self._abort)
        self.abort_btn.setEnabled(False)
        top.addWidget(self.method); top.addWidget(self.url, 1)
        top.addWidget(self.send_btn); top.addWidget(self.abort_btn)
        root.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)

        hist_wrap = QWidget(); hl = QVBoxLayout(hist_wrap); hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(QLabel("History"))
        self.history = QListWidget(); self.history.itemClicked.connect(self._load_history)
        hl.addWidget(self.history)
        clr = QPushButton("Clear history"); clr.clicked.connect(self._clear_history)
        hl.addWidget(clr)
        split.addWidget(hist_wrap)

        rv = QSplitter(Qt.Orientation.Vertical)
        req_tabs = QTabWidget()
        self.params = KVTable(); req_tabs.addTab(self._with_rowbtns(self.params), "Params")
        self.headers = KVTable(); req_tabs.addTab(self._with_rowbtns(self.headers), "Headers")
        req_tabs.addTab(self._build_body_tab(), "Body")
        req_tabs.addTab(self._build_auth_tab(), "Auth")
        rv.addWidget(req_tabs)
        rv.addWidget(self._build_response())
        rv.setSizes([260, 380])
        split.addWidget(rv)
        split.setSizes([200, 900])
        root.addWidget(split, 1)

        self.status = QLabel("Ready.")
        root.addWidget(self.status)

    def _with_rowbtns(self, table):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(table)
        row = QHBoxLayout()
        rm = QPushButton("Remove selected"); rm.clicked.connect(table.remove_selected)
        row.addStretch(1); row.addWidget(rm)
        lay.addLayout(row)
        return w

    def _build_body_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        row = QHBoxLayout()
        row.addWidget(QLabel("Content-Type:"))
        self.ctype = QComboBox(); self.ctype.setEditable(True); self.ctype.addItems(CONTENT_TYPES)
        row.addWidget(self.ctype, 1)
        fmt = QPushButton("Format JSON"); fmt.clicked.connect(self._format_json)
        row.addWidget(fmt)
        lay.addLayout(row)
        self.body = QPlainTextEdit()
        self.body.setPlaceholderText("Raw request body (JSON, form, xml, …). Empty = no body.")
        lay.addWidget(self.body)
        return w

    def _build_auth_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        row = QHBoxLayout()
        row.addWidget(QLabel("Auth:"))
        self.auth_type = QComboBox(); self.auth_type.addItems(["None", "Bearer", "Basic"])
        self.auth_type.currentTextChanged.connect(self._auth_changed)
        row.addWidget(self.auth_type); row.addStretch(1)
        lay.addLayout(row)
        self.auth_token = QLineEdit(); self.auth_token.setPlaceholderText("token")
        self.auth_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.auth_user = QLineEdit(); self.auth_user.setPlaceholderText("username")
        self.auth_pass = QLineEdit(); self.auth_pass.setPlaceholderText("password")
        self.auth_pass.setEchoMode(QLineEdit.EchoMode.Password)
        for wdg in (self.auth_token, self.auth_user, self.auth_pass):
            lay.addWidget(wdg)
        lay.addStretch(1)
        self._auth_changed("None")
        return w

    def _auth_changed(self, kind):
        self.auth_token.setVisible(kind == "Bearer")
        self.auth_user.setVisible(kind == "Basic")
        self.auth_pass.setVisible(kind == "Basic")

    def _build_response(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0)
        self.resp_status = QLabel("—"); self.resp_status.setStyleSheet("font-weight:bold;")
        lay.addWidget(self.resp_status)
        tabs = QTabWidget()
        self.resp_body = QPlainTextEdit(); self.resp_body.setReadOnly(True)
        self.resp_body.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        tabs.addTab(self.resp_body, "Body")
        self.resp_headers = QTableWidget(0, 2)
        self.resp_headers.setHorizontalHeaderLabels(["Header", "Value"])
        self.resp_headers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.resp_headers.verticalHeader().setVisible(False)
        tabs.addTab(self.resp_headers, "Headers")
        lay.addWidget(tabs)
        return w

    # ── request build + send ─────────────────────────────────────────────
    def _format_json(self):
        try:
            self.body.setPlainText(json.dumps(json.loads(self.body.toPlainText()), indent=2))
        except Exception as exc:
            self.status.setText("Not valid JSON: %s" % exc)

    def _effective_url(self):
        url = QUrl(self.url.text().strip())
        pairs = self.params.pairs()
        if pairs:
            q = QUrlQuery(url.query())
            for k, v in pairs:
                q.addQueryItem(k, v)
            url.setQuery(q)
        return url

    def send(self):
        if self._reply is not None:
            return
        if not self.url.text().strip():
            self.status.setText("Enter a URL first.")
            return
        url = self._effective_url()
        if not url.isValid() or not url.scheme():
            self.status.setText("Invalid URL (include http:// or https://).")
            return
        req = QNetworkRequest(url)
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        req.setTransferTimeout(30000)

        header_pairs = list(self.headers.pairs())
        header_keys = {k.lower() for k, _ in header_pairs}
        method = self.method.currentText()
        body_txt = self.body.toPlainText()
        body = QByteArray(body_txt.encode()) if body_txt else QByteArray()

        ct = self.ctype.currentText().strip()
        if body_txt and ct and "content-type" not in header_keys:
            header_pairs.append(("Content-Type", ct))
        atype = self.auth_type.currentText()
        if atype == "Bearer" and self.auth_token.text().strip() and "authorization" not in header_keys:
            header_pairs.append(("Authorization", "Bearer " + self.auth_token.text().strip()))
        elif atype == "Basic" and "authorization" not in header_keys:
            tok = base64.b64encode(("%s:%s" % (self.auth_user.text(), self.auth_pass.text())).encode()).decode()
            header_pairs.append(("Authorization", "Basic " + tok))
        for k, v in header_pairs:
            req.setRawHeader(k.encode(), v.encode())

        self._current = {
            "method": method, "url": self.url.text().strip(), "params": self.params.pairs(),
            "headers": self.headers.pairs(), "ctype": ct, "body": body_txt, "auth_type": atype,
        }
        self.status.setText("Sending %s %s …" % (method, url.toString()))
        self.send_btn.setEnabled(False); self.abort_btn.setEnabled(True)
        self.resp_status.setText("… waiting")
        self._timer.restart()
        self._reply = self._nam.sendCustomRequest(req, method.encode(), body)
        self._reply.finished.connect(self._on_finished)

    def _abort(self):
        if self._reply is not None:
            self._reply.abort()

    # ── response ─────────────────────────────────────────────────────────
    def _on_finished(self):
        reply = self._reply
        self._reply = None
        self.send_btn.setEnabled(True); self.abort_btn.setEnabled(False)
        elapsed = self._timer.elapsed()
        if reply is None:
            return
        raw = bytes(reply.readAll())
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        reason = reply.attribute(QNetworkRequest.Attribute.HttpReasonPhraseAttribute)
        err = reply.error()

        if status is None and err != QNetworkReply.NetworkError.NoError:
            self.resp_status.setText("✗ %s" % reply.errorString())
            self.resp_status.setStyleSheet("color:#b00000; font-weight:bold;")
            self.resp_body.setPlainText(raw.decode(errors="replace") or reply.errorString())
            self.status.setText("Failed in %d ms." % elapsed)
            self._record(None)
            reply.deleteLater()
            return

        size = len(raw)
        color = "#2e7d32" if (status or 0) < 400 else ("#b26a00" if status < 500 else "#b00000")
        self.resp_status.setText("%s %s   ·   %d ms   ·   %s"
                                 % (status, reason or "", elapsed, _fmt_size(size)))
        self.resp_status.setStyleSheet("color:%s; font-weight:bold;" % color)

        text = raw.decode(errors="replace")
        ctype = _header_value(reply, b"content-type")
        if "json" in ctype.lower() or _looks_json(text):
            try:
                text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
            except Exception:
                pass
        self.resp_body.setPlainText(text)

        self.resp_headers.setRowCount(0)
        for name, value in reply.rawHeaderPairs():
            r = self.resp_headers.rowCount()
            self.resp_headers.insertRow(r)
            self.resp_headers.setItem(r, 0, QTableWidgetItem(bytes(name).decode(errors="replace")))
            self.resp_headers.setItem(r, 1, QTableWidgetItem(bytes(value).decode(errors="replace")))

        self.status.setText("Done in %d ms." % elapsed)
        self._record(status)
        reply.deleteLater()

    # ── history ──────────────────────────────────────────────────────────
    def _record(self, status):
        entry = dict(self._current); entry["status"] = status
        self._history.append(entry)
        label = "%s  %s  %s" % (status if status is not None else "✗",
                                entry["method"], entry["url"])
        it = QListWidgetItem(label)
        it.setData(Qt.ItemDataRole.UserRole, len(self._history) - 1)
        if status is not None:
            it.setForeground(QColor("#2e7d32" if status < 400 else "#b00000"))
        self.history.insertItem(0, it)

    def _load_history(self, item):
        entry = self._history[item.data(Qt.ItemDataRole.UserRole)]
        self.method.setCurrentText(entry["method"])
        self.url.setText(entry["url"])
        self.params.set_pairs(entry["params"])
        self.headers.set_pairs(entry["headers"])
        self.ctype.setCurrentText(entry.get("ctype", ""))
        self.body.setPlainText(entry.get("body", ""))
        self.auth_type.setCurrentText(entry.get("auth_type", "None"))

    def _clear_history(self):
        self._history.clear()
        self.history.clear()


def start():
    from abstract_gui.QT6.utils.console_utils import startConsole
    startConsole(apiConsole)
