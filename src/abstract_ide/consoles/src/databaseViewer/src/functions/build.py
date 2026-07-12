from ..imports import *
from PyQt6.QtWidgets import QTabWidget


def _build_ui(self):
    central = QWidget()
    self.setCentralWidget(central)
    root = QVBoxLayout(central)

    # ---------- top bar: connect / refresh / status ----------
    top = QHBoxLayout()
    self.connect_btn = QPushButton("Connect")
    self.connect_btn.clicked.connect(self._on_connect)
    self.refresh_btn = QPushButton("Refresh")
    self.refresh_btn.clicked.connect(self._on_refresh)
    self.refresh_btn.setEnabled(False)
    self.status_label = QLabel("Not connected")
    top.addWidget(self.connect_btn)
    top.addWidget(self.refresh_btn)
    top.addWidget(self.status_label)
    top.addStretch()
    root.addLayout(top)

    # ---------- outer vertical splitter: work area over log ----------
    outer = QSplitter(Qt.Orientation.Vertical)
    root.addWidget(outer)

    work = QSplitter(Qt.Orientation.Horizontal)
    outer.addWidget(work)

    # ----- left panel: tables, columns, stream settings, search -----
    left = QWidget()
    left_lay = QVBoxLayout(left)
    left_lay.setContentsMargins(0, 0, 0, 0)

    left_lay.addWidget(QLabel("Tables:"))
    self.tables_list = QListWidget()
    self.tables_list.itemClicked.connect(self._on_table_selected)
    left_lay.addWidget(self.tables_list)

    left_lay.addWidget(QLabel("Columns:"))
    self.columns_list = QListWidget()
    left_lay.addWidget(self.columns_list)

    left_lay.addWidget(QLabel("Stream Settings:"))
    track_row = QHBoxLayout()
    track_row.addWidget(QLabel("Track:"))
    self.watermark_combo = QComboBox()
    self.watermark_combo.setToolTip("Column to track for new rows (e.g., id, created_at)")
    track_row.addWidget(self.watermark_combo)
    left_lay.addLayout(track_row)

    poll_row = QHBoxLayout()
    poll_row.addWidget(QLabel("Poll:"))
    self.poll_interval = QSpinBox()
    self.poll_interval.setRange(100, 60000)
    self.poll_interval.setValue(1000)
    self.poll_interval.setSuffix(" ms")
    self.poll_interval.setToolTip("How often to check for new rows")
    poll_row.addWidget(self.poll_interval)
    left_lay.addLayout(poll_row)

    self.watch_btn = QPushButton("▶ Watch")
    self.watch_btn.setCheckable(True)
    self.watch_btn.setEnabled(False)
    self.watch_btn.clicked.connect(self._on_watch_toggle)
    left_lay.addWidget(self.watch_btn)

    # search row
    search_row = QHBoxLayout()
    self.search_column = QComboBox()
    self.search_column.setMinimumWidth(120)
    self.search_value = QLineEdit()
    self.search_value.setPlaceholderText("Search value...")
    self.search_value.returnPressed.connect(self._on_search)
    self.search_btn = QPushButton("Search")
    self.search_btn.clicked.connect(self._on_search)
    self.limit_spin = QSpinBox()
    self.limit_spin.setPrefix("Limit: ")
    self.limit_spin.setRange(1, 100000)
    self.limit_spin.setValue(100)
    search_row.addWidget(self.search_column)
    search_row.addWidget(self.search_value)
    search_row.addWidget(self.search_btn)
    search_row.addWidget(self.limit_spin)
    left_lay.addLayout(search_row)

    work.addWidget(left)

    # ----- right panel: results / stream tabs -----
    self.results_tabs = QTabWidget()

    self.table_view = QTableView()
    self.table_model = DataFrameModel()
    self.table_view.setModel(self.table_model)
    self.table_view.setSortingEnabled(True)
    self.table_view.horizontalHeader().setStretchLastSection(True)
    self.results_tabs.addTab(self.table_view, "Results")

    stream_tab = QWidget()
    stream_lay = QVBoxLayout(stream_tab)
    stream_bar = QHBoxLayout()
    self.stream_status = QLabel("Not streaming")
    self.stream_count = QLabel("0 rows")
    self.clear_stream_btn = QPushButton("Clear")
    self.clear_stream_btn.clicked.connect(self._on_clear_stream)
    stream_bar.addWidget(self.stream_status)
    stream_bar.addWidget(self.stream_count)
    stream_bar.addStretch()
    stream_bar.addWidget(self.clear_stream_btn)
    stream_lay.addLayout(stream_bar)
    self.stream_view = QTableView()
    self.stream_model = DataFrameModel()
    self.stream_view.setModel(self.stream_model)
    self.stream_view.setSortingEnabled(True)
    stream_lay.addWidget(self.stream_view)
    self.results_tabs.addTab(stream_tab, "Stream (0)")

    work.addWidget(self.results_tabs)
    work.setStretchFactor(1, 3)

    # ----- log console at the bottom -----
    self.log_console = QTextEdit()
    self.log_console.setReadOnly(True)
    self.log_console.setMaximumHeight(150)
    outer.addWidget(self.log_console)
    outer.setStretchFactor(0, 5)

    # stream accumulation state
    self._stream_data = pd.DataFrame()
    self._stream_row_count = 0
