from .functionsTab import _FunctionsTab
from .runnerTab import runnerTab
from .testRunnerTab import testRunnerTab
from .imports import *
# Content Finder = the nested group you built (Find Content, Directory Map, Collect, Imports, Diff)
class reactRunnerTab(ConsoleBase):
    def __init__(self, *, bus=None, parent=None):
        super().__init__(bus=bus, parent=parent)
        inner = QTabWidget()
        self.layout().addWidget(inner)
        install_qt_logging() 
        # all content tabs share THIS console’s bus
        inner.addTab(runnerTab(),      "react Runner")
        inner.addTab(_FunctionsTab(),   "Functions")
        inner.addTab(testRunnerTab(),   "Test Runner")
        
        #add_logs_tab(inner, title="Logs")   # << auto-attaches to the same logger pipe
        #self._logs_view = add_logs_to(self)   # adds a Show/Hide Logs bar + panel

    def test():
        startConsole(reactRunnerTab)
