from ..imports import *
def start_collect(self):
    self.list.clear()
    self.btn_run.setEnabled(False)
    try:
        self.params = make_params(self)
    except Exception as e:
        QMessageBox.critical(self, "Bad input", str(e))
        self.btn_run.setEnabled(True)
        return
    class CollectWorker(QThread):
        log = pyqtSignal(str)
        done = pyqtSignal(list)
        def __init__(self, params):
            super().__init__()
            self.params = params
        def run(self):
            try:
                results = collect_filepaths(**self.params)
                self.done.emit(results)
            except Exception:
                self.log.emit(traceback.format_exc())
                self.done.emit([])
    self.worker = CollectWorker(self.params)
    self.worker.log.connect(self.append_log)
    self.worker.done.connect(self.populate_results)
    self.worker.finished.connect(lambda: self.btn_run.setEnabled(True))
    self.worker.start()
def append_log(self, text: str):
    self.log.moveCursor(self.log.textCursor().MoveOperation.End)
    self.log.insertPlainText(text)
def populate_results(self, results: list):
    self._last_results = results or []
    if not results:
        self.append_log("✅ No files found.\n")
        self.btn_secondary.setEnabled(False)
        return
    self.append_log(f"✅ Found {len(results)} file(s).\n")
    self.btn_secondary.setEnabled(True)
    for file_path in results:
        if isinstance(file_path, str):
            self.list.addItem(QListWidgetItem(file_path))
            self.append_log(file_path + "\n")

