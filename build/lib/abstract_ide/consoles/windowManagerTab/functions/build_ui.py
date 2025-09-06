from ..imports import *
# ---------------- UI ------------------------------------------------------
def _build_ui(self) -> None:
    central = QWidget(self)
    self.setCentralWidget(central)
    outer = QVBoxLayout(central)

    # filter row
    filt = QHBoxLayout()
    self.search_edit = QLineEdit()
    self.search_edit.setPlaceholderText("Search titles…")
    self.search_edit.textChanged.connect(self.update_table)
    filt.addWidget(self.search_edit)

    self.type_combo = QComboBox()
    self.type_combo.addItems(["All", "Browser", "Editor", "Terminal", "Other"])
    self.type_combo.currentIndexChanged.connect(self.update_table)
    filt.addWidget(self.type_combo)

    sel_type_btn = QPushButton("Select‑All (type)")
    sel_type_btn.clicked.connect(self.select_all_by_type)
    filt.addWidget(sel_type_btn)

    open_btn = QPushButton("Open File…")
    open_btn.clicked.connect(self.open_file)
    filt.addWidget(open_btn)

    outer.addLayout(filt)

    # table
    self.table = QTableWidget()
    self.table.setColumnCount(len(self.COLS))
    self.table.setHorizontalHeaderLabels(self.COLS)
    self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
    self.table.itemDoubleClicked.connect(self.activate_window)
    outer.addWidget(self.table, stretch=1)

    # control panel
    ctrl = QHBoxLayout()
    self.monitor_combo = QComboBox(); ctrl.addWidget(self.monitor_combo)

    mv_btn = QPushButton("Move to Monitor"); mv_btn.clicked.connect(self.move_window); ctrl.addWidget(mv_btn)
    mn_btn = QPushButton("Minimize"); mn_btn.clicked.connect(lambda: self.control_window("minimize")); ctrl.addWidget(mn_btn)
    mx_btn = QPushButton("Maximize"); mx_btn.clicked.connect(lambda: self.control_window("maximize")); ctrl.addWidget(mx_btn)
    cls_all_btn = QPushButton("Close Selected (all)"); cls_all_btn.clicked.connect(lambda: self.close_selected(True)); ctrl.addWidget(cls_all_btn)
    cls_saved_btn = QPushButton("Close Selected (saved)"); cls_saved_btn.clicked.connect(lambda: self.close_selected(False)); ctrl.addWidget(cls_saved_btn)
    rf_btn = QPushButton("Refresh"); rf_btn.clicked.connect(self.refresh); ctrl.addWidget(rf_btn)

    outer.addLayout(ctrl)
    self.setStatusBar(QStatusBar())
