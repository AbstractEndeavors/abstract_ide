from __future__ import annotations
import enum
from ..imports import *
import inspect
import PyQt6
from PyQt6 import QtWidgets,QtCore
import inspect



def _build_ui(self):
        if self.layout() is None:
                layout = QVBoxLayout(self)
        else:
                layout = self.layout()

        # Base URL combo
        self.base_combo = createCombo(
        self,
        label="Base URL:",
        items=PREDEFINED_BASE_URLS,
        attr_name="base_combo",
        connect=self._on_base_changed,
        insertPolicy="NoInsert",
        editable=True
        )
        layout.addWidget(self.base_combo)

        # API Prefix input
        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("API Prefix:"))
        self.api_prefix_in = QLineEdit(self)
        self.api_prefix_in.setText("/api")
        self.api_prefix_in.textChanged.connect(self._on_api_prefix_changed)
        api_row.addWidget(self.api_prefix_in)

        createButton(api_row,
        widget_cls=QPushButton,
        label="Detect",
        connect=lambda: self.detect_api_prefix(None, None)
        )
        layout.addLayout(api_row)
        #self.base_combo.currentIndexChanged.connect(self._on_base_changed)

        # Fetch remote endpoints button (label now dynamic)
        self.fetch_button = QPushButton(self._fetch_label())
        layout.addWidget(self.fetch_button)
        self.fetch_button.clicked.connect(self.fetch_remote_endpoints)
        # Endpoints table
        layout.addWidget(QLabel("Endpoints (select one row):"))
        self.endpoints_table = QTableWidget(0, 2)
        self.endpoints_table.setHorizontalHeaderLabels(["Endpoint Path", "Methods"])
        self.endpoints_table.horizontalHeader().setStretchLastSection(True)
        self.endpoints_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        layout.addWidget(self.endpoints_table)
        self.endpoints_table.cellClicked.connect(self.on_endpoint_selected)
        # Method override selector
        self.methodComboInit(layout)
       
        # 4 columns: Use | Key | Value | Modular
        self.headers_table = QTableWidget(len(PREDEFINED_HEADERS) + 1, 4)
        self.headers_table.setHorizontalHeaderLabels(["Use", "Key", "Value", "Modular"])
        self.headers_table.horizontalHeader().setStretchLastSection(False)
        self.headers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.headers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.headers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.headers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.headers_table.setColumnWidth(2, 260)  # Value
        self.headers_table.setColumnWidth(3, 260)  # Modular (Type)
        layout.addWidget(self.headers_table)
        # keep references to row widgets
        self._row_type_boxes = {}
        self._row_value_boxes = {}
        # Fill rows
        for i, (k, v) in enumerate(PREDEFINED_HEADERS):
            # Use (checkbox)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked)
            self.headers_table.setItem(i, 0, chk)
            # key / value cells
            self.headers_table.setItem(i, 1, QTableWidgetItem(k))
            if k != "Authorization":
                value_cb = self._make_value_combo(i)
                type_cb = self._make_type_combo(i)
                self.headers_table.setCellWidget(i, 2, value_cb)
                self.headers_table.setCellWidget(i, 3, type_cb)
            else:
                self.headers_table.setItem(i, 2, QTableWidgetItem(v))
        # add a blank row at the end (optional)
        # blank row
        empty_chk = QTableWidgetItem()
        empty_chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        empty_chk.setCheckState(Qt.CheckState.Unchecked)
        self.headers_table.setItem(len(PREDEFINED_HEADERS), 0, empty_chk)
        self.headers_table.setItem(len(PREDEFINED_HEADERS), 1, QTableWidgetItem(""))
        self.headers_table.setItem(len(PREDEFINED_HEADERS), 2, QTableWidgetItem(""))
        self.headers_table.cellChanged.connect(self._maybe_add_header_row)
        # Body / Query-Params table
        layout.addWidget(QLabel("Body / Query-Params (key → value):"))
        self.body_table = QTableWidget(1, 2)
        self.body_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.body_table.setMinimumHeight(120)
        self.body_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.body_table)
        # initial blank row
        self.body_table.setItem(0, 0, QTableWidgetItem(""))
        self.body_table.setItem(0, 1, QTableWidgetItem(""))
        self.body_table.cellChanged.connect(self._maybe_add_body_row)
        # Send button
        self.send_button = QPushButton("▶ Send Request")
        layout.addWidget(self.send_button)
        self.send_button.clicked.connect(self.send_request)
        # Response
        layout.addWidget(QLabel("Response:"))
        self.response_output = QTextEdit()
        self.response_output.setReadOnly(True)
        self.response_output.setMinimumHeight(120)
        self.response_output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.response_output)
        # Append Response
        self.append_chk = QCheckBox("Append responses")
        self.append_chk.setChecked(True)
        layout.addWidget(self.append_chk)
        # Logs toggle + area
        toggle_row = QHBoxLayout()
        self.toggle_logs = QPushButton("Show Logs")
        self.toggle_logs.setCheckable(True)
        self.toggle_logs.setChecked(False)
        self.toggle_logs.toggled.connect(lambda on: (
            self.log_output.setVisible(on),
            self.toggle_logs.setText("Hide Logs" if on else "Show Logs")
        ))
        toggle_row.addWidget(self.toggle_logs)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        layout.addWidget(QLabel("Logs:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(80)
        self.log_output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log_output.setVisible(False)  # start hidden
        layout.addWidget(self.log_output)


        # after you add everything to layout in order, assign stretch:
        # 0..N refer to widgets/layouts in the order you added them
        layout.setStretch(layout.indexOf(self.endpoints_table), 2)
        layout.setStretch(layout.indexOf(self.headers_table),   3)
        layout.setStretch(layout.indexOf(self.body_table),      2)
        layout.setStretch(layout.indexOf(self.response_output), 3)
        layout.setStretch(layout.indexOf(self.log_output),      1)

        # make the light “form” rows not stretch
        layout.setStretch(layout.indexOf(self.base_combo),      0)
        layout.setStretch(layout.indexOf(self.fetch_button),    0)
