# logs_tab.py
from __future__ import annotations
import os, sys, io, logging, traceback
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, qInstallMessageHandler, QtMsgType, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPlainTextEdit, QTabWidget, QPushButton, QHBoxLayout
)

LOG_DIR  = os.path.join(os.path.expanduser("~"), ".cache", "abstract_logging")
LOG_FILE = os.path.join(LOG_DIR, "finder.log")
os.makedirs(LOG_DIR, exist_ok=True)

# ---------- Python/Qt → Qt signal ----------
class QtLogEmitter(QObject):
    line = pyqtSignal(str)

_emitter: QtLogEmitter | None = None
_handler: logging.Handler | None = None

def _get_emitter() -> QtLogEmitter:
    global _emitter
    if _emitter is None:
        _emitter = QtLogEmitter()
    return _emitter

class QtLogHandler(logging.Handler):
    def __init__(self, emitter: QtLogEmitter):
        super().__init__()
        self.emitter = emitter
    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self.emitter.line.emit(msg + "\n")

def install_python_logging():
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
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
    global _handler
    if _handler is None:
        _handler = QtLogHandler(_get_emitter())
        _handler.setLevel(logging.DEBUG)
        _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(_handler)

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

def install_logging_stack():
    install_python_logging()
    install_qt_bridge()

# ---------- Log viewer core (batched + trimmed) ----------
def _trim(te: QPlainTextEdit, max_lines: int):
    doc = te.document()
    extra = doc.blockCount() - max_lines
    if extra <= 0: return
    cur = te.textCursor()
    cur.beginEditBlock()
    blk = doc.firstBlock()
    while extra > 0 and blk.isValid():
        cur.setPosition(blk.position())
        cur.movePosition(cur.MoveOperation.NextBlock, cur.MoveMode.KeepAnchor)
        cur.removeSelectedText()
        cur.deleteChar()
        blk = blk.next()
        extra -= 1
    cur.endEditBlock()

def attach_log_stream(
    text: QPlainTextEdit,
    *,
    max_lines: int = 2000,
    debounce_ms: int = 120,
    tail_file: str | None = LOG_FILE,
    start_from_end: bool = True
):
    install_qt_bridge()  # ensure handler exists
    buf: list[str] = []
    t = QTimer(text)
    t.setInterval(debounce_ms)

    def flush():
        if not buf: return
        chunk = "".join(buf); buf.clear()
        text.appendPlainText(chunk)
        _trim(text, max_lines)

    t.timeout.connect(flush); t.start()
    _get_emitter().line.connect(buf.append)

    if tail_file:
        # start from EOF for cheap startup
        try:
            with open(tail_file, "rb") as f:
                pos = f.seek(0, os.SEEK_END)
                text._tail_pos = pos
        except FileNotFoundError:
            text._tail_pos = 0

        tail_t = QTimer(text); tail_t.setInterval(500)
        def poll():
            try:
                with open(tail_file, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(getattr(text, "_tail_pos", 0))
                    chunk = f.read()
                    text._tail_pos = f.tell()
                if chunk:
                    buf.append(chunk)
            except FileNotFoundError:
                pass
        tail_t.timeout.connect(poll); tail_t.start()
