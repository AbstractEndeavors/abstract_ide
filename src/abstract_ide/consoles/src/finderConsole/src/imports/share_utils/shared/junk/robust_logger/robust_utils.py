# robust_utils.py — unified, fast log panel (PyQt6)

from __future__ import annotations
import io, os, sys, logging, traceback
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, qInstallMessageHandler, QtMsgType, Qt
from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QPlainTextEdit, QDockWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget
)
from PyQt6.QtGui import QTextCursor  # used only for QTextEdit fallback (if ever)

# ---------- paths ----------
LOG_DIR  = os.path.join(os.path.expanduser("~"), ".cache", "abstract_finder")
LOG_FILE = os.path.join(LOG_DIR, "finder.log")
os.makedirs(LOG_DIR, exist_ok=True)

def get_log_file_path() -> str:
    return LOG_FILE

# ---------- Python/Qt -> Qt signal bridge ----------
class QtLogEmitter(QObject):
    new_log = pyqtSignal(str)

_emitter_singleton: QtLogEmitter | None = None
_handler_singleton: logging.Handler | None = None

def _emitter() -> QtLogEmitter:
    global _emitter_singleton
    if _emitter_singleton is None:
        _emitter_singleton = QtLogEmitter()
    return _emitter_singleton

class QtLogHandler(logging.Handler):
    def __init__(self, emitter: QtLogEmitter):
        super().__init__()
        self.emitter = emitter
    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self.emitter.new_log.emit(msg + "\n")

def install_python_logging():
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.DEBUG)

        f = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
        f.setLevel(logging.DEBUG)
        f.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"))
        root.addHandler(f)

        c = logging.StreamHandler(sys.stderr)
        c.setLevel(logging.INFO)
        c.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        root.addHandler(c)

    def _format_exc(exctype, value, tb):
        return "".join(traceback.format_exception(exctype, value, tb))
    def excepthook(exctype, value, tb):
        logging.critical("UNCAUGHT EXCEPTION:\n%s", _format_exc(exctype, value, tb))
    sys.excepthook = excepthook

def install_qt_bridge():
    global _handler_singleton
    if _handler_singleton is None:
        _handler_singleton = QtLogHandler(_emitter())
        _handler_singleton.setLevel(logging.DEBUG)
        _handler_singleton.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(_handler_singleton)

    def qt_msg(mode, ctx, message):
        level = {
            QtMsgType.QtDebugMsg:    logging.DEBUG,
            QtMsgType.QtInfoMsg:     logging.INFO,
            QtMsgType.QtWarningMsg:  logging.WARNING,
            QtMsgType.QtCriticalMsg: logging.ERROR,
            QtMsgType.QtFatalMsg:    logging.CRITICAL,
        }.get(mode, logging.INFO)
        logging.log(level, "Qt: %s (%s:%d)", message, ctx.file, ctx.line)
    qInstallMessageHandler(qt_msg)

def install_qt_logging():
    """Call once at app startup (idempotent)."""
    install_python_logging()
    install_qt_bridge()

# ---------- low-level helpers ----------
def _trim_plain_text_edit(te: QPlainTextEdit, max_lines: int):
    doc = te.document()
    extra = doc.blockCount() - max_lines
    if extra <= 0:
        return
    cur = te.textCursor()
    cur.beginEditBlock()
    blk = doc.firstBlock()
    while extra > 0 and blk.isValid():
        cur.setPosition(blk.position())
        cur.movePosition(cur.MoveOperation.NextBlock, cur.MoveMode.KeepAnchor)
        cur.removeSelectedText()
        cur.deleteChar()  # remove newline
        blk = blk.next()
        extra -= 1
    cur.endEditBlock()

def _safe_append(te: QPlainTextEdit | 'QTextEdit', chunk: str):
    # We standardize on QPlainTextEdit, but keep a QTextEdit fallback if someone passes one.
    if isinstance(te, QPlainTextEdit):
        te.appendPlainText(chunk)
    else:
        # Lazy import to avoid hard dependency
        from PyQt6.QtWidgets import QTextEdit  # type: ignore
        if isinstance(te, QTextEdit):
            te.moveCursor(QTextCursor.MoveOperation.End)
            te.insertPlainText(chunk)
            te.ensureCursorVisible()
        else:
            # last resort
            try:
                te.appendPlainText(chunk)  # may work if it's QTextBrowser-like
            except Exception:
                pass

# ---------- public: create/attach/view ----------
def set_self_log(host) -> QPlainTextEdit:
    """
    Create a cheap QPlainTextEdit log widget as a child of `host`.
    Returns the widget (idempotent).
    """
    if getattr(host, "log", None) and isinstance(host.log, QPlainTextEdit):
        return host.log
    log = QPlainTextEdit(host)
    log.setReadOnly(True)
    log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    log.setMinimumHeight(140)
    host.log = log
    return log

def attach_textedit_to_logs(
    textedit: QPlainTextEdit,
    *,
    tail_file: str | None = LOG_FILE,
    max_lines: int = 2000,
    debounce_ms: int = 120,
    start_from_end: bool = True,
    poll_interval_ms: int = 500
):
    """
    Batched, trimmed log feed to `textedit`.
    - Starts from EOF (cheap) if tailing a file.
    - Batches appends to reduce UI churn.
    """
    install_qt_bridge()  # ensure the handler exists

    buf: list[str] = []
    timer = QTimer(textedit)
    timer.setInterval(debounce_ms)

    def _flush():
        if not buf:
            return
        chunk = "".join(buf)
        buf.clear()
        _safe_append(textedit, chunk)
        _trim_plain_text_edit(textedit, max_lines)

    timer.timeout.connect(_flush)
    timer.start()
    textedit._batch_timer = timer  # keep alive
    textedit._batch_buf = buf

    # Live Python/Qt logs
    _emitter().new_log.connect(buf.append)
    textedit._emitter_conn = buf.append

    # Optional tail
    if tail_file:
        # start from end to keep startup fast
        textedit._tail_pos = 0
        try:
            with io.open(tail_file, "rb") as f:
                f.seek(0, os.SEEK_END)
                textedit._tail_pos = f.tell()
        except FileNotFoundError:
            pass

        tail_timer = QTimer(textedit)
        tail_timer.setInterval(poll_interval_ms)

        def _poll():
            try:
                with io.open(tail_file, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(getattr(textedit, "_tail_pos", 0))
                    chunk = f.read()
                    textedit._tail_pos = f.tell()
                if chunk:
                    buf.append(chunk)
            except FileNotFoundError:
                pass

        tail_timer.timeout.connect(_poll)
        tail_timer.start()
        textedit._tail_timer = tail_timer

def add_logs_to(host) -> QPlainTextEdit:
    """
    Add a log viewer to a host container.
    - If host is QMainWindow: create a bottom dock + a small toggle button.
    - Else: insert a small toolbar with Show/Hide and the log view under it.
    Returns the QPlainTextEdit.
    """
    log = QPlainTextEdit(host)
    log.setReadOnly(True)
    log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    log.setMinimumHeight(140)

    if isinstance(host, QMainWindow):
        dock = QDockWidget("Logs", host)
        dock.setObjectName("DockLogs")
        dock.setWidget(log)
        host.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        dock.hide()

        cw = host.centralWidget() or QWidget(host)
        if host.centralWidget() is None:
            host.setCentralWidget(cw)
        lay = cw.layout() or QVBoxLayout()
        if cw.layout() is None:
            cw.setLayout(lay)

        bar = QWidget(cw)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("Show Logs", bar)

        def toggle():
            if dock.isHidden():
                dock.show()
                btn.setText("Hide Logs")
            else:
                dock.hide()
                btn.setText("Show Logs")

        btn.clicked.connect(toggle)
        bl.addStretch(1)
        bl.addWidget(btn)
        lay.addWidget(bar)
        return log

    # Plain QWidget host
    lay = host.layout() or QVBoxLayout(host)
    if host.layout() is None:
        host.setLayout(lay)

    bar = QWidget(host)
    bl = QHBoxLayout(bar)
    bl.setContentsMargins(0, 0, 0, 0)
    btn = QPushButton("Show Logs", bar)
    log.hide()

    def toggle():
        if log.isHidden():
            log.show()
            btn.setText("Hide Logs")
        else:
            log.hide()
            btn.setText("Show Logs")

    btn.clicked.connect(toggle)
    bl.addStretch(1)
    bl.addWidget(btn)
    lay.addWidget(bar)
    lay.addWidget(log)
    return log

# ---------- optional: logs as a tab ----------
class LogConsole(QWidget):
    """Self-contained log console suitable for a tab."""
    def __init__(self, parent: QWidget | None = None, *, title: str = "Logs"):
        super().__init__(parent)
        self.title = title
        v = QVBoxLayout(self)
        # toolbar
        bar = QWidget(self); hb = QHBoxLayout(bar); hb.setContentsMargins(0,0,0,0)
        self.btn_clear = QPushButton("Clear", bar)
        self.btn_pause = QPushButton("Pause", bar); self.btn_pause.setCheckable(True)
        hb.addStretch(1); hb.addWidget(self.btn_pause); hb.addWidget(self.btn_clear)
        v.addWidget(bar)
        # view
        self.view = QPlainTextEdit(self)
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.view.setMinimumHeight(160)
        v.addWidget(self.view)

        install_qt_logging()
        attach_textedit_to_logs(self.view)

        self.btn_clear.clicked.connect(lambda: self.view.setPlainText(""))
        self.btn_pause.toggled.connect(lambda chk: self.view.setDisabled(chk))

def add_logs_tab(tabw: QTabWidget, *, title: str = "Logs") -> LogConsole:
    console = LogConsole(tabw, title=title)
    tabw.addTab(console, title)
    return console
