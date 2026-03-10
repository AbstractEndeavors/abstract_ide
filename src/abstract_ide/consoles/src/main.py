from .apiConsole import apiConsole
from .clipit import ClipIt
from .finderConsole import finderConsole
from .logConsole import logConsole
from .appRunner import appRunner
from .reactRunner import *
from .windowManager import windowManager
from .webPardner import webPardner
from .databaseViewer import databaseViewer
from .imageTab import startImageConsole, imageTab
from .dbImageViewer import startDbImageConsole,DbImageViewer
from abstract_gui.QT6 import QTabWidget,QMainWindow
from abstract_gui.QT6.utils.console_utils import ConsoleBase
from abstract_gui.QT6.utils.console_utils import startConsole

# Content Finder = the nested group you built (Find Content, Directory Map, Collect, Imports, Diff)
class ideConsole(ConsoleBase):
    def __init__(self, *, bus=None, parent=None):
        super().__init__(bus=bus, parent=parent)
        inner = QTabWidget()
        self.layout().addWidget(inner)
        # all content tabs share THIS console’s bus
        inner.addTab(reactRunner(),      "react Runner")
        inner.addTab(finderConsole(),   "Finder")
        inner.addTab(apiConsole(),   "Api")
        inner.addTab(databaseViewer(),   "databaseViewer")
        inner.addTab(ClipIt(),   "Clipit")
        inner.addTab(webPardner(),   "Web Pardner")
        inner.addTab(windowManager(),   "Window Mgr")
        inner.addTab(appRunner(),   "app runner")
        inner.addTab(imageTab(),   "Images")
        inner.addTab(DbImageViewer(),   "dbImageViewer")
        inner.addTab(logConsole(),   "logs")
        
    def start():
        startConsole(ideConsole)
        
