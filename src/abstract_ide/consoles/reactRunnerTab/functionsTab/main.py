from .functionsTab import functionsTab as _FunctionsTab
from abstract_gui.QT6.utils.console_utils import ConsoleBase,startConsole
class finderConsole(ConsoleBase):
    def __init__(self, *, bus=None, parent=None):
        super().__init__(bus=bus, parent=parent)
        tabs = QTabWidget()
        self.layout().addWidget(tabs)
        tabs.addTab(_FunctionsTab(), "Functions")

def startFinderConsole():
    startConsole(finderConsole)
