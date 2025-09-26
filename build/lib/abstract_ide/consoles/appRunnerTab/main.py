from PyQt6 import QtCore, QtGui, QtWidgets
import os, sys, shlex, logging
from logging.handlers import RotatingFileHandler

# ---------------- shared rotating logger ----------------
LOG_DIR = os.path.join(os.path.expanduser("~"), ".cache", "abstract_finder")
LOG_FILE = os.path.join(LOG_DIR, "finder.log")
os.makedirs(LOG_DIR, exist_ok=True)

root_logger = logging.getLogger("launcher")
if not root_logger.handlers:
    root_logger.setLevel(logging.DEBUG)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"))
    root_logger.addHandler(fh)
# add near the top of the module
import shutil, os, shlex, sys
from typing import Tuple, List
from abstract_gui.QT6.utils.console_utils.startConsole import *
from abstract_utilities import *
# Works when run as a script or via -m (derives package from this file):
#logPaneTab   = safe_import("..logPaneTab",   member="logPaneTab",   file=__file__, caller_globals=globals())

def _which(prog: str) -> str | None:
    return shutil.which(prog)

def _is_python_script(path: str) -> bool:
    low = path.lower()
    return low.endswith(".py") or (os.path.isfile(path) and open(path, 'rb').read(2) == b'#!' and b'python' in open(path, 'rb').read(64))

def _split_command(cmd: str | List[str]) -> Tuple[str, List[str]]:
    """
    Returns (program, args) ready for QProcess.start(program, args),
    handling quoted paths with spaces safely.
    """
    try:
        if isinstance(cmd, list):
            parts = cmd[:]  # assume already tokenized correctly by caller
        else:
            parts = shlex.split(cmd)  # keeps quoted paths intact

        if not parts:
            raise ValueError("Empty command")

        # If a single token is an existing .py file with spaces (quoted), run via python
        if len(parts) == 1 and _is_python_script(parts[0]) and os.path.exists(parts[0]):
            py = _which("python3") or sys.executable
            return py, ["-u", parts[0]]

        prog = parts[0]
        args = parts[1:]

        # If first token is a .py script, prefer python -u script.py args...
        if _is_python_script(prog) and os.path.exists(prog):
            py = _which("python3") or sys.executable
            return py, ["-u", prog, *args]

        # Otherwise, ensure program exists in PATH or as an absolute path
        resolved = _which(prog) if not os.path.isabs(prog) else prog
        if not resolved or (os.path.isabs(resolved) and not os.path.exists(resolved)):
            raise FileNotFoundError(f"Executable not found: {prog}")

        return resolved, args
    except Exception as e:
        print(f"{e}")
def _wrap_stdbuf(program: str, args: List[str]) -> Tuple[str, List[str]]:
    """Wrap non-python programs with stdbuf if available to force line-buffered output."""
    base = os.path.basename(program)
    if base.startswith(("python", "python3")):
        return program, args
    sb = _which("stdbuf")
    if not sb:
        return program, args
    # We return stdbuf as the program, and shift the original as an arg
    return sb, ["-oL", "-eL", program, *args]
def log_path(): return LOG_FILE

# ---------------- toggleable log pane ----------------
class LogPane(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0,0,0,0)
        self.toolbar = QtWidgets.QToolBar()
        self.clear_act = self.toolbar.addAction("Clear")
        self.open_act  = self.toolbar.addAction("Open Log File")
        self.auto_scroll = QtWidgets.QCheckBox("Auto-scroll"); self.auto_scroll.setChecked(True)
        self.toolbar.addWidget(self.auto_scroll)
        v.addWidget(self.toolbar)
        self.view = QtWidgets.QPlainTextEdit(readOnly=True)
        self.view.setMaximumBlockCount(5000)  # cap memory
        v.addWidget(self.view)
        self.clear_act.triggered.connect(self.view.clear)
        self.open_act.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(log_path())))

    def append_line(self, line: str):
        self.view.appendPlainText(line.rstrip("\n"))
        if self.auto_scroll.isChecked():
            self.view.moveCursor(QtGui.QTextCursor.MoveOperation.End)

# ---------------- supervised child process runner ----------------
class appRunnerTab(QtCore.QObject):
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal(int)      # exit code
    crashed = QtCore.pyqtSignal(int)      # exit code

    def __init__(self, log_pane: LogPane=None, autorestart: bool = True, parent=None):
        super().__init__(parent)
        self.log = root_logger.getChild("AppRunner")
        self.p = QtCore.QProcess(self)
        self.p.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
        self.p.readyReadStandardOutput.connect(self._drain)
        self.p.readyReadStandardError.connect(self._drain)
        self.p.started.connect(lambda: (self.log.info("child started pid=%s", self.p.processId()), self.started.emit()))
        self.p.errorOccurred.connect(lambda e: self.log.error("QProcess error: %s", e.name))
        self.p.finished.connect(self._on_finished)
        self.autorestart = autorestart
        self._last_cmd = None
        self._last_cwd = None
        self._last_env = None
        self.log_pane = log_pane

    # replace your AppRunner.start with this version
    def start(self, cmd: list[str] | str, cwd: str | None = None, env: dict | None = None, force_line_buffer: bool = True):
        # Save context for possible autorestart only after successful start
        self._last_cmd = None
        self._last_cwd = None
        self._last_env = None

        pe = QtCore.QProcessEnvironment.systemEnvironment()
        pe.insert("PYTHONUNBUFFERED", "1")
        pe.insert("PYTHONFAULTHANDLER", "1")
        for k, v in (env or {}).items():
            pe.insert(k, v)

        try:
            program, args = _split_command(cmd)

            if force_line_buffer:
                program, args = _wrap_stdbuf(program, args)

            self.p.setProcessEnvironment(pe)
            if cwd:
                self.p.setWorkingDirectory(cwd)

            self.log.info("launch: %s %s (cwd=%s)", program, " ".join(map(shlex.quote, args)), cwd or os.getcwd())
            self.p.start(program, args)

            if not self.p.waitForStarted(5000):
                err = self.p.error()
                self.log.error("failed to start: %s %s (QProcess error=%s)", program, args, err.name)
                self.log_pane.append_line(f"[ERROR] failed to start: {program} {args} (QProcess error={err.name})")
                return  # don't arm autorestart on never-started process

            # only arm autorestart if we actually started
            self._last_cmd = cmd
            self._last_cwd = cwd
            self._last_env = env or {}

        except Exception as e:
            self.log.exception("start() exception while preparing command: %r", cmd)
            self.log_pane.append_line(f"[ERROR] start() exception: {e!r}")
            return


    def _drain(self):
        bs = self.p.readAllStandardOutput().data().decode(errors="replace")
        if bs:
            for line in bs.splitlines():
                root_logger.info("[child] %s", line)
                self.log_pane.append_line(line)
        bs = self.p.readAllStandardError().data().decode(errors="replace")
        if bs:
            for line in bs.splitlines():
                root_logger.error("[child:stderr] %s", line)
                self.log_pane.append_line(line)

    def _on_finished(self, code: int, status: QtCore.QProcess.ExitStatus):
        if status == QtCore.QProcess.ExitStatus.CrashExit:
            self.log.error("child crashed (code=%s)", code); self.crashed.emit(code)
        else:
            self.log.info("child exited (code=%s)", code); self.stopped.emit(code)
        if self.autorestart and self._last_cmd:
            self.log.warning("autorestart enabled; relaunching …")
            QtCore.QTimer.singleShot(1000, lambda: self.start(self._last_cmd, self._last_cwd, self._last_env))

    def stop(self):
        if self.p.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.log.info("stopping child …")
            self.p.terminate()
            if not self.p.waitForFinished(3000):
                self.log.warning("terminate timed out; killing")
                self.p.kill()

# ---------------- integrate into your UI ----------------
class LauncherWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal App Launcher (supervised)")
        self.resize(1000, 700)

        # central dummy (replace with your real UI)
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central)

        # command entry + buttons
        row = QtWidgets.QHBoxLayout()
        self.cmd_edit = QtWidgets.QLineEdit()
        self.cmd_edit.setPlaceholderText("Command to run (e.g. python -u your_app.py or /usr/bin/someapp)")
        self.run_btn = QtWidgets.QPushButton("Run")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        row.addWidget(self.cmd_edit); row.addWidget(self.run_btn); row.addWidget(self.stop_btn)
        v.addLayout(row)

        # toggleable bottom log pane
        self.log_pane = LogPane(self)
        self.log_pane.setVisible(True)  # start visible; you can default to False
        v.addWidget(self.log_pane)

        # runner
        self.runner = appRunnerTab(self.log_pane, autorestart=True, parent=self)

        # actions
        self.run_btn.clicked.connect(self._on_run)
        self.stop_btn.clicked.connect(self.runner.stop)

        # menu / toolbar toggle
        self.toggle_log_act = QtGui.QAction("Show/Hide Log", self, checkable=True, checked=True)
        self.toggle_log_act.triggered.connect(lambda checked: self.log_pane.setVisible(checked))
        tb = self.addToolBar("View"); tb.addAction(self.toggle_log_act)

        # hotkey: F12 toggles log
        QtGui.QShortcut(QtGui.QKeySequence("F12"), self, activated=lambda: self.toggle_log_act.trigger())

    def _on_run(self):
        try:
            cmd = self.cmd_edit.text().strip()
            if not cmd:
                QtWidgets.QMessageBox.warning(self, "No command", "Please enter a command to run.")
                return
            # Example: bias environment for Python targets
            env = {"PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1"}
            self.runner.start(cmd, cwd=None, env=env)
        except Exception as e:
            print(f"{e}")
