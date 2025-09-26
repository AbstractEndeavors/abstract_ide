##from .functionsTab import _FunctionsTab
from .apiTab import apiTab, startApiConsole
from .imageTab import startImageConsole, imageTab
from .clipitTab import clipitTab, startClipitConsole
from .finderTab import finderConsole, startFinderConsole
from .logPaneTab import logPaneTab, startLogPaneConsole
from .appRunnerTab import appRunnerTab, startAppRunnerConsole
from .reactRunnerTab import reactRunnerTab, startReactRunnerConsole
from .windowManagerTab import windowManagerTab, startWindowManagerConsole
from .scriptWindowTab import scriptWindowTab, startScriptWindowConsole
from .launcherWindowTab import launcherWindowTab, startLauncherWindowConsole
from .webPardnerTab import webPardnerTab,startWebPardnerConsole
from abstract_gui.QT6 import QTabWidget,QMainWindow
from abstract_gui.QT6.utils.console_utils import ConsoleBase
from abstract_gui.QT6.utils.console_utils import startConsole
# Content Finder = the nested group you built (Find Content, Directory Map, Collect, Imports, Diff)
class ideTab(ConsoleBase):
    def __init__(self, *, bus=None, parent=None):
        super().__init__(bus=bus, parent=parent)
        inner = QTabWidget()
        self.layout().addWidget(inner)
        # all content tabs share THIS console’s bus
        inner.addTab(reactRunnerTab(),      "react Runner")
        inner.addTab(finderConsole(),   "Finder")
        inner.addTab(apiTab(),   "Api")
        inner.addTab(clipitTab(),   "Clipit")
        inner.addTab(webPardnerTab(),   "Web Pardner")
        inner.addTab(windowManagerTab(),   "Window Mgr")
        inner.addTab(launcherWindowTab(),   "launcherWindow")
        inner.addTab(scriptWindowTab(),   "scriptWindow")
        inner.addTab(imageTab(),   "Images")
        inner.addTab(logPaneTab(),   "logs")
        
        
