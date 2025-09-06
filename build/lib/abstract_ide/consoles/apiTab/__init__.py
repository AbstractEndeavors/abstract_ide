from abstract_gui.QT6 import *
from abstract_utilities import get_logFile
from .main import apiTab
from abstract_gui.QT6.utils.console_utils import startConsole
logger = get_logFile(__name__)
# ─── Main GUI ─────────────────────────────────────────────────────────────
class apiConsole(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("API Console Demo")
        self.setCentralWidget(apiTab())

def startApiConsole():
    startConsole(apiTab)
