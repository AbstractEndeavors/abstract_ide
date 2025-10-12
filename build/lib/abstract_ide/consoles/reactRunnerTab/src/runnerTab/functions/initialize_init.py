from ...imports import *
def _on_path_changed(self, new_text: str):
    self.init_path = new_text.strip()
def initializeInit(self):
    self.fn_filter_mode = "io"   # "source" | "io" | "all"
    self.current_fn = None       # last clicked function name

    self.setWindowTitle("🔍 React Build Finder")
    self.resize(1100, 720)

    self.cb_try_alt_ext = QCheckBox("Try alternate extensions")
    self.cb_try_alt_ext.setChecked(True)

    # state
    self.last_output = ""
    self.last_errors_only = ""
    self.last_warnings_only = ""
    self.last_all_only = ""
    self.parsed_logs = {'entries': [], 'by_file': {}}

    # editor state
    self.current_file_path = None
    self.original_text = ""

    # editor widgets (wired into layout in runnerTab/main.py)
    self.editor = QPlainTextEdit()
    self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    try:
        f = self.editor.font(); f.setFamily("Fira Code"); f.setStyleHint(QFont.StyleHint.Monospace); f.setFixedPitch(True)
        self.editor.setFont(f)
    except Exception:
        pass
    self.btn_save   = QPushButton("Save")
    self.btn_revert = QPushButton("Revert")
    self.btn_save.clicked.connect(self._editor_save_current)
    self.btn_revert.clicked.connect(self._editor_revert_current)
    default_user = "solcatcher"
##    # inputs
##    try:
##        default_user = os.getlogin()
##    except Exception:
##        default_user = "solcatcher"
    self.user_in = QLineEdit(default_user)
    self.user_in.setPlaceholderText("ssh solcatcher")
    self.path_in = make_path_input(
        init_value=getattr(self, "init_path", ""),
        parent=self,                        # required for auto-wiring
        validate=require_package_json,      # optional
        user_only=True,                     # only user edits trigger
        # bind_attr="init_path",            # default; set to None to disable attr binding
    )
    add_fs_completer(self.path_in)  # optional but nice

    # buttons
    self.run_btn = QPushButton("Run");    self.run_btn.clicked.connect(self.start_work)
    self.rerun_btn = QPushButton("Re-run build"); self.rerun_btn.clicked.connect(self.start_work)
    self.clear_btn = QPushButton("Clear"); self.clear_btn.clicked.connect(self.clear_ui)

    # log + filter
    self.log_view = QTextEdit(); self.log_view.setReadOnly(True);
    self.log_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    self.filter_group, rbs = self.create_radio_group(["All", "Errors only", "Warnings only"], 0, self.apply_log_filter)
    self.rb_all, self.rb_err, self.rb_wrn = rbs

    # lists
    # trees (grouped by file)
    
    # trees (grouped by file)
    self.errors_tree   = self.build_group_tree()
    self.warnings_tree = self.build_group_tree()
    self.all_tree = self.build_group_tree()
    # clicks -> open in editor / highlight
    self.errors_tree.itemClicked.connect(lambda i,c: self.on_tree_item_clicked(i, c))
    self.warnings_tree.itemClicked.connect(lambda i,c: self.on_tree_item_clicked(i, c))
    self.all_tree.itemClicked.connect(lambda i,c: self.on_tree_item_clicked(i, c))
