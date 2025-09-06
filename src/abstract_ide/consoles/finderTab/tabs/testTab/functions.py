# finderTab/functions.py
from types import SimpleNamespace
from pathlib import Path

def _to_ns(obj):
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _to_ns(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_ns(v) for v in obj]
    return obj

def start_search(self):
    enable_widget(self, "btn_run", False)
    try:
        params_dict = make_params(self)            # <- your function returns a dict
        # normalize directory to a clean string path
        params_dict["directory"] = str(Path(params_dict["directory"]).expanduser())

        params = _to_ns(params_dict)               # <- convert dict -> attrs

        self.worker = SearchWorker(params)
        self.worker.log.connect(self.append_log)
        self.worker.done.connect(self.populate_results)
        # only if SearchWorker actually has a 'finished' signal; otherwise rely on 'done'
        try:
            self.worker.finished.connect(lambda: enable_widget(self, "btn_run", True))
        except Exception:
            self.worker.done.connect(lambda _=None: enable_widget(self, "btn_run", True))
        self.worker.start()
    except Exception as e:
        QMessageBox.critical(self, "Search error", str(e))
        enable_widget(self, "btn_run", True)
