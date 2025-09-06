from ..imports import *
def start_work(self):
    try:
        self.run_btn.setEnabled(False)
        user = self.user_in.text().strip() or 'solcatcher'   # <- swap order (yours hard-coded the default)
        path = self.path_in.text().strip()
        if not path or not os.path.isdir(path):
            QMessageBox.critical(self, "Error", "Invalid project path.")
            self.run_btn.setEnabled(True)
            return

        # Clear old UI bits
        self.errors_tree.clear()
        self.warnings_tree.clear()
        
        # Kick off non-blocking build
        self._run_build_qprocess(path)
        
    except Exception:
        self.append_log("start_work error:\n" + traceback.format_exc() + "\n")
        self.run_btn.setEnabled(True)

def clear_ui(self):
    self.log_view.clear()
    self.errors_tree.clear()
    self.warnings_tree.clear()
    self.last_output = ""
    self.last_errors_only = ""
    self.last_warnings_only = ""
