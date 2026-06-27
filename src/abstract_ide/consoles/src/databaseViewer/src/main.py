from .imports import *

class databaseViewer(QMainWindow):
    """
    Main database viewer window.
    Uses queue-based worker, no blocking operations on UI thread.
    """
    
    def __init__(self):
        super().__init__()
        initFuncs(self)
        self.setWindowTitle("Database Viewer")
        self.resize(1200, 800)
        
        # State
        self.current_table: Optional[str] = None
        self.column_types: Dict[str, str] = {}
        self.columns_list_data: List[str] = []
        self.db_config: Optional[DbConfig] = None  # Store config for stream worker
        
        # Worker
        self.worker = DatabaseWorker()
        self.worker.result_ready.connect(self._on_result)
        self.worker.start()
        
        # Stream worker (created when connection established)
        self.stream_worker: Optional[StreamWorker] = None
        self.streaming_tables: set = set()
        
        self._build_ui()
    def start():
        startConsole(databaseViewer)
