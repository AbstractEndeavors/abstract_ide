from .functionsTab import functionsTab
from .imports import *
class finderTab(ConsoleBase):
    def __init__(self, *, bus=None, parent=None):
        super().__init__(bus=bus, parent=parent)
        initFuncs(self)
        tabs = QTabWidget()
        self.layout().addWidget(tabs)
        tabs.addTab(functionsTab(), "Functions")
    def start():
        startConsole(finderTab)

