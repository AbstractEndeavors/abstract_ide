from ..imports import *
import os, sys, shlex, tempfile

from abstract_gui.QT6.utils.console_utils.startConsole import *
from abstract_utilities import *

# If your ..imports didn’t bring Qt symbols, fall back to PyQt6
try:
	QtWidgets
except NameError:  # pragma: no cover
	from PyQt6 import QtCore, QtWidgets, QtGui

# Works when run as a script or via -m (derives package from this file):

# ---------- helpers bound via initFuncs ----------

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
		self.runner.start(cmd, cwd=_guess_cwd(self), env=env)
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
