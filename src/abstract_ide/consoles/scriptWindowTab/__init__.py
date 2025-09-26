from abstract_utilities import call_for_all_tabs
call_for_all_tabs()
from .main import scriptWindowTab
from abstract_gui.QT6.utils.console_utils import startConsole
def startScriptWindowConsole():
    startConsole(scriptWindowTab)
