from ..imports import *
def _update_dir_patterns(self):
    """Update self.exclude_dirs from dir_input text."""
    checked = {name for name, cb in self.dir_checks.items() if cb.isChecked()}
    self.user_exclude_dirs = checked
    # keep defaults + user excludes
    self.exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | {"backup", "backups"} | self.user_exclude_dirs

    #self._log(f"Directory row visible: True, checkboxes: {list(new_checks.keys())}")





def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
    if event.mimeData().hasUrls():
        event.acceptProposedAction()
    else:
        event.ignore()

def dropEvent(self, event: QtGui.QDropEvent):
    try:
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in make_list(urls)]
        if not paths:
            raise ValueError("No local files detected on drop.")
        self.process_files(paths)
    except Exception as e:
        tb = traceback.format_exc()
        self.status.setText(f"⚠️ Error during drop: {e}")
        self._log(f"dropEvent ERROR:\n{tb}")

def filter_paths(self, paths: list[str]) -> list[str]:
    filtered = collect_filepaths(
        paths,
        allowed_exts=self.allowed_exts,
        unallowed_exts=self.unallowed_exts,
        exclude_types=self.exclude_types,
        exclude_dirs=self.exclude_dirs,  # Use dynamic dir patterns
        exclude_patterns=self.exclude_patterns
    )
    self._log(f"_filtered_file_list returned {len(filtered)} path(s)")
    if not filtered:
        self.status.setText("⚠️ No valid files detected in drop.")
        self._log("No valid paths after filtering.")
        return []
    self._log(f"Proceeding to process {len(filtered)} file(s).")
    return filtered

# add near the top of the file
RAW_EXTS = {'.json', '.ts', '.tsx', '.js', '.css', '.html', '.md'}

def get_contents_text(self, file_path: str, idx: int = 0, filtered_paths: list[str] = []):
    basename = os.path.basename(file_path)
    filename, ext = os.path.splitext(basename)
    if ext not in self.unallowed_exts:
        header = f"=== {file_path} ===\n"
        footer = "\n\n――――――――――――――――――\n\n"
        info = {
            'path': file_path,
            'basename': basename,
            'filename': filename,
            'ext': ext,
            'text': "",
            'error': False,
            'visible': True,
            'raw': ext.lower() in RAW_EXTS,   # <<< NEW
        }
        try:
            body = read_file_as_text(file_path) or ""
            if isinstance(body, list):
                body = "\n".join(body)
            # If raw, do NOT wrap with header/footer
            if info['raw']:
                info["text"] = ["", body, ""]     # <<< NEW (body only)
            else:
                info["text"] = [header, body, footer]
            if ext == '.py':
                self._parse_functions(file_path, str(body))
        except Exception as exc:
            info["error"] = True
            info["text"] = f"[Error reading {basename}: {exc}]\n"
            self._log(f"Error reading {file_path} → {exc}")
        return info

def process_files(self, paths: list[str] = None) -> None:
    paths = paths or []
    self._last_raw_paths = paths
    filtered = self.filter_paths(paths)
    if not filtered:
        return
    self._rebuild_ext_row(filtered)
    self._rebuild_dir_row(filtered)
    filtered_paths=[]
    if self.ext_checks or self.dir_checks:
        visible_exts = {ext for ext, cb in self.ext_checks.items() if cb.isChecked()}
        visible_dirs = {di for di, cb in self.dir_checks.items() if cb.isChecked()}
        self._log(f"Visible extensions: {visible_exts}")
        def in_any_dir(path: str, dirs: set[str]) -> bool:
            return any(d and d in path for d in dirs)

        if visible_dirs:
            filtered_paths = [
                p for p in filtered
                if (os.path.isdir(p) or os.path.splitext(p)[1].lower() in visible_exts)
                and in_any_dir(p, visible_dirs)
            ]
        else:
            filtered_paths = [
                p for p in filtered
                if os.path.isdir(p) or os.path.splitext(p)[1].lower() in visible_exts
            ]
    else:
        filtered_paths  = filtered
    if not filtered_paths:
        self.text_view.clear()
        self.status.setText("⚠️ No files match current extension filter.")
        return
    self.status.setText(f"Reading {len(filtered_paths)} file(s)…")
    QtWidgets.QApplication.processEvents()
    self.combined_text_lines = {}
    self.functions = []
    self.python_files = []
    for idx, p in enumerate(filtered_paths, 1):
        info = self.get_contents_text(p, idx, filtered_paths)
        if info:
            self.combined_text_lines[p] = info
            if info['ext'] == '.py':
                self.python_files.append(info)
    self._populate_list_view()
    self._populate_text_view()
    self.status.setText("Files processed. Switch tabs to view.")




def on_function_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
    index = self.function_list.row(item)
    function_info = self.functions[index]
    self.function_selected.emit(function_info)

def on_python_file_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
    index = self.python_file_list.row(item)
    file_info = self.python_files[index]
    self.file_selected.emit(file_info)

def browse_files(self) -> None:
    files, _ = QtWidgets.QFileDialog.getOpenFileNames(
        self,
        "Select Files to Copy",
        "",
        "All Supported Files (" + " ".join(f"*{ext}" for ext in self.allowed_exts) + ");;All Files (*)"
    )
    if files:
        filtered = self.filter_paths(files)
        if filtered:
            self.process_files(filtered)

def _log(self, message: str) -> None:
    timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
    logger.info(f"[{timestamp}] {message}")
    self.log_widget.append(f"[{timestamp}] {message}")

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
