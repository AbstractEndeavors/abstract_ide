#!/usr/bin/env python3
"""
Database Viewer - Clean implementation
Explicit wiring, no singleton magic, proper error handling
"""
from .init_imports import *
from .db_imports import *
from .module_imports import *
# ============================================================================
# SCHEMA DEFINITIONS
# ============================================================================

class TaskType(Enum):
    CONNECT = auto()
    LIST_TABLES = auto()
    LIST_COLUMNS = auto()
    QUERY = auto()
    PREVIEW = auto()


@dataclass
class DbConfig:
    """Explicit database configuration - no magic defaults"""
    url: str
    
    @classmethod
    def from_parts(cls, dialect: str, user: str, password: str, 
                   host: str, port: int, database: str) -> 'DbConfig':
        url = f"{dialect}://{user}:{password}@{host}:{port}/{database}"
        return cls(url=url)
    
    @classmethod
    def sqlite(cls, path: str) -> 'DbConfig':
        return cls(url=f"sqlite:///{path}")


@dataclass
class Task:
    """Work item for the background queue"""
    task_type: TaskType
    payload: Dict[str, Any] = field(default_factory=dict)
    callback_id: str = ""


@dataclass 
class TaskResult:
    """Result from background processing"""
    task_type: TaskType
    success: bool
    data: Any = None
    error: Optional[str] = None
    callback_id: str = ""


@dataclass
class StreamConfig:
    """Configuration for streaming table changes"""
    table_name: str
    watermark_column: str  # Column to track (e.g., 'id', 'created_at')
    poll_interval_ms: int = 1000
    batch_size: int = 50
    
    # For PostgreSQL NOTIFY (optional)
    use_notify: bool = False
    channel_name: Optional[str] = None


@dataclass
class StreamEvent:
    """A batch of new rows from the stream"""
    table_name: str
    rows: pd.DataFrame
    watermark_value: Any
    event_type: str = "insert"  # Could extend to "update", "delete" with triggers


# ============================================================================
# DATABASE LAYER - No singletons, explicit connections
# ============================================================================

class DatabaseConnection:
    """
    Explicit database connection - you create it, you own it, you close it.
    No singleton nonsense.
    """
    
    def __init__(self, config: DbConfig):
        self.config = config
        self.engine = None
        self.session = None
        self.inspector = None
        self.metadata = MetaData()
    
    def connect(self) -> None:
        """Establish connection - raises on failure"""
        self.engine = create_engine(self.config.url, pool_pre_ping=True)
        # Test the connection immediately
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.inspector = inspect(self.engine)
    
    def close(self) -> None:
        if self.session:
            self.session.close()
        if self.engine:
            self.engine.dispose()
    
    def list_tables(self) -> List[str]:
        if not self.inspector:
            raise RuntimeError("Not connected")
        return self.inspector.get_table_names()
    
    def list_columns(self, table_name: str) -> List[str]:
        if not self.inspector:
            raise RuntimeError("Not connected")
        columns = self.inspector.get_columns(table_name)
        return [c['name'] for c in columns]
    
    def get_column_types(self, table_name: str) -> Dict[str, str]:
        if not self.inspector:
            raise RuntimeError("Not connected")
        columns = self.inspector.get_columns(table_name)
        return {c['name']: str(c['type']) for c in columns}
    
    def preview_table(self, table_name: str, limit: int = 100) -> pd.DataFrame:
        if not self.session:
            raise RuntimeError("Not connected")
        query = text(f'SELECT * FROM "{table_name}" LIMIT :limit')
        result = self.session.execute(query, {"limit": limit})
        rows = result.fetchall()
        columns = result.keys()
        return pd.DataFrame(rows, columns=columns)
    
    def search(self, table_name: str, column: str, value: str, limit: int = 100) -> pd.DataFrame:
        if not self.session:
            raise RuntimeError("Not connected")
        # Use LIKE with LOWER for cross-database compatibility (ILIKE is postgres-only)
        query = text(f'''
            SELECT * FROM "{table_name}" 
            WHERE LOWER(CAST("{column}" AS TEXT)) LIKE LOWER(:pattern)
            LIMIT :limit
        ''')
        result = self.session.execute(query, {"pattern": f"%{value}%", "limit": limit})
        rows = result.fetchall()
        columns = result.keys()
        return pd.DataFrame(rows, columns=columns)
    
    def execute_raw(self, sql: str, limit: int = 1000) -> pd.DataFrame:
        if not self.session:
            raise RuntimeError("Not connected")
        result = self.session.execute(text(sql))
        rows = result.fetchmany(limit)
        columns = result.keys()
        return pd.DataFrame(rows, columns=columns)
    
    def get_max_watermark(self, table_name: str, watermark_column: str) -> Any:
        """Get the current maximum value of the watermark column"""
        if not self.session:
            raise RuntimeError("Not connected")
        query = text(f'SELECT MAX("{watermark_column}") as max_val FROM "{table_name}"')
        result = self.session.execute(query)
        row = result.fetchone()
        return row[0] if row else None
    
    def get_rows_after_watermark(
        self, 
        table_name: str, 
        watermark_column: str, 
        watermark_value: Any,
        limit: int = 50
    ) -> pd.DataFrame:
        """Fetch rows where watermark_column > watermark_value"""
        if not self.session:
            raise RuntimeError("Not connected")
        
        if watermark_value is None:
            # First poll - get latest rows
            query = text(f'''
                SELECT * FROM "{table_name}" 
                ORDER BY "{watermark_column}" DESC 
                LIMIT :limit
            ''')
            result = self.session.execute(query, {"limit": limit})
        else:
            query = text(f'''
                SELECT * FROM "{table_name}" 
                WHERE "{watermark_column}" > :watermark
                ORDER BY "{watermark_column}" ASC 
                LIMIT :limit
            ''')
            result = self.session.execute(query, {"watermark": watermark_value, "limit": limit})
        
        rows = result.fetchall()
        columns = result.keys()
        return pd.DataFrame(rows, columns=columns)
    
    def setup_notify_trigger(self, table_name: str, channel_name: str) -> None:
        """
        Set up PostgreSQL NOTIFY trigger for real-time updates.
        Only works with PostgreSQL.
        """
        if not self.session:
            raise RuntimeError("Not connected")
        
        # Check if we're on PostgreSQL
        if 'postgresql' not in str(self.engine.url):
            raise RuntimeError("NOTIFY triggers only supported on PostgreSQL")
        
        trigger_name = f"notify_{table_name}_{channel_name}"
        function_name = f"notify_trigger_{channel_name}"
        
        # Create the notification function
        create_function = text(f'''
            CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS trigger AS $$
            BEGIN
                PERFORM pg_notify('{channel_name}', row_to_json(NEW)::text);
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        ''')
        
        # Create the trigger
        create_trigger = text(f'''
            DROP TRIGGER IF EXISTS {trigger_name} ON "{table_name}";
            CREATE TRIGGER {trigger_name}
            AFTER INSERT ON "{table_name}"
            FOR EACH ROW EXECUTE FUNCTION {function_name}();
        ''')
        
        self.session.execute(create_function)
        self.session.execute(create_trigger)
        self.session.commit()
    
    def listen(self, channel_name: str, timeout: float = 1.0) -> List[str]:
        """
        Listen for PostgreSQL NOTIFY messages.
        Returns list of payloads received within timeout.
        """
        if not self.engine:
            raise RuntimeError("Not connected")
        
        if 'postgresql' not in str(self.engine.url):
            raise RuntimeError("LISTEN only supported on PostgreSQL")
        
        import select
        
        # Need raw connection for LISTEN
        raw_conn = self.engine.raw_connection()
        raw_conn.set_isolation_level(0)  # Autocommit required for LISTEN
        
        cursor = raw_conn.cursor()
        cursor.execute(f"LISTEN {channel_name};")
        
        payloads = []
        if select.select([raw_conn], [], [], timeout) != ([], [], []):
            raw_conn.poll()
            while raw_conn.notifies:
                notify = raw_conn.notifies.pop(0)
                payloads.append(notify.payload)
        
        cursor.close()
        return payloads


# ============================================================================
# WORKER - Queue-based, no callbacks
# ============================================================================

class DatabaseWorker(QObject):
    """
    Background worker using a queue.
    Emits signals instead of callbacks - Qt's thread-safe mechanism.
    """
    
    result_ready = pyqtSignal(object)  # TaskResult
    
    def __init__(self):
        super().__init__()
        self.task_queue: Queue[Task] = Queue()
        self.connection: Optional[DatabaseConnection] = None
        self._running = False
        self._thread: Optional[Thread] = None
    
    def start(self):
        self._running = True
        self._thread = Thread(target=self._process_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
        self.task_queue.put(Task(TaskType.CONNECT))  # Unblock the queue
        if self._thread:
            self._thread.join(timeout=1.0)
    
    def submit(self, task: Task):
        self.task_queue.put(task)
    
    def _process_loop(self):
        while self._running:
            task = self.task_queue.get()
            if not self._running:
                break
            
            result = self._process_task(task)
            self.result_ready.emit(result)
    
    def _process_task(self, task: Task) -> TaskResult:
        try:
            if task.task_type == TaskType.CONNECT:
                config = task.payload.get('config')
                if self.connection:
                    self.connection.close()
                self.connection = DatabaseConnection(config)
                self.connection.connect()
                return TaskResult(task.task_type, True, "Connected", callback_id=task.callback_id)
            
            if not self.connection:
                return TaskResult(task.task_type, False, error="Not connected", callback_id=task.callback_id)
            
            if task.task_type == TaskType.LIST_TABLES:
                tables = self.connection.list_tables()
                return TaskResult(task.task_type, True, tables, callback_id=task.callback_id)
            
            if task.task_type == TaskType.LIST_COLUMNS:
                table = task.payload['table']
                columns = self.connection.list_columns(table)
                types = self.connection.get_column_types(table)
                return TaskResult(task.task_type, True, {'columns': columns, 'types': types}, callback_id=task.callback_id)
            
            if task.task_type == TaskType.PREVIEW:
                table = task.payload['table']
                limit = task.payload.get('limit', 100)
                df = self.connection.preview_table(table, limit)
                return TaskResult(task.task_type, True, df, callback_id=task.callback_id)
            
            if task.task_type == TaskType.QUERY:
                table = task.payload['table']
                column = task.payload.get('column')
                value = task.payload.get('value')
                limit = task.payload.get('limit', 100)
                raw_sql = task.payload.get('raw_sql')
                
                if raw_sql:
                    df = self.connection.execute_raw(raw_sql, limit)
                elif column and value:
                    df = self.connection.search(table, column, value, limit)
                else:
                    df = self.connection.preview_table(table, limit)
                
                return TaskResult(task.task_type, True, df, callback_id=task.callback_id)
            
            return TaskResult(task.task_type, False, error=f"Unknown task: {task.task_type}")
            
        except Exception as e:
            return TaskResult(task.task_type, False, error=str(e), callback_id=task.callback_id)


class StreamWorker(QObject):
    """
    Dedicated worker for streaming table changes.
    Uses polling with watermark tracking.
    Separate from main worker to not block queries.
    Creates its own connection to avoid thread-safety issues.
    """
    
    new_rows = pyqtSignal(object)  # StreamEvent
    error = pyqtSignal(str)
    status_changed = pyqtSignal(str)  # "running", "stopped", "error"
    
    def __init__(self, db_config: DbConfig):
        super().__init__()
        self.db_config = db_config
        self.connection: Optional[DatabaseConnection] = None
        self._subscriptions: Dict[str, StreamConfig] = {}  # table_name -> config
        self._watermarks: Dict[str, Any] = {}  # table_name -> last watermark value
        self._running = False
        self._thread: Optional[Thread] = None
        self._poll_queue: Queue[str] = Queue()  # Commands: "stop", table names to check
    
    def subscribe(self, config: StreamConfig) -> None:
        """Subscribe to changes on a table"""
        table = config.table_name
        self._subscriptions[table] = config
        
        if not self._running:
            self.start()
        else:
            # Initialize watermark for new subscription
            try:
                if self.connection:
                    current_max = self.connection.get_max_watermark(table, config.watermark_column)
                    self._watermarks[table] = current_max
            except Exception as e:
                self.error.emit(f"Failed to get watermark for {table}: {e}")
    
    def unsubscribe(self, table_name: str) -> None:
        """Unsubscribe from a table"""
        self._subscriptions.pop(table_name, None)
        self._watermarks.pop(table_name, None)
        
        if not self._subscriptions:
            self.stop()
    
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._worker_main, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._poll_queue.put("stop")
        if self._thread:
            self._thread.join(timeout=2.0)
        if self.connection:
            self.connection.close()
            self.connection = None
        self.status_changed.emit("stopped")
    
    def _worker_main(self) -> None:
        """Main worker thread - creates its own connection"""
        try:
            # Create connection in this thread
            self.connection = DatabaseConnection(self.db_config)
            self.connection.connect()
            self.status_changed.emit("running")
            
            # Initialize watermarks for all subscriptions
            for table, config in self._subscriptions.items():
                try:
                    current_max = self.connection.get_max_watermark(table, config.watermark_column)
                    self._watermarks[table] = current_max
                except Exception as e:
                    self.error.emit(f"Failed to get watermark for {table}: {e}")
            
            # Start polling loop
            self._poll_loop()
            
        except Exception as e:
            self.error.emit(f"Stream worker connection error: {e}")
            self.status_changed.emit("error")
        finally:
            if self.connection:
                self.connection.close()
                self.connection = None
    
    def _poll_loop(self) -> None:
        """Main polling loop"""
        while self._running:
            # Calculate minimum poll interval across all subscriptions
            if not self._subscriptions:
                time.sleep(0.1)
                continue
            
            min_interval = min(c.poll_interval_ms for c in self._subscriptions.values())
            
            for table_name, config in list(self._subscriptions.items()):
                if not self._running:
                    break
                
                try:
                    self._poll_table(table_name, config)
                except Exception as e:
                    self.error.emit(f"Poll error for {table_name}: {e}")
            
            # Sleep for the poll interval
            time.sleep(min_interval / 1000.0)
    
    def _poll_table(self, table_name: str, config: StreamConfig) -> None:
        """Poll a single table for new rows"""
        if not self.connection:
            return
        
        last_watermark = self._watermarks.get(table_name)
        
        df = self.connection.get_rows_after_watermark(
            table_name=table_name,
            watermark_column=config.watermark_column,
            watermark_value=last_watermark,
            limit=config.batch_size
        )
        
        if len(df) > 0:
            # Update watermark to max value in results
            new_watermark = df[config.watermark_column].max()
            self._watermarks[table_name] = new_watermark
            
            event = StreamEvent(
                table_name=table_name,
                rows=df,
                watermark_value=new_watermark
            )
            self.new_rows.emit(event)


class NotifyStreamWorker(QObject):
    """
    PostgreSQL-specific worker using LISTEN/NOTIFY.
    Zero polling - instant notifications.
    """
    
    new_row = pyqtSignal(object)  # dict (single row as JSON)
    error = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    
    def __init__(self, db_config: DbConfig):
        super().__init__()
        self.db_config = db_config
        self._channels: Dict[str, str] = {}  # channel_name -> table_name
        self._running = False
        self._thread: Optional[Thread] = None
    
    def subscribe(self, table_name: str, channel_name: str) -> None:
        """Subscribe to NOTIFY on a channel"""
        self._channels[channel_name] = table_name
        
        if not self._running:
            self.start()
    
    def unsubscribe(self, channel_name: str) -> None:
        self._channels.pop(channel_name, None)
        if not self._channels:
            self.stop()
    
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        self.status_changed.emit("running")
    
    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.status_changed.emit("stopped")
    
    def _listen_loop(self) -> None:
        """Main listen loop using raw psycopg2 connection"""
        import select
        import psycopg2
        import json
        
        try:
            conn = psycopg2.connect(self.db_config.url)
            conn.set_isolation_level(0)  # Autocommit for LISTEN
            cursor = conn.cursor()
            
            # Subscribe to all channels
            for channel in self._channels.keys():
                cursor.execute(f"LISTEN {channel};")
            
            while self._running:
                if select.select([conn], [], [], 1.0) != ([], [], []):
                    conn.poll()
                    while conn.notifies:
                        notify = conn.notifies.pop(0)
                        try:
                            row_data = json.loads(notify.payload)
                            self.new_row.emit({
                                'channel': notify.channel,
                                'table': self._channels.get(notify.channel),
                                'row': row_data
                            })
                        except json.JSONDecodeError:
                            self.error.emit(f"Invalid JSON in notify: {notify.payload}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.error.emit(f"LISTEN error: {e}")
            self.status_changed.emit("error")


# ============================================================================
# TABLE MODEL
# ============================================================================

class DataFrameModel(QAbstractTableModel):
    """Qt model wrapping a pandas DataFrame with sorting support"""
    
    def __init__(self, df: pd.DataFrame = None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()
        self._df_display = self._df.copy() if not self._df.empty else pd.DataFrame()
    
    def set_dataframe(self, df: pd.DataFrame):
        self.beginResetModel()
        self._df = df
        self._df_display = self._df.copy() if not self._df.empty else pd.DataFrame()
        self.endResetModel()
    
    def sort(self, column: int, order):
        """Sort table by given column"""
        if self._df.empty:
            return
        
        self.layoutAboutToBeChanged.emit()
        
        col_name = self._df.columns[column]
        ascending = (order == Qt.SortOrder.AscendingOrder)
        
        try:
            self._df_display = self._df.sort_values(
                by=col_name, 
                ascending=ascending,
                na_position='last'
            ).reset_index(drop=True)
        except Exception as e:
            # If sorting fails (e.g., mixed types), fall back to string sort
            self._df_display = self._df.copy()
            self._df_display[col_name] = self._df_display[col_name].astype(str)
            self._df_display = self._df_display.sort_values(
                by=col_name,
                ascending=ascending
            ).reset_index(drop=True)
        
        self.layoutChanged.emit()
    
    def rowCount(self, parent=None) -> int:
        return len(self._df_display)
    
    def columnCount(self, parent=None) -> int:
        return len(self._df_display.columns) if not self._df_display.empty else 0
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._df_display.iloc[index.row(), index.column()]
            # Truncate long values for display
            s = str(value)
            return s[:200] + "..." if len(s) > 200 else s
        return None
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._df_display.columns[section]) if not self._df_display.empty else ""
            return str(section)
        return None


# ============================================================================
# DIALOGS
# ============================================================================

class ConnectionDialog(QDialog):
    """Database connection dialog with explicit fields"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to Database")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Connection type
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["PostgreSQL", "SQLite", "MySQL", "Custom URL"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        type_row.addWidget(self.type_combo)
        layout.addLayout(type_row)
        
        # URL field (for custom)
        self.url_field = QLineEdit()
        self.url_field.setPlaceholderText("postgresql://user:pass@host:2345/dbname")
        layout.addWidget(QLabel("Connection URL:"))
        layout.addWidget(self.url_field)
        
        # Individual fields
        self.fields_widget = QWidget()
        fields_layout = QVBoxLayout(self.fields_widget)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        
        self.host_field = QLineEdit("192.168.0.100")
        self.port_field = QSpinBox()
        self.port_field.setRange(1, 65535)
        self.port_field.setValue(2345)
        self.user_field = QLineEdit('solcatcher')
        self.pass_field = QLineEdit(get_env_value('SOLCATCHER_POSTGRESQL_PASS'))
        self.pass_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_field = QLineEdit('solcatcher')
        self.path_field = QLineEdit()  # For SQLite
        
        for label, widget in [
            ("Host:", self.host_field),
            ("Port:", self.port_field),
            ("User:", self.user_field),
            ("Password:", self.pass_field),
            ("Database:", self.db_field),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(70)
            row.addWidget(lbl)
            row.addWidget(widget)
            fields_layout.addLayout(row)
        
        # SQLite path (hidden by default)
        self.sqlite_widget = QWidget()
        sqlite_layout = QHBoxLayout(self.sqlite_widget)
        sqlite_layout.setContentsMargins(0, 0, 0, 0)
        sqlite_layout.addWidget(QLabel("Path:"))
        sqlite_layout.addWidget(self.path_field)
        self.sqlite_widget.hide()
        
        layout.addWidget(self.fields_widget)
        layout.addWidget(self.sqlite_widget)
        
        # Buttons
        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.cancel_btn = QPushButton("Cancel")
        self.connect_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)
        
        self._on_type_changed("PostgreSQL")
    
    def _on_type_changed(self, type_name: str):
        is_custom = type_name == "Custom URL"
        is_sqlite = type_name == "SQLite"
        
        self.url_field.setVisible(is_custom)
        self.fields_widget.setVisible(not is_custom and not is_sqlite)
        self.sqlite_widget.setVisible(is_sqlite)
        
        if type_name == "PostgreSQL":
            self.port_field.setValue(2345)
        elif type_name == "MySQL":
            self.port_field.setValue(3306)
    
    def get_config(self) -> Optional[DbConfig]:
        type_name = self.type_combo.currentText()
        
        if type_name == "Custom URL":
            url = self.url_field.text().strip()
            return DbConfig(url=url) if url else None
        
        if type_name == "SQLite":
            path = self.path_field.text().strip()
            return DbConfig.sqlite(path) if path else None
        
        dialect = "postgresql" if type_name == "PostgreSQL" else "mysql+pymysql"
        
        return DbConfig.from_parts(
            dialect=dialect,
            user=self.user_field.text(),
            password=self.pass_field.text(),
            host=self.host_field.text(),
            port=self.port_field.value(),
            database=self.db_field.text()
        )


# ============================================================================
# MAIN WINDOW
# ============================================================================

class DatabaseViewer(QMainWindow):
    """
    Main database viewer window.
    Uses queue-based worker, no blocking operations on UI thread.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Database Viewer")
        self.resize(1200, 800)
        
        # State
        self.current_table: Optional[str] = None
        self.column_types: Dict[str, str] = {}
        self.columns_list_data: List[str] = []
        
        # Worker
        self.worker = DatabaseWorker()
        self.worker.result_ready.connect(self._on_result)
        self.worker.start()
        
        # Stream worker (created when connection established)
        self.stream_worker: Optional[StreamWorker] = None
        self.streaming_tables: set = set()
        
        self._build_ui()
    



# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    app = QApplication(sys.argv)
    window = DatabaseViewer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
