# in your SearchWorker.run()
import logging, traceback
from PyQt6.QtCore import pyqtSignal, QThread

class SearchWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(list)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            logging.info("Search started: %s", self.params)
            # ... your search logic here, emit self.log(...) as you go ...
            results = self._do_search(self.params)
            self.done.emit(results or [])
            logging.info("Search finished: %d hits", len(results or []))
        except Exception as e:
            tb = "".join(traceback.format_exc())
            logging.exception("Worker crashed: %s", e)
            self.log.emit("❌ Worker crashed:\n" + tb)
            # Do NOT re-raise — keep the app alive
