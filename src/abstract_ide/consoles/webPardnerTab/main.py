from .imports import *
from .initFuncs import initFuncs

class webPardnerTab(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robust Web Scraper (PyQt6: Playwright / Selenium)")
        self.setGeometry(100, 100, 1000, 760)
        self.profiles = {}
        self.last_result = None
        self.workers: List[QThread] = []
        self.init_ui()

webPardnerTab = initFuncs(webPardnerTab)
