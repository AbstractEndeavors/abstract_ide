from ..imports import *
def populate_python_view(self) -> None:
    try:
        self.python_file_list.clear()
        all_paths = [info['path'] for info in self.python_files]
        filtered_set = set(self.filter_paths(self._last_raw_paths))
        for p in all_paths:
            item = QtWidgets.QListWidgetItem(os.path.basename(p))
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if p in filtered_set else Qt.CheckState.Unchecked)
            self.python_file_list.addItem(item)
        self.python_file_list.setVisible(bool(all_paths))
    except Exception as e:
        print(f"{e}")
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
        self.populate_python_view()
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
