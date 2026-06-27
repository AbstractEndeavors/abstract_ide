from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, QThreadPool
from .imports.ui.article_browser import ArticleBrowser
from .imports.ui.query_bar import QueryBar
from .imports import startConsole


class _AuthSignals(QObject):
    done  = pyqtSignal(str)
    error = pyqtSignal(str)


class _AuthWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = _AuthSignals()

    def run(self):
        try:
            from .imports.managers.listManager import LISTMANAGER
            token = LISTMANAGER().authenticate()
            self.signals.done.emit(token or "")
        except Exception as e:
            self.signals.error.emit(str(e))


class DbImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("dbImageViewer")
        self.resize(1200, 800)

        browser = ArticleBrowser()
        controls = QueryBar(browser)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(controls)
        layout.addWidget(browser)
        self.setCentralWidget(central)

        # authenticate in background — captcha prompt goes to terminal
        auth = _AuthWorker()
        auth.signals.done.connect(lambda t: print(f"[auth] token acquired"))
        auth.signals.error.connect(lambda e: print(f"[auth error] {e}"))
        QThreadPool.globalInstance().start(auth)


def startDbImageConsole():
    startConsole(DbImageViewer)
