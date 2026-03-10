from ..imports import *
def _build_ui(self):
    central = QWidget()
    self.setCentralWidget(central)
    
    main_layout = QVBoxLayout(central)
    
    # Toolbar
    toolbar = QHBoxLayout()
    self.connect_btn = QPushButton("Connect")
    self.refresh_btn = QPushButton("Refresh")
    self.status_label = QLabel("Not connected")
    
    self.connect_btn.clicked.connect(self._on_connect)
    self.refresh_btn.clicked.connect(self._on_refresh)
    self.refresh_btn.setEnabled(False)
    
    toolbar.addWidget(self.connect_btn)
    toolbar.addWidget(self.refresh_btn)
    toolbar.addStretch()
    toolbar.addWidget(self.status_label)
    main_layout.addLayout(toolbar)
    
    # Main splitter
    splitter = QSplitter(Qt.Orientation.Horizontal)
    
    # Left panel - tables and columns
    left_panel = QWidget()
    left_layout = QVBoxLayout(left_panel)
    left_layout.setContentsMargins(0, 0, 0, 0)
    
    left_layout.addWidget(QLabel("Tables:"))
    self.tables_list = QListWidget()
    self.tables_list.itemClicked.connect(self._on_table_selected)
    left_layout.addWidget(self.tables_list)
    
    left_layout.addWidget(QLabel("Columns:"))
    self.columns_list = QListWidget()
    left_layout.addWidget(self.columns_list)
    
    # Stream controls
    stream_group = QWidget()
    stream_layout = QVBoxLayout(stream_group)
    stream_layout.setContentsMargins(0, 10, 0, 0)
    stream_layout.addWidget(QLabel("Stream Settings:"))
    
    watermark_row = QHBoxLayout()
    watermark_row.addWidget(QLabel("Track:"))
    self.watermark_combo = QComboBox()
    self.watermark_combo.setToolTip("Column to track for new rows (e.g., id, created_at)")
    watermark_row.addWidget(self.watermark_combo)
    stream_layout.addLayout(watermark_row)
    
    interval_row = QHBoxLayout()
    interval_row.addWidget(QLabel("Poll:"))
    self.poll_interval = QSpinBox()
    self.poll_interval.setRange(100, 60000)
    self.poll_interval.setValue(1000)
    self.poll_interval.setSuffix(" ms")
    self.poll_interval.setToolTip("How often to check for new rows")
    interval_row.addWidget(self.poll_interval)
    stream_layout.addLayout(interval_row)
    
    self.watch_btn = QPushButton("â–¶ Watch")
    self.watch_btn.setCheckable(True)
    self.watch_btn.setEnabled(False)
    self.watch_btn.clicked.connect(self._on_watch_toggle)
    stream_layout.addWidget(self.watch_btn)
    
    left_layout.addWidget(stream_group)
    
    splitter.addWidget(left_panel)
    
    # Right panel - query and results
    right_panel = QWidget()
    right_layout = QVBoxLayout(right_panel)
    right_layout.setContentsMargins(0, 0, 0, 0)
    
    # Search bar
    search_layout = QHBoxLayout()
    self.search_column = QComboBox()
    self.search_column.setMinimumWidth(150)
    self.search_value = QLineEdit()
    self.search_value.setPlaceholderText("Search value...")
    self.search_value.returnPressed.connect(self._on_search)
    self.search_btn = QPushButton("Search")
    self.search_btn.clicked.connect(self._on_search)
    
    self.limit_spin = QSpinBox()
    self.limit_spin.setRange(10, 10000)
    self.limit_spin.setValue(100)
    self.limit_spin.setPrefix("Limit: ")
    
    search_layout.addWidget(self.search_column)
    search_layout.addWidget(self.search_value)
    search_layout.addWidget(self.search_btn)
    search_layout.addWidget(self.limit_spin)
    right_layout.addLayout(search_layout)
    
    # Tab widget for Results and Stream
    from PyQt6.QtWidgets import QTabWidget
    self.results_tabs = QTabWidget()
    
    # Results tab
    results_widget = QWidget()
    results_layout = QVBoxLayout(results_widget)
    results_layout.setContentsMargins(0, 0, 0, 0)
    self.table_view = QTableView()
    self.table_model = DataFrameModel()
    self.table_view.setModel(self.table_model)
    self.table_view.setSortingEnabled(True)  # Enable column sorting
    self.table_view.horizontalHeader().setStretchLastSection(True)
    results_layout.addWidget(self.table_view)
    self.results_tabs.addTab(results_widget, "Results")
    
    # Stream tab
    stream_widget = QWidget()
    stream_tab_layout = QVBoxLayout(stream_widget)
    stream_tab_layout.setContentsMargins(0, 0, 0, 0)
    
    stream_header = QHBoxLayout()
    self.stream_status = QLabel("Not streaming")
    self.stream_count = QLabel("0 rows")
    self.clear_stream_btn = QPushButton("Clear")
    self.clear_stream_btn.clicked.connect(self._on_clear_stream)
    stream_header.addWidget(self.stream_status)
    stream_header.addStretch()
    stream_header.addWidget(self.stream_count)
    stream_header.addWidget(self.clear_stream_btn)
    stream_tab_layout.addLayout(stream_header)
    
    self.stream_view = QTableView()
    self.stream_model = DataFrameModel()
    self.stream_view.setModel(self.stream_model)
    self.stream_view.setSortingEnabled(True)  # Enable column sorting
    self.stream_view.horizontalHeader().setStretchLastSection(True)
    stream_tab_layout.addWidget(self.stream_view)
    
    self.results_tabs.addTab(stream_widget, "Stream (0)")
    
    # Log console
    self.log_console = QTextEdit()
    self.log_console.setReadOnly(True)
    self.log_console.setMaximumHeight(150)
    
    results_splitter = QSplitter(Qt.Orientation.Vertical)
    results_splitter.addWidget(self.results_tabs)
    results_splitter.addWidget(self.log_console)
    results_splitter.setStretchFactor(0, 3)
    results_splitter.setStretchFactor(1, 1)
    
    right_layout.addWidget(results_splitter)
    
    splitter.addWidget(right_panel)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 3)
    
    main_layout.addWidget(splitter)
    
    # Stream data storage
    self._stream_data = pd.DataFrame()
    self._stream_row_count = 0
