from .imports import *
# Data structures
def enable_widget(parent, name: str, enabled: bool):
    try:
        getattr(parent, name).setEnabled(enabled)
    except AttributeError:
        print(f"[WARN] No widget {name} in {parent}")

# — Actions —
def start_search(self):
    try:
        reset_find_console_stop()  # reset flag before starting
        
        enable_widget(self, "primary_btn", False)
        enable_widget(self, "btn_secondary", True)   # enable stop button
        
        try:
            params = self.make_params(self)
        except Exception as e:
            logger.info(f"{e}")
        logger.info(f"params == {params}")
        self.worker = SearchWorker(params)
        
        self.worker.log.connect(self.append_log)
        self.worker.done.connect(self.populate_results)
        
        self.worker.finished.connect(lambda: enable_widget(self,"primary_btn",True))
        self.worker.start()
    except Exception as e:
        logger.info(e)
def stop_search(self):
    if hasattr(self, "worker") and self.worker.isRunning():
        request_find_console_stop()
        enable_widget(self, "primary_btn", True)
        enable_widget(self, "btn_secondary", False)

def append_log(self, text: str):
    """
    Append text to the tab's log widget (QPlainTextEdit or QTextEdit).
    Safe if self.log is missing.
    """
    try:
        edit = getattr(self, "log", None)

        # Prefer QPlainTextEdit (faster for logs)
        if isinstance(edit, QPlainTextEdit):
            if not text.endswith("\n"):
                text += "\n"
            edit.appendPlainText(text)
            return

        # QTextEdit fallback
        if isinstance(edit, QTextEdit):
            if not text.endswith("\n"):
                text += "\n"
            cursor = edit.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            edit.setTextCursor(cursor)
            edit.insertPlainText(text)
            return

        # No log widget? Avoid crashing, at least surface somewhere:
        try:
            print(text, end="" if text.endswith("\n") else "\n")
        except Exception:
            pass
    except Exception as e:
        logger.info(e)
def populate_results(self, results: list):
    try:
        self._last_results = results or []
        self.list.clear()
        if not results:
            self.append_log("✅ No matches found.\n")
            enable_widget(self, "btn_secondary", False)
            return

        self.append_log(f"✅ Found {len(results)} file(s).\n")
        enable_widget(self, "btn_secondary", True)
        self.lines_list = {}
        for fp in results:
            if isinstance(fp, dict):
                file_path = fp.get("file_path")
                lines = fp.get("lines", [])
            else:
                file_path = fp
                lines = []

            if not isinstance(file_path, str):
                continue

            if lines:
                for obj in lines:
                    line = obj.get("line")
                    text = f"{file_path}" if line is not None else file_path
                    if file_path not in self.lines_list:
                        self.lines_list[file_path] = []
                        item = QListWidgetItem(text)
                        item.setData(Qt.ItemDataRole.UserRole, {"file_path": file_path, "line": line})
                        self.list.addItem(item)
                    self.lines_list[file_path].append(line)
            else:
                text = f"{file_path}" if line is not None else file_path
                if file_path not in self.lines_list:
                    item = QListWidgetItem(file_path)
                    item.setData(Qt.ItemDataRole.UserRole, {"file_path": file_path, "line": None})
                    self.list.addItem(item)
                    self.append_log(file_path + "\n")
            
    except Exception as e:
        logger.info(e)
