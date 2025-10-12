from abstract_gui.QT6 import *
import os
from abstract_gui.QT6.utils.log_utils.robustLogger.searchWorker import *
from abstract_paths import reset_find_console_stop,request_find_console_stop,findContent
# Data structures
@dataclass
class initSearchParams:
    directory: str
    paths: Union[bool, str] = True
    exts: Union[bool, str, List[str]] = True
    recursive: bool = True
    strings: List[str] = None
    total_strings: bool = False
    parse_lines: bool = False
    spec_line: Union[bool, int] = False
    get_lines: bool = True
    # ————————————————————————————————————————————————————————————————

# ————————————————————————————————————————————————————————————————
# Main GUI
# Define SearchParams if not already defined
# Define SearchParams if not already defined
@dataclass
class SearchParams:
    directory: str
    allowed_exts: Union[bool, Set[str]]
    unallowed_exts: Union[bool, Set[str]]
    exclude_types: Union[bool, Set[str]]
    exclude_dirs: Union[bool, List[str]]
    exclude_patterns: Union[bool, List[str]]
    add: bool
    recursive: bool
    strings: List[str]
    total_strings: bool
    parse_lines: bool
    spec_line: Union[bool, int]
    get_lines: bool
class SearchWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(list)
    def __init__(self, params: SearchParams):
        super().__init__()
        self.params = params
    def run(self):
        self.log.emit("Starting search...\n")
        try:
            results = findContent(
                **self.params
            )
            self.done.emit(results or [])
            logging.info("Search finished: %d hits", len(results or []))
        except Exception as e:
            tb = "".join(traceback.format_exc())
            logging.exception("Worker crashed: %s", e)
            self.log.emit("❌ Worker crashed:\n" + tb)
def enable_widget(parent, name: str, enabled: bool):
    try:
        getattr(parent, name).setEnabled(enabled)
    except AttributeError:
        print(f"[WARN] No widget {name} in {parent}")

# Background worker so the UI doesn’t freeze
class initSearchWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(list)
    def __init__(self, params: initSearchParams):
        super().__init__()
        self.params = params
    def run(self):
        try:
            if findContent is None:
                raise RuntimeError(
                    "Could not import your finder functions. Import error:\n"
                    f"{_IMPORT_ERR if '_IMPORT_ERR' in globals() else 'unknown'}"
                )
            self.log.emit("🔎 Searching…\n")
            results = findContent(
                directory=self.params.directory,
                paths=self.params.paths,
                exts=self.params.exts,
                recursive=self.params.recursive,
                strings=self.params.strings or [],
                total_strings=self.params.total_strings,
                parse_lines=self.params.parse_lines,
                spec_line=self.params.spec_line,
                get_lines=self.params.get_lines
            )
           
            self.done.emit(results)
        except Exception:
            self.log.emit(traceback.format_exc())
            self.done.emit([])
def enable_widget(parent, name: str, enabled: bool):
    try:
        getattr(parent, name).setEnabled(enabled)
    except AttributeError:
        print(f"[WARN] No widget {name} in {parent}")

# — Actions —
def start_search(self):
    reset_find_console_stop()  # reset flag before starting

    enable_widget(self, "btn_run", False)
    enable_widget(self, "btn_stop", True)   # enable stop button

    params = make_params(self)
    self.worker = SearchWorker(params)
    self.worker.log.connect(self.append_log)
    self.worker.done.connect(self.populate_results)
    self.worker.finished.connect(lambda: enable_widget(self,"btn_run",True))
    self.worker.start()
def stop_search(self):
    if hasattr(self, "worker") and self.worker.isRunning():
        request_find_console_stop()
        enable_widget(self, "btn_run", True)
        enable_widget(self, "btn_stop", False)

def append_log(self, text: str):
    """
    Append text to the tab's log widget (QPlainTextEdit or QTextEdit).
    Safe if self.log is missing.
    """
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

def populate_results(self, results: list):
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
            
