from abstract_utilities import call_for_all_tabs
call_for_all_tabs()
from .main import clipitTab
from abstract_gui.QT6.utils.console_utils import startConsole,ConsoleBase

def startClipitConsole():
    startConsole(clipitTab)
