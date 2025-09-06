from .get_file_drop import *

# 5) If you want to know what “roles” you can pass to item.data()/setData():
roles = [(name, getattr(QtCore.Qt, name))
         for name in dir(QtCore.Qt) if name.endswith('Role')]
print("Data roles:", roles)
from ..imports import *
logger = get_logFile('clipit_logs')
from abstract_utilities import get_media_exts
def unlist(obj):
    if obj and isinstance(obj,list):
        obj = obj[0]
    return obj
def try_it(function,default,*args,**kwargs):
    try:
        result = function(*args,**kwargs)
        return result
    except Exception as e:
        print(f"{e}")
        return default

def get_selected_text(_selected_text,python_files,path=None):
    entry = next((f for f in python_files if f['path'] == path), None)
    text  = entry['text'] if entry else read_file_as_text(path)
    _selected_text[path] = f"=== {path} ===\n{text}"
    return _selected_text
def selected_text_view(selected_text,text_view):
    joined = "\n\n".join(selected_text.values())
    text_view.setPlainText(joined)
    text_view.setVisible(bool(joined))
    return text_view
def view_tabs_parent(view_tabs,text_view):
    view_tabs.setCurrentWidget(text_view.parentWidget())
    return view_tabs
class FileDropArea(QtWidgets.QWidget):
    function_selected = QtCore.pyqtSignal(dict)
    file_selected     = QtCore.pyqtSignal(dict)

    def __init__(self, log_widget: QtWidgets.QTextEdit,view_widget=None, parent=None):
        super().__init__(parent)

        # ─── Ensure the parent accepts drops ────────────────────────────────
        self.setAcceptDrops(True)

        self.log_widget = log_widget
        self.view_widget = view_widget

        # Map ".ext" → QCheckBox
        self.ext_checks: dict[str, QtWidgets.QCheckBox] = {}
        self._last_raw_paths: list[str] = []
        self.functions: list[dict] = []
        self.python_files: list[dict] = []
        self.combined_text_lines: list[str] = []
        self.allowed_extensions = {
            '.py', '.txt', '.md', '.csv', '.tsv', '.log',
            '.xls', '.xlsx', '.ods', '.parquet', '.geojson', '.shp'
        }
     
        self.unallowed_extentions = set(list(get_media_exts(['video','audio','image']))+[".pyc"])
        self.exclude_dirs=set(list(DEFAULT_EXCLUDE_DIRS) + ["backups", "backup", "node_modules", "__pycache__", "logs", "log"]),
        self.exclude_file_patterns=['__init__.py', "*.zip"]
        # ─── Main vertical layout ─────────────────────────────────────────
        lay = QtWidgets.QVBoxLayout(self)

        # 1) “Browse Files…” button
        browse_btn = get_push_button(text="Browse Files…",action=self.browse_files)

        # 2) Extension‐filter row
        self.ext_row = QtWidgets.QScrollArea(widgetResizable=True)
        self.ext_row.setFixedHeight(45)
        self.ext_row.setVisible(False)
        self.ext_row_w = QtWidgets.QWidget()
        self.ext_row.setWidget(self.ext_row_w)
        self.ext_row_lay = QtWidgets.QHBoxLayout(self.ext_row_w)
        self.ext_row_lay.setContentsMargins(4, 4, 4, 4)
        self.ext_row_lay.setSpacing(10)


        # 3) Tab widget to switch between “List View” and “Text View”
        self.view_tabs = QtWidgets.QTabWidget()


        # ─── 3a) List View Tab ─────────────────────────────────────────────
        list_tab = QtWidgets.QWidget()
        list_layout = get_layout(parent=list_tab)

        # Function list (QListWidget) inside List View
        self.function_list = QtWidgets.QListWidget()
        self.function_list.setVisible(False)
        self.function_list.setAcceptDrops(False)  # ensure drops go to parent
        self.function_list.itemClicked.connect(self.on_function_clicked)

        # Python file list (QListWidget) inside List View
        self.python_file_list = QtWidgets.QListWidget()
        self.python_file_list.setVisible(False)
        self.python_file_list.setAcceptDrops(False)
        self.python_file_list.itemClicked.connect(self.on_python_file_clicked)

        add_widgets(list_layout,
                    {"widget":self.python_file_list},
                    {"widget":self.function_list}
                    )


        self.view_tabs.addTab(list_tab, "List View")

        # ─── 3b) Text View Tab ─────────────────────────────────────────────
        text_tab = QtWidgets.QWidget()
        text_layout = QtWidgets.QVBoxLayout(text_tab)

        # QTextEdit for raw‐text inside Text View
        self.text_view = QtWidgets.QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setVisible(False)
        self.text_view.setAcceptDrops(False)  # ensure drops go to parent
        add_widgets(text_layout,
                    {"widget":self.text_view}
                    )
        self.view_tabs.addTab(text_tab, "Text View")

        # 4) Status label
        self.status = QtWidgets.QLabel("No files selected.", alignment=QtCore.Qt.AlignCenter)
        self.status.setStyleSheet("color: #333; font-size: 12px;")

        add_widgets(lay,
                    {"widget":browse_btn,"kargs":{"alignment":QtCore.Qt.AlignHCenter}},
                    {"widget":self.view_tabs},
                    {"widget":self.ext_row},
                    {"widget":self.status}
                    )
        # Keep track of each checked file’s contents
        self._selected_text: dict[str, str] = {}

        # After creating python_file_list:
        self.python_file_list.itemChanged.connect(self._on_file_toggled)

        # Ensure the checkbox state change emits itemChanged
        self.python_file_list.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
    def _on_file_toggled(self, item):
        path = item.data(Qt.UserRole)
        if item.checkState() == Qt.Checked:
            info = self.get_contents_text(path)
            self._selected_text[path] = info['text']
        else:
            self._selected_text.pop(path, None)

        joined = "".join(self._selected_text.values())
        self.text_view.setPlainText(joined)
        

    # ────────────────────────────────────────────────────────────────────────
    # dragEnterEvent / dropEvent (parent still handles all drops)
    # ────────────────────────────────────────────────────────────────────────
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent):
        try:
            urls = event.mimeData().urls()
            paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
            self._last_unfiltered_paths =collect_filepaths(
                paths,
                exclude_dirs=[],
                exclude_file_patterns=[]
            )
            self._log(f"Received raw drop paths: {paths!r}")

            if not paths:
                raise ValueError("No local files detected on drop.")

            filtered = self.filter_paths(paths)
            if not filtered:
                return

            self.process_files(filtered)

        except Exception as e:
            tb = traceback.format_exc()
            self.status.setText(f"⚠️ Error during drop: {e}")
            self._log(f"dropEvent ERROR:\n{tb}")

    # ────────────────────────────────────────────────────────────────────────
    # Expand directories, exclude unwanted files
    # ────────────────────────────────────────────────────────────────────────
    def filter_paths(self, paths: list[str]) -> list[str]:
        
        filtered = collect_filepaths(
            paths,
            exclude_dirs=self.exclude_dirs,
            exclude_file_patterns=self.exclude_file_patterns
        )
        self._log(f"_filtered_file_list returned {len(filtered)} path(s): {filtered!r}")

        if not filtered:
            self.status.setText("⚠️ No valid files detected in drop.")
            self._log("No valid paths after filtering.")
            return []

        self._log(f"Proceeding to process {len(filtered)} file(s).")
        return filtered
    def get_contents_text(self, file_path: str, idx: int = 0, filtered_paths: list[str] = []):
        basename = os.path.basename(file_path)
        filename, ext = os.path.splitext(basename)
        if ext.lower() not in self.unallowed_extentions:
            header = f"\n\n=== {file_path} ===\n"
            footer = "\n\n――――――――――――――――――\n\n"
            info   = {
                'path':    file_path,
                'basename': basename,
                'filename': filename,
                'ext':      ext,
                'text':    "",
                'error':   False,
                'visible': True
            }

            try:
                body = read_file_as_text(file_path) or ""
                info["text"] = f"{header}{body}{footer}"

                # parse functions	if it’s Python
                if ext == '.py':
                    self._parse_functions(file_path, body)
            except Exception as exc:
                info["error"] = True
                info["text"]  = f"[Error reading {basename}: {exc}]\n"
                self._log(f"Error reading {file_path} → {exc}")

            return info
    # ────────────────────────────────────────────────────────────────────────
    # Main processing logic: read files, then update both tabs
    # ────────────────────────────────────────────────────────────────────────
    def process_files(self, raw_paths: list[str]) -> None:
        """
        1. Expand directories → all_paths
        2. Rebuild extension row
        3. Filter by checked extensions
        4. Read & parse files
        5. Populate “List View” widgets and the “Text View” widget
        """
        self._last_raw_paths = raw_paths
        
        # 1) Expand directories
        self._last_all_paths = collect_filepaths(
            self._last_raw_paths,
            exclude_dirs=self.exclude_dirs,
            exclude_file_patterns=self.exclude_file_patterns
        )
        self._last_all_paths =  [path for path in self._last_all_paths if f".{path.split('.')[-1]}".lower() not in self.unallowed_extentions]
        self._log(f"{len(self._last_all_paths)} total path(s) after expansion")

        # 2) Rebuild extension‐filter row
        self._rebuild_ext_row(self._last_all_paths)

        # 3) Filter by checked extensions
        if self.ext_checks:
            visible_exts = {ext for ext, cb in self.ext_checks.items() if cb.isChecked()}
            self._log(f"Visible extensions: {visible_exts}")
            filtered_paths = [
                p for p in self._last_all_paths
                if os.path.isdir(p) or os.path.splitext(p)[1].lower() in visible_exts
            ]
        else:
            filtered_paths = self._last_all_paths

        if not filtered_paths:
            self.text_view.clear()
            self.status.setText("⚠️ No files match current extension filter.")
            
            return

        self.status.setText(f"Reading {len(filtered_paths)} file(s)…")
        self._log(f"Reading {len(filtered_paths)} file(s)")
        QtWidgets.QApplication.processEvents()

        # 4) Read & parse each file into a dict
        self.combined_text_lines: dict[str, dict] = {}
        self.functions = []
        self.python_files = []
        for idx, p in enumerate(filtered_paths, 1):
            info = self.get_contents_text(p, idx, filtered_paths)
            if info:
                self.combined_text_lines[p] = info
                # collect .py entries for your python_files list
                if not info['error'] and info['ext'] == '.py':
                    self.python_files.append({'path': p, 'text': info['text']})
        # 5) Populate
        self._populate_list_view()
        self._populate_text_view(self.combined_text_lines)
        self.status.setText("Files processed. Switch tabs to view.")

    # ────────────────────────────────────────────────────────────────────────
    # Rebuild the extension‐filter row
    # ────────────────────────────────────────────────────────────────────────
    def _rebuild_ext_row(self, paths: list[str]) -> None:
        exts = {os.path.splitext(p)[1].lower() for p in paths if os.path.isfile(p)}
        exts.discard("")

        if not exts:
            self.ext_row.setVisible(False)
            self.ext_checks.clear()
            
            return

        self._clear_layout(self.ext_row_lay)
        
        new_checks: dict[str, QtWidgets.QCheckBox] = {}
        for ext in sorted(exts):
            cb = QtWidgets.QCheckBox(ext)
            prev_cb = self.ext_checks.get(ext)
            cb.setChecked(prev_cb.isChecked() if prev_cb else True)
            cb.stateChanged.connect(self._apply_ext_filter)
            self.ext_row_lay.addWidget(cb)
            new_checks[ext] = cb

        self.ext_checks = new_checks
        self.ext_row.setVisible(True)

    def _apply_ext_filter(self) -> None:
        """Re‐run processing when an extension checkbox changes."""
        self._populate_text_view(combined_lines=self.combined_text_lines)
    def on_python_file_clicked(self, item):
        path = item.data(Qt.UserRole)
        # find or read its text
        txt  = next((f['text'] for f in self.python_files if f['path']==path), None)
        if txt is None:
            txt = read_file_as_text(path)
        self.file_selected.emit({'path':path, 'text':txt})

    def populate_python_view(self) -> None:
        """
        Show every .py in self.all_python_files;
        check only those that survive the current filter.
        """
        self.python_file_list.clear()


     
        # Build a set of filtered paths once:
        all_paths   = [info for info in self._last_unfiltered_paths if info.endswith('.py')]
        
        filtered_set = set(self.filter_paths(all_paths))

        for p in all_paths:
            item = QListWidgetItem(os.path.basename(p))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            # check if it's in the filtered list
            item.setCheckState(Qt.Checked if p in filtered_set else Qt.Unchecked)
            self.python_file_list.addItem(item)

        self.python_file_list.setVisible(True)

    # ────────────────────────────────────────────────────────────────────────
    # Populate the “List View” tab (two QListWidget)s
    # ────────────────────────────────────────────────────────────────────────
    def _populate_list_view(self) -> None:
        # ─── Function list ──────────────────────────────────────────────
        self.function_list.clear()
        if self.functions:
            for func in self.functions:
                itm = QListWidgetItem(f"{func['name']} ({func['file']})")
                itm.setFlags(itm.flags() | Qt.ItemIsUserCheckable)
                itm.setCheckState(Qt.Unchecked)
                self.function_list.addItem(itm)
            self.function_list.setVisible(True)
        else:
            self.function_list.setVisible(False)

        # ─── Python‐file list ────────────────────────────────────────────
        self.populate_python_view()

    # ────────────────────────────────────────────────────────────────────────
    # Populate the “Text View” tab (QTextEdit)
    # ────────────────────────────────────────────────────────────────────────
    def _populate_text_view(self, combined_lines: dict[str, dict] = None, joiner: str = "") -> None:
        if combined_lines:
            # only include those marked visible=True
            parts = []
            for path, info in combined_lines.items():
                if info.get('visible', True):
                    parts.append(info['text'])
            text = joiner.join(parts)
            self.text_view.setPlainText(text)
            self.text_view.setVisible(bool(text))
            copy_to_clipboard(text)
        else:
            self._selected_text.clear()
            self.text_view.clear()
            self.text_view.setVisible(False)
            copy_to_clipboard()

    def _toggle_populate_text_view(self, view_toggle=None) -> None:
        self._populate_text_view()
        view_toggle= view_toggle or 'array'
        combined_lines = self.combined_text_lines
        joiner="\n\n"
        
        if view_toggle == 'print':
            joiner = '\n\n'
            
            try:
                combined_lines = [unlist(line) for line in combined_lines if line]
            except Exception as e:
                print(f"{e}")
        self._populate_text_view(combined_lines=combined_lines,joiner=joiner)
    # ────────────────────────────────────────────────────────────────────────
    # Parse Python files for function definitions (unchanged from before)
    # ────────────────────────────────────────────────────────────────────────
    def _parse_functions(self, file_path: str, text: str) -> None:
        try:
            tree = ast.parse(text, filename=file_path)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_code = "\n".join(text.splitlines()[node.lineno-1:node.end_lineno])
                    imports = self._extract_imports(tree)
                    self.functions.append({
                        'name': node.name,
                        'file': file_path,
                        'line': node.lineno,
                        'code': func_code,
                        'imports': imports
                    })
        except SyntaxError as e:
            self._log(f"Syntax error in {file_path}: {e}")

    def _extract_imports(self, tree: ast.AST) -> list[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")
        return imports

    # ────────────────────────────────────────────────────────────────────────
    # Handle clicks in “List View” tab
    # ────────────────────────────────────────────────────────────────────────
    def on_function_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        index = self.function_list.row(item)
        function_info = self.functions[index]
        self.function_selected.emit(function_info)

    def on_python_file_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        index = self.python_file_list.row(item)
        file_info = self.python_files[index]
        self.file_selected.emit(file_info)

    # ────────────────────────────────────────────────────────────────────────
    # Copy function dependencies to clipboard (unchanged)
    # ────────────────────────────────────────────────────────────────────────
    def map_function_dependencies(self, function_info: dict) -> None:
        combined_lines = []
        combined_lines.append(f"=== Function: {function_info['name']} ===\n")
        combined_lines.append(function_info['code'])
        combined_lines.append("\n\n=== Imports ===\n")
        combined_lines.extend(function_info['imports'])

        project_files = collect_filepaths(
            [os.path.dirname(function_info['file'])],
            exclude_dirs=DEFAULT_EXCLUDE_DIRS,
            exclude_file_patterns=DEFAULT_EXCLUDE_FILE_PATTERNS
        )
        combined_lines.append("\n\n=== Project Reach ===\n")
        for file_path in project_files:
            if file_path != function_info['file'] and file_path.endswith('.py'):
                combined_lines.append(f"--- {file_path} ---\n")
                try:
                    text = read_file_as_text(file_path)
                    combined_lines.append(text)
                except Exception as exc:
                    combined_lines.append(f"[Error reading {os.path.basename(file_path)}: {exc}]\n")
                combined_lines.append("\n")

        QtWidgets.QApplication.clipboard().setText("\n".join(combined_lines))
        self.status.setText(f"✅ Copied function {function_info['name']} and dependencies to clipboard!")
        self._log(f"Copied function {function_info['name']} with dependencies")

    # ────────────────────────────────────────────────────────────────────────
    # Copy import chain to clipboard (unchanged)
    # ────────────────────────────────────────────────────────────────────────
    def map_import_chain(self, file_info: dict) -> None:
        try:
            module_paths, imports = get_py_script_paths([file_info['path']])
            combined_lines = []
            combined_lines.append(f"=== Import Chain for {file_info['path']} ===\n")
            combined_lines.append("Modules:\n")
            if module_paths:
                combined_lines.extend(f"- {p}" for p in module_paths)
            else:
                combined_lines.append("- None\n")
            combined_lines.append("\nImports:\n")
            if imports:
                combined_lines.extend(f"- {imp}" for imp in imports)
            else:
                combined_lines.append("- None\n")

            QtWidgets.QApplication.clipboard().setText("\n".join(combined_lines))
            self.status.setText(f"✅ Copied import chain for {os.path.basename(file_info['path'])} to clipboard!")
            self._log(f"Copied import chain for {file_info['path']}")
        except Exception as e:
            tb = traceback.format_exc()
            self.status.setText(f"⚠️ Error mapping import chain: {e}")
            self._log(f"map_import_chain ERROR:\n{tb}")

    # ────────────────────────────────────────────────────────────────────────
    # “Browse Files…” button
    # ────────────────────────────────────────────────────────────────────────
    def browse_files(self) -> None:
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select Files to Copy",
            "",
            "All Supported Files (" + " ".join(f"*{ext}" for ext in self.allowed_extensions) + ");;All Files (*)"
        )
        if files:
            filtered = self.filter_paths(files)
            if filtered:
                self.process_files(filtered)

    # ────────────────────────────────────────────────────────────────────────
    # Logging helper
    # ────────────────────────────────────────────────────────────────────────
    def _log(self, message: str) -> None:
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        logger.info(f"[{timestamp}] {message}")
        self.log_widget.append(f"[{timestamp}] {message}")

    # ────────────────────────────────────────────────────────────────────────
    # Clear a QLayout recursively
    # ────────────────────────────────────────────────────────────────────────
    def _clear_layout(self, layout: QtWidgets.QLayout) -> None:
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
