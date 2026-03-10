from ..src import *

class RsyncWorker(QThread):
    output = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, sources, remote_path):
        super().__init__()
        self.sources = sources
        self.remote_path = remote_path

    def run(self):
        cmd = [
            "rsync",
            "-av",
            "--progress",
            *self.sources,
            f"{REMOTE_USER}@{REMOTE_HOST}:{self.remote_path}/"
        ]

        self.output.emit(f"$ {' '.join(cmd)}\n")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            self.output.emit(line)

        process.wait()
        self.finished.emit(process.returncode)
