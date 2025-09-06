from ..imports import *
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QTableWidget, QTextEdit, QAbstractItemView
from PyQt6.QtCore import Qt

def _build_ui(self):
    try:
        if self.layout() is None:
            layout = QVBoxLayout(self)
        else:
            layout = self.layout()

        # Base URL selection
        layout.addWidget(QLabel("Base URL:"))
        self.base_combo = QComboBox(self)
        self.base_combo.setEditable(True)
        self.base_combo.addItems([url for url, _ in PREDEFINED_BASE_URLS])
        self.base_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        layout.addWidget(self.base_combo)

        # API Prefix
        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("API Prefix:"))
        self.api_prefix_in = QLineEdit(self.api_prefix, self)
        self.api_prefix_in.setPlaceholderText("/api")
        self.api_prefix_in.setClearButtonEnabled(True)
        self.api_prefix_in.textChanged.connect(self._on_api_prefix_changed)
        api_row.addWidget(self.api_prefix_in)

        detect_btn = QPushButton("Detect", self)
        detect_btn.clicked.connect(self.detect_api_prefix)
        api_row.addWidget(detect_btn)
        layout.addLayout(api_row)

        # Fetch remote endpoints button
        self.fetch_button = QPushButton(self._fetch_label(), self)
        self.fetch_button.clicked.connect(self.fetch_remote_endpoints)
        layout.addWidget(self.fetch_button)

        # Endpoints table
        layout.addWidget(QLabel("Endpoints (select one row):"))
        self.endpoints_table = QTableWidget(0, 2, self)
        self.endpoints_table.setHorizontalHeaderLabels(["Endpoint Path", "Methods"])
        self.endpoints_table.horizontalHeader().setStretchLastSection(True)
        self.endpoints_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.endpoints_table.setFixedHeight(200)
        self.endpoints_table.cellClicked.connect(self.on_endpoint_selected)
        layout.addWidget(self.endpoints_table)

        # Method override selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Override Method:"))
        self.method_box = QComboBox(self)
        self.method_box.addItems(["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
        row.addWidget(self.method_box)
        layout.addLayout(row)

        # Headers table
        layout.addWidget(QLabel("Headers (check to include):"))
        self.headers_table = QTableWidget(len(PREDEFINED_HEADERS)+1, 3, self)
        self.headers_table.setHorizontalHeaderLabels(["Use", "Key", "Value"])
        self.headers_table.setFixedHeight(200)
        layout.addWidget(self.headers_table)
        for i, (k, v) in enumerate(PREDEFINED_HEADERS):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked)
            self.headers_table.setItem(i, 0, chk)
            self.headers_table.setItem(i, 1, QTableWidgetItem(k))
            self.headers_table.setItem(i, 2, QTableWidgetItem(v))
        empty_chk = QTableWidgetItem()
        empty_chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        empty_chk.setCheckState(Qt.CheckState.Unchecked)
        self.headers_table.setItem(len(PREDEFINED_HEADERS), 0, empty_chk)
        self.headers_table.setItem(len(PREDEFINED_HEADERS), 1, QTableWidgetItem(""))
        self.headers_table.setItem(len(PREDEFINED_HEADERS), 2, QTableWidgetItem(""))
        self.headers_table.cellChanged.connect(self._maybe_add_header_row)

        # Body / Query-Params table
        layout.addWidget(QLabel("Body / Query-Params (key → value):"))
        self.body_table = QTableWidget(1, 2, self)
        self.body_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.body_table.setFixedHeight(200)
        self.body_table.setItem(0, 0, QTableWidgetItem(""))
        self.body_table.setItem(0, 1, QTableWidgetItem(""))
        self.body_table.cellChanged.connect(self._maybe_add_body_row)
        layout.addWidget(self.body_table)

        # Send button
        self.send_button = QPushButton("▶ Send Request", self)
        self.send_button.clicked.connect(self.send_request)
        layout.addWidget(self.send_button)

        # Response
        layout.addWidget(QLabel("Response:"))
        self.response_output = QTextEdit(self)
        self.response_output.setReadOnly(True)
        self.response_output.setFixedHeight(200)
        layout.addWidget(self.response_output)

        # Logs
        layout.addWidget(QLabel("Logs:"))
        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(150)
        layout.addWidget(self.log_output)
    except Exception as e:
        logging.error(f"_build_ui error: {e}", exc_info=True)
        raise
