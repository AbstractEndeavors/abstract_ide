# functionsTab/functionsTab/functions/build_ui.py
from ..imports import *
##from abstract_gui.QT6. import attach_textedit_to_logs

def _build_ui(self):
    root = QHBoxLayout(self)

    # ---------- left panel (project/scan + tabs) ----------
    left = QVBoxLayout()

    # project row (unchanged)
    row = QHBoxLayout()
    row.addWidget(QLabel("Project Path:"))
    self.path_in = QLineEdit(self.init_path)
    self.path_in.setPlaceholderText("Folder containing package.json / source")
    row.addWidget(self.path_in, 1)
    row.addWidget(QLabel("Scope:"))
    self.scope_combo = QComboBox(); self.scope_combo.addItems(["all", "reachable"])
    row.addWidget(self.scope_combo)
    left.addLayout(row)

    self.btn_scan = QPushButton("Scan Project")
    left.addWidget(self.btn_scan)
    self.init_functions_button_tab()
    self.init_variables_button_tab()
    # ---- NEW: tabs for Functions / Variables chips -----------------

    left.addWidget(self.tabs)

    # ---------- right panel (reuse for both kinds) ----------
    right = QVBoxLayout()
    right.addWidget(QLabel("Exported In"))
    self.exporters_list = QListWidget(); right.addWidget(self.exporters_list)
    right.addWidget(QLabel("Imported In"))
    self.importers_list = QListWidget(); right.addWidget(self.importers_list)
    right.addWidget(QLabel("Log"))
    self.log_view = QTextEdit(); self.log_view.setReadOnly(True); right.addWidget(self.log_view)
##    try:
##        attach_textedit_to_logs(self.log_view, tail_file=None)
##    except Exception:
##        pass

    root.addLayout(left, 1)
    root.addLayout(right, 2)

    # ---------- wiring ----------
    self.btn_scan.clicked.connect(lambda: self.scanRequested.emit(self.scope_combo.currentText()))
    self.scanRequested.connect(self._start_func_scan)

    # functions
    self.search_fn.textChanged.connect(self._filter_fn_buttons)
    self.rb_fn_source.toggled.connect(lambda _: self._on_fn_filter_mode_changed())
    self.rb_fn_io.toggled.connect(    lambda _: self._on_fn_filter_mode_changed())
    self.rb_fn_all.toggled.connect(   lambda _: self._on_fn_filter_mode_changed())

    # variables
    self.search_var.textChanged.connect(self._filter_var_buttons)
    self.rb_var_source.toggled.connect(lambda _: self._on_var_filter_mode_changed())
    self.rb_var_io.toggled.connect(    lambda _: self._on_var_filter_mode_changed())
    self.rb_var_all.toggled.connect(   lambda _: self._on_var_filter_mode_changed())

    # optional: double-click open in editor
    self.exporters_list.itemDoubleClicked.connect(lambda it: os.system(f'code -g "{it.text()}"'))
    self.importers_list.itemDoubleClicked.connect(lambda it: os.system(f'code -g "{it.text()}"'))
