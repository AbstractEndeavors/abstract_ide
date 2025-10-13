from ..imports import *
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

def _populate_list_view(self) -> None:
    try:
        self.function_list.clear()
        if self.functions:
            for func in self.functions:
                itm = QtWidgets.QListWidgetItem(f"{func['name']} ({func['file']})")
                itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                itm.setCheckState(Qt.CheckState.Unchecked)
                self.function_list.addItem(itm)
            self.function_list.setVisible(True)
        else:
            self.function_list.setVisible(False)
        self.populate_file_view()   # ← show ALL files here
    except Exception as e:
        print(f"{e}")
def copy_raw(self):
    chunks = []
    for _, info in self.combined_text_lines.items():
        txt = info.get('text')
        body = txt[1] if isinstance(txt, list) else str(txt or "")
        chunks.append(body)
    QtWidgets.QApplication.clipboard().setText("\n\n".join(chunks))
    self.status.setText("✅ Copied RAW bodies to clipboard")
def _populate_text_view(self) -> None:
    try:
        if not self.combined_text_lines:
            self.text_view.clear()
            self.text_view.setVisible(False)
            return
        parts = []
        for path, info in self.combined_text_lines.items():
            if not info.get('visible', True):
                continue
            lines = info['text']

            is_raw = bool(info.get('raw'))
            if is_raw:
                # body only, exactly as read
                lines = [lines[1]] if isinstance(lines, list) else [str(lines)]
            else:
                # Non-raw: header/body/footer with optional compacting in non-print view
                if self.view_toggle != 'print':
                    body = repr(lines[1]) if isinstance(lines, list) else repr(lines)
                    lines = [lines[0], body, lines[-1]]
                else:
                    lines = [l for l in lines if l is not None]

            seg = "\n".join(lines)
            parts.append(seg)

        final = "\n\n".join(parts)
        self.text_view.setPlainText(final)
        self.text_view.setVisible(bool(final))
        copy_to_clipboard(final)
    except Exception as e:
        print(f"{e}")

def copy_raw_with_paths(self):
    parts = []
    for path, info in self.combined_text_lines.items():
        if not info.get('visible', True):
            continue
        lines = info['text']
        is_raw = bool(info.get('raw'))
        if is_raw:
            # add banner + body
            parts.append(f"=== {path} ===\n{lines[1]}\n")
        else:
            # already [header, body, footer]
            parts.append("\n".join([l for l in lines if l is not None]))
        parts.append("\n――――――――――――――――――\n")
    payload = "\n".join(parts).rstrip()
    QtWidgets.QApplication.clipboard().setText(payload)
    self.status.setText("✅ Copied with absolute paths")
def _toggle_populate_text_view(self, view_toggle=None) -> None:
    try:
        if view_toggle:
            self.view_toggle = view_toggle
        self._populate_text_view()
    except Exception as e:
        print(f"{e}")
def on_file_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
    """Emit the selected file (any type) with its current text."""
    try:
        path = item.data(Qt.ItemDataRole.UserRole)
        info = self.combined_text_lines.get(path)
        if not info:
            # Fallback: read from disk if it wasn't in the dict for some reason
            body = read_file_as_text(path) or ""
            payload = ["", body, ""] if os.path.splitext(path)[1].lower() in {'.json','.ts','.tsx','.js','.css','.html','.md'} else [f"=== {path} ===", body, ""]
            info = {'path': path, 'text': payload, 'raw': True}
        self.file_selected.emit(info)
    except Exception as e:
        print(f"{e}")
def populate_file_view(self) -> None:
    """List *all* currently processed files, not just .py."""
    try:
        self.python_file_list.clear()
        # All files we processed in this pass:
        all_paths = list(self.combined_text_lines.keys())
        if not all_paths:
            self.python_file_list.setVisible(False)
            return
        # Which of the originally provided paths are still visible per filters:
        filtered_set = set(self.filter_paths(self._last_raw_paths))
        for p in all_paths:
            base = os.path.basename(p)
            item = QtWidgets.QListWidgetItem(base)
            item.setToolTip(p)  # show absolute path on hover
            item.setData(Qt.ItemDataRole.UserRole, p)  # store absolute path
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if p in filtered_set else Qt.CheckState.Unchecked)
            self.python_file_list.addItem(item)
        self.python_file_list.setVisible(True)
    except Exception as e:
        print(f"{e}")
