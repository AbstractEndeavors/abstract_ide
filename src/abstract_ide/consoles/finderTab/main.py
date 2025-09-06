from .imports import *
from .tabs import (
    collectFilesTab, diffParserTab,directoryMapTab,
    extractImportsTab, finderTab,
)
from abstract_gui.QT6.utils.console_utils.consoleBase import ConsoleBase
# Content Finder = the nested group you built (Find Content, Directory Map, Collect, Imports, Diff)
class finderConsole(ConsoleBase):
    def __init__(self, *, bus=None, parent=None):
        super().__init__(bus=bus, parent=parent)
        inner = QTabWidget()
        self.layout().addWidget(inner)
    
        # all content tabs share THIS console’s bus
        inner.addTab(finderTab(self.bus),         "Find Content")
        inner.addTab(directoryMapTab(self.bus),   "Directory Map")
        inner.addTab(extractImportsTab(self.bus), "Extract Python Imports")
        inner.addTab(diffParserTab(self.bus),     "Diff (Repo)")
