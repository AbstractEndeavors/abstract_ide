from .imports import *
from .initFuncs import initFuncs

# ---------- Public: Logs as a tab ----------
class logTab(QWidget):
    """A self-contained 'Logs' console: toolbar + QPlainTextEdit."""
    def __init__(self, parent: QWidget | None = None, *, title: str = "Logs"):
        super().__init__(parent)
        self.setObjectName("LogConsole")
        self.title = title

        lay = QVBoxLayout(self)
        # toolbar
        bar = QWidget(self); bl = QHBoxLayout(bar); bl.setContentsMargins(0,0,0,0)
        self.btn_clear = QPushButton("Clear", bar)
        self.btn_pause = QPushButton("Pause", bar); self.btn_pause.setCheckable(True)
        bl.addStretch(1); bl.addWidget(self.btn_pause); bl.addWidget(self.btn_clear)
        lay.addWidget(bar)

        # log view
        self.view = QPlainTextEdit(self)
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.view.setMinimumHeight(160)
        lay.addWidget(self.view)

        install_logging_stack()  # once is fine; idempotent
        attach_log_stream(self.view)

        # actions
        self.btn_clear.clicked.connect(lambda: self.view.setPlainText(""))
        self.btn_pause.toggled.connect(self._toggle_pause)
        self._paused = False
logTab = initFuncs(logTab)

