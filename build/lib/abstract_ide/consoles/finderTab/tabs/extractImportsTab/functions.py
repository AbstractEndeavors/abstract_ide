from ..imports import *
class _ExtractWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(tuple)   # (module_paths: list[str], imports: list[str])

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            py_files = collect_filepaths(**self.params)  # from your lib
            module_paths, imports = get_py_script_paths(py_files)  # your function
            self.done.emit((module_paths, imports))
        except Exception:
            self.log.emit(traceback.format_exc())
            self.done.emit(([], []))

# ------------- Actions -------------
def start_extract(self):
    self.log.clear() if hasattr(self, "log") else None
    self.btn_run.setEnabled(False)
    try:
        self.params = make_params(self)
    except Exception as e:
        QMessageBox.critical(self, "Bad input", str(e))
        self.btn_run.setEnabled(True)
        return

    self.worker = _ExtractWorker(self.params)
    self.worker.log.connect(self.append_log)
    self.worker.done.connect(self.display_imports)
    self.worker.finished.connect(lambda: self.btn_run.setEnabled(True))
    self.worker.start()

def append_log(self, text: str):
    if not hasattr(self, "log"):
        return
    c = self.log.textCursor()
    c.movePosition(c.MoveOperation.End)
    self.log.setTextCursor(c)
    self.log.insertPlainText(text)
    self.log.ensureCursorVisible()

# Build a reverse index import -> [files] (cheap pass over files)
def _build_import_index(self, module_paths: list[str]) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    for fp in module_paths:
        try:
            content = read_from_file(fp)
        except Exception:
            continue
        # very simple: reuse your extractor on this file
        for mod in extract_python_imports(fp):
            idx.setdefault(mod, []).append(fp)
        # handle “from .x import y” quick pass (optional)
        for line in content.splitlines():
            s = line.strip()
            if s.startswith("from "):
                parts = s.split()
                if len(parts) > 1:
                    base = parts[1].split('.')[0]
                    if base:
                        idx.setdefault(base, []).append(fp)
    # dedupe lists
    for k in list(idx.keys()):
        idx[k] = sorted(set(idx[k]))
    return idx

def display_imports(self, results: tuple):
    module_paths, imports = results or ([], [])

    # Save whole sets
    self._last_module_paths = sorted(set(module_paths))
    self._last_imports = sorted(set(s.strip() for s in imports if s and s.strip()))

    # Build / update reverse index
    self._import_to_files = self._build_import_index(self._last_module_paths)

    # ---- populate files (default: all) ----
    self._fill_files(self._last_module_paths)

    # ---- populate imports (wrapped chips) ----
    self._fill_imports(self._last_imports)

    if not self._last_imports:
        self.append_log("No imports found.\n")
    if not self._last_module_paths:
        self.append_log("No module_paths found.\n")

# helpers to fill views
def _fill_files(self, files: list[str]):
    self.module_paths.clear()
    if files:
        self.module_paths.addItems(files)

def _fill_imports(self, imports: list[str]):
    self.modules_list.clear()
    fm = self.modules_list.fontMetrics()
    for s in imports:
        it = QListWidgetItem(s)
        # make a “chip” size hint that wraps nicely
        w = fm.horizontalAdvance(s) + 24
        h = fm.height() + 10
        it.setSizeHint(QSize(min(max(w, 80), 380), h))
        self.modules_list.addItem(it)

# selection handler: filter files by selected imports
def _on_import_selection_changed(self):
    selected = [it.text() for it in self.modules_list.selectedItems()]
    if not selected:
        # Show all
        self._fill_files(self._last_module_paths)
        return

    # Gather union of files for all selected imports
    files = set()
    for name in selected:
        files.update(self._import_to_files.get(name, []))
    self._fill_files(sorted(files))

def _open_selected_module_path(self, item: QListWidgetItem):
    path = item.data(Qt.ItemDataRole.UserRole) or item.text()
    if path and os.path.exists(path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def _copy_imports(self):
    # Copy selected imports; if none selected, copy all
    items = self.modules_list.selectedItems()
    if items:
        text = ", ".join(sorted({it.text() for it in items}))
    else:
        text = ", ".join(self._last_imports)
    QGuiApplication.clipboard().setText(text, QClipboard.Mode.Clipboard)           
