from .imports import *
class webPardner(QMainWindow):
    def __init__(self):
        super().__init__()
        initFuncs(self)
        self.setWindowTitle("Robust Web Scraper (PyQt6: Playwright / Selenium)")
        self.setGeometry(100, 100, 1000, 760)
        self.profiles = {}
        self.last_result = None
        self.workers: List[QThread] = []
        self.init_ui()
    def start():
        startConsole(webPardner)
