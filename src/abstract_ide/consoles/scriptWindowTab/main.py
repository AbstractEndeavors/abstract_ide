import os
from ..logPaneTab import logPaneTab
from ..appRunnerTab import appRunnerTab
from abstract_gui.QT6.utils.console_utils.startConsole import *
from abstract_utilities import *
# Works when run as a script or via -m (derives package from this file):
##logPaneTab   = safe_import("..logPaneTab",   member="logPaneTab",   file=__file__, caller_globals=globals())
##appRunnerTab = safe_import("..appRunnerTab", member="appRunnerTab", file=__file__, caller_globals=globals())
def _write_temp_script(text: str) -> str:
	fd, path = tempfile.mkstemp(prefix="abstract_ide_", suffix=".py")
	with os.fdopen(fd, "w", encoding="utf-8") as f:
		f.write(text)
	return path
class scriptWindowTab(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal App Launcher (supervised)")
        self.resize(1100, 800)
        self._current_path: str | None = None

        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central)

        # Editor toolbar
        etb = QtWidgets.QToolBar("Editor", self)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, etb)
        new_act = etb.addAction("New")
        open_act = etb.addAction("Open…")
        saveas_act = etb.addAction("Save As…")
        etb.addSeparator()
        run_buf_act = etb.addAction("Run Code (F5)")
        run_sel_act = etb.addAction("Run Selection (F6)")
        
        self.input_form = QFormLayout()
        self.input_widget = QWidget()
        self.input_widget.setLayout(self.input_form)
        # Editor
        self.editor = QtWidgets.QPlainTextEdit()
        self._set_mono_font(self.editor)
        self.editor.setPlaceholderText("# Type Python here and press F5 to run the buffer, F6 for selection.\n")
        v.addWidget(self.editor, 2)

        # Command row
        row = QtWidgets.QHBoxLayout()
        self.cmd_edit = QtWidgets.QLineEdit()
        self.cmd_edit.setPlaceholderText("Command to run (e.g. python -u your_app.py or /usr/bin/someapp)")
        self.run_btn = QtWidgets.QPushButton("Run Cmd")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        row.addWidget(self.cmd_edit); row.addWidget(self.run_btn); row.addWidget(self.stop_btn)
        v.addLayout(row)

        # Log pane
        self.log_pane = logPaneTab(self)
        self.log_pane.setVisible(True)
        v.addWidget(self.log_pane, 1)

        # Runner (make sure it's created!)
        self.runner = appRunnerTab(self.log_pane, autorestart=False, parent=self)

        # Wire actions
        self.run_btn.clicked.connect(self._on_run)
        self.stop_btn.clicked.connect(self.runner.stop)

        self.toggle_log_act = QtGui.QAction("Show/Hide Log", self, checkable=True, checked=True)
        self.toggle_log_act.triggered.connect(lambda checked: self.log_pane.setVisible(checked))
        tb = self.addToolBar("View"); tb.addAction(self.toggle_log_act)

        new_act.triggered.connect(self._on_new_buffer)
        open_act.triggered.connect(self._on_open_file)
        saveas_act.triggered.connect(self._on_save_file_as)
        run_buf_act.triggered.connect(self._on_run_code)
        run_sel_act.triggered.connect(self._on_run_selection)

        # Hotkeys
        QtGui.QShortcut(QtGui.QKeySequence("F12"), self, activated=lambda: self.toggle_log_act.trigger())
        QtGui.QShortcut(QtGui.QKeySequence("F5"), self, activated=self._on_run_code)
        QtGui.QShortcut(QtGui.QKeySequence("F6"), self, activated=self._on_run_selection)
        self._install_excepthook()
    def show_inputs(self, pkg, fn):
        # Clear old inputs
        while self.input_form.rowCount():
            self.input_form.removeRow(0)

        self.current_pkg = pkg

        self.arg_edits = []

        self.current_fn = fn["name"]
        for param in fn.get("params", []):
            edit = QLineEdit()
            self.input_form.addRow(QLabel(f"{param}:"), edit)
            self.arg_edits.append(edit)

    def _install_excepthook(self):
            # keep UI alive on exceptions triggered by button/shortcut handlers
            def _excepthook(exctype, value, tb):
                    try:
                            import traceback
                            msg = "".join(traceback.format_exception(exctype, value, tb))
                            root_logger.exception("UNCAUGHT:\n%s", msg)
                            self.log_pane.append_line(f"[EXC] {value!r}")
                            QtWidgets.QMessageBox.critical(self, "Unhandled error", str(value))
                    except Exception:
                            print(value, file=sys.stderr)
            sys.excepthook = _excepthook

    def _set_mono_font(self, widget: QtWidgets.QPlainTextEdit):
            try:
                    font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
                    font.setPointSize(11)
                    widget.setFont(font)
            except Exception as e:
                    print(f"{e}")



    def _guess_cwd(self) -> str | None:
            if getattr(self, "_current_path", None):
                    return os.path.dirname(self._current_path)
            return None

    def _on_new_buffer(self):
            try:
                    self._current_path = None
                    self.editor.setPlainText("# New buffer")
                    self.statusBar().showMessage("New buffer", 2000)
            except Exception as e:
                    print(f"{e}")

    def _on_open_file(self):
            try:
                    path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Python file", "", "Python (*.py);;All (*)")
                    if not path:
                            return
                    with open(path, "r", encoding="utf-8") as f:
                            self.editor.setPlainText(f.read())
                    self._current_path = path
                    self.statusBar().showMessage(f"Opened {path}", 3000)
            except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Open failed", str(e))

    def _on_save_file_as(self):
            try:
                    path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save As", self._current_path or "", "Python (*.py);;All (*)")
                    if not path:
                            return
                    with open(path, "w", encoding="utf-8") as f:
                            f.write(self.editor.toPlainText())
                    self._current_path = path
                    self.statusBar().showMessage(f"Saved {path}", 3000)
            except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Save failed", str(e))

    def _on_run(self):
            try:
                    cmd = self.cmd_edit.text().strip()
                    if not cmd:
                            QtWidgets.QMessageBox.warning(self, "No command", "Please enter a command to run.")
                            return
                    env = {"PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1"}
                    self.runner.start(cmd, cwd=None, env=env)
            except Exception as e:
                    print(f"{e}")

    def _on_run_code(self):
            try:
                    code_text = self.editor.toPlainText()
                    if not code_text.strip():
                            QtWidgets.QMessageBox.information(self, "Nothing to run", "The editor is empty.")
                            return
                    script_path = _write_temp_script(code_text)
                    env = {"PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1"}
                    py = sys.executable or "python3"
                    cmd = f"{py} -u {shlex.quote(script_path)}"
                    self.runner.start(cmd, cwd=self._guess_cwd(), env=env)
            except Exception as e:
                    self.log_pane.append_line(f"[ERROR] _on_run_code: {e!r}")
    def _on_run_selection(self):
            try:
                    cursor = self.editor.textCursor()
                    selected = cursor.selectedText().replace('\u2029', '\n')
                    if not selected.strip():
                            cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
                            selected = cursor.selectedText().replace('\u2029', '\n')
                            if not selected.strip():
                                    QtWidgets.QMessageBox.information(self, "No selection", "Select some code and try again.")
                                    return
                    # ... same as above
            except Exception as e:
                    self.log_pane.append_line(f"[ERROR] _on_run_selection: {e!r}")



