from .imports import *
from .initFuncs import initFuncs
# -----------------------------------------------------------------------------
#  supervised child process runner ------------------------------------------------------------
# -----------------------------------------------------------------------------
class logPaneTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        try:
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
        except Exception as e:
            print(f"{e}")


logPaneTab = initFuncs(logPaneTab)
