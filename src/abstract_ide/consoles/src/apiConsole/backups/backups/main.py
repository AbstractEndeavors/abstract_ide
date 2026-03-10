from .imports import *
# ------------------------------------------------------------------------------
# Widget
# ------------------------------------------------------------------------------
class apiConsole(QWidget):
    TIMEOUT_MS = 15000  # 15s timeout

    def __init__(self, *, bases: Optional[Tuple[Tuple[str, str], ...]] = None,
                 default_prefix: str = "/api"):
        super().__init__()
        
        self.setWindowTitle("API Console (async, non-blocking)")
 

        self._bases = bases or PREDEFINED_BASE_URLS
        self._api_prefix = default_prefix if default_prefix.startswith("/") else f"/{default_prefix}"
     
        self._inflight: Optional[QNetworkReply] = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

        self._build_ui()
        self._wire()


    def start():
        startConsole(apiConsole)

