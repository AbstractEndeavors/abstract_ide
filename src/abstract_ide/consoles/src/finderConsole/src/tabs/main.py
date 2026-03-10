from .imports import *
from .diffParserTab import diffParserTab
from .directoryMapTab import directoryMapTab
from .extractImportsTab import extractImportsTab
from .finderTab import finderTab
from .collectFilesTab import collectFilesTab
from .scaffolder import Scaffolder
class finderConsole(ConsoleBase):
    def __init__(self, *, bus=None, parent=None):
        super().__init__(bus=bus, parent=parent)
        inner = QTabWidget()
        self.layout().addWidget(inner)
    
        # all content tabs share THIS console’s bus
        inner.addTab(finderTab(self.bus),         "Find Content")
        inner.addTab(directoryMapTab(self.bus),   "Directory Map")
        #inner.addTab(extractImportsTab(self.bus), "Extract Python Imports")
        inner.addTab(diffParserTab(self.bus),     "Diff (Repo)")
        inner.addTab(Scaffolder(self.bus),     "scaffolder")
