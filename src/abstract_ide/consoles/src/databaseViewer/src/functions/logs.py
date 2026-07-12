from ..imports import *


def _log(self, msg):
    self.log_console.append(msg)


def closeEvent(self, event):
    if self.stream_worker:
        self.stream_worker.stop()
    self.worker.stop()
    super(type(self), self).closeEvent(event)
