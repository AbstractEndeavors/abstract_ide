from .imports import QTabWidget
from .main import logTab
from abstract_gui import  startConsole
def startLogConsole():
    startConsole(logTab)
def add_logs_tab(tabw: QTabWidget, *, title: str = "Logs") -> logTab:
    """Add a 'Logs' tab to an existing QTabWidget; returns the console."""
    console = logTab(tabw, title=title)
    tabw.addTab(console, title)
    return console
