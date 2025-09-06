from abstract_utilities import call_for_all_tabs
call_for_all_tabs()
from .main import launcherWindowTab
from abstract_gui.QT6.utils.console_utils import startConsole
def startLauncherWindowConsole():
    startConsole(launcherWindowTab)
