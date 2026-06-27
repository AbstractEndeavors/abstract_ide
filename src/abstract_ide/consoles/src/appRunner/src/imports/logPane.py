from .src import *
from .utils import *
# ---------------- toggleable log pane ----------------
class LogPane(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0,0,0,0)
        self.toolbar = QtWidgets.QToolBar()
        self.clear_act = self.toolbar.addAction("Clear")
        self.open_act  = self.toolbar.addAction("Open Log File")
        self.auto_scroll = QtWidgets.QCheckBox("Auto-scroll"); self.auto_scroll.setChecked(True)
        self.toolbar.addWidget(self.auto_scroll)
        v.addWidget(self.toolbar)
        self.view = QtWidgets.QPlainTextEdit(readOnly=True)
        self.view.setMaximumBlockCount(5000)  # cap memory
        v.addWidget(self.view)
        self.clear_act.triggered.connect(self.view.clear)
        self.open_act.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(log_path())))

    def append_line(self, line: str):
        self.view.appendPlainText(line.rstrip("\n"))
        if self.auto_scroll.isChecked():
            self.view.moveCursor(QtGui.QTextCursor.MoveOperation.End)
