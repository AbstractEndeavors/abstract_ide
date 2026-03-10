from .src import *
from .utils import *
from .logPane import *
# ---------------- supervised child process runner ----------------
class appRunnerWorker(QtCore.QObject):
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

