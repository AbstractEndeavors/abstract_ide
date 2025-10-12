from ...imports import *
def resolve_alt_ext(self,path: str, project_root: str) -> str:
    """
    If 'path' doesn't exist, try swapping extensions using a common React stack order.
    Also try replacing absolute project-root prefix with relative 'src/' and vice-versa.
    """
    try_paths = [path]
    base, ext = os.path.splitext(path)
    for e in _PREFERRED_EXT_ORDER:
        try_paths.append(base + e)

    # also try joining with project_root, and under src/
    if project_root and not path.startswith(project_root):
        rel = path.lstrip("./")
        try_paths.extend([
            os.path.join(project_root, rel),
            os.path.join(project_root, "src", os.path.basename(base)) + ext,
        ])
        for e in _PREFERRED_EXT_ORDER:
            try_paths.append(os.path.join(project_root, "src", os.path.basename(base)) + e)

    for candidate in try_paths:
        if os.path.isfile(candidate):
            return candidate
    return path  # fallback

def _editor_save_current(self):
    if not self.current_file_path:
        QMessageBox.information(self, "Save", "No file loaded.")
        return
    try:
        text = self.editor.toPlainText()
        with open(self.current_file_path, "w", encoding="utf-8") as f:
            f.write(text)
        self.original_text = text
        self.append_log(f"[editor] saved: {self.current_file_path}\n")
    except Exception as e:
        QMessageBox.critical(self, "Save Error", str(e))
        self.append_log(f"[editor] save error: {e}\n")

def _editor_revert_current(self):
    if not self.current_file_path:
        return
    self.editor.setPlainText(self.original_text or "")
    self.append_log(f"[editor] reverted: {self.current_file_path}\n")
    
def _editor_show_ranges(self, path: str, ranges: list[dict], center: tuple[int,int]|None=None):
    """
    ranges: [{line:int, col:int, message:str, code:str}]
    """
    try:
        if not hasattr(self, "editor") or not self.editor:
            return
        if hasattr(self.editor, "set_document"):
            self.editor.set_document(path)  # ensure the right file is loaded
        if hasattr(self.editor, "highlight_ranges"):
            # your editor can decide color by severity/ code; we pass metadata
            self.editor.highlight_ranges(ranges, center=center)
        elif hasattr(self.editor, "highlight_range"):  # legacy single-call
            for r in ranges:
                self.editor.highlight_range(r["line"], r["col"])
            if center:
                self.editor.center_on_line(center[0])
    except Exception:
        pass
    
def open_in_editor(self, item: QListWidgetItem):
    try:
        text = item.text()
        path, line, col = self._parse_item(text)
        if self.cb_try_alt_ext.isChecked():
            path = resolve_alt_ext(path, self.path_in.text().strip())
        target = f"{path}:{line}:{col or 1}"

        # prefer VS Code if available (platform-aware)
        candidates = ["code"]
        if os.name == "nt":
            candidates = ["code.cmd", "code.exe", "code"]

        for cmd in candidates:
            if shutil.which(cmd):
                # -g path:line[:col]
                QProcess.startDetached(cmd, ["-g", target])
                return

        # fallback: open the file without line:col via OS handler
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    except Exception:
        self.append_log("open_in_editor error:\n" + traceback.format_exc() + "\n")
