# functions_console.py
from .imports import QWidget,pyqtSignal

from .initFuncs import initFuncs
# --- Console ---------------------------------------------------------------
# functionsTab/main.py

class functionsTab(QWidget):
    functionSelected = pyqtSignal(str)
    variableSelected = pyqtSignal(str)    # <- move here (don’t create signals inside __init__)
    scanRequested   = pyqtSignal(str)
    def __init__(self, parent=None, use_flow=False):
        super().__init__(parent)
        self.func_map = {}
        self.init_path= '/var/www/html/clownworld/bolshevid'
        self.fn_filter_mode = "io"
        self.current_fn = None
        self.current_var = None
        self.use_flow=use_flow
        self._build_ui()



functionsTab = initFuncs(functionsTab)
