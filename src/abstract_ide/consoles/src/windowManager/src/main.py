from .imports import *
# -----------------------------------------------------------------------------
#  main application ------------------------------------------------------------
# -----------------------------------------------------------------------------
class windowManager(QMainWindow):
    COLS = ["Window ID", "Title", "PID", "Monitor", "Type", "Selected?"]
    def __init__(self) -> None:
        super().__init__()
        initFuncs(self)                      # <-- IMPORTANT: load imports FIRST
        self.setWindowTitle("Window Manager")
        self.resize(980, 640)

        self.monitors: List[Tuple[str, int, int, int, int]] = []
        self.windows:  List[Tuple[str, str, str, str, str]] = []

        self._build_ui()                     # <-- NOW SAFE
        self.wm_compute_self_ids()             # <-- also imported
        self.refresh()
        
    def start():
        startConsole(windowManager)
