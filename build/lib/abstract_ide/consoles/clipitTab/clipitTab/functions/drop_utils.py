from ..imports import *
def _toggle_logs(self, checked: bool):
    """
    Show/hide the log console when the toolbar action is toggled.
    """
    if checked:
        self.log_widget.show()
        self.toggle_logs_action.setText("Hide Logs")
        self._log("Logs shown.")
    else:
        self._log("Logs hidden.")
        self.log_widget.hide()
        self.toggle_logs_action.setText("Show Logs")

def _toggle_view(self, checked: bool):
    """
    Show/hide the log console when the toolbar action is toggled.
    """
    if checked:
        self.view_widget = 'array'
        self.toggle_view_action.setText("View Print")
        self._log("View Array.")
    else:
        self._log("View Print.")
        self.view_widget = 'print'
        self.toggle_view_action.setText("View Array")
    self.drop_area._toggle_populate_text_view(view_toggle=self.view_widget)
def on_tree_copy(self, paths: List[str]):
    """
    Called when the “Copy Selected” button is pressed.
    We log how many items, then forward to drop_area.
    """
    self._log(f"Copy Selected triggered on {len(paths)} path(s).")
    self.drop_area.process_files(paths)
def copy_raw(self):
    chunks = []
    for _, info in self.combined_text_lines.items():
        txt = info.get('text')
        body = txt[1] if isinstance(txt, list) else str(txt or "")
        chunks.append(body)
    QtWidgets.QApplication.clipboard().setText("\n\n".join(chunks))
    self._log("✅ Copied RAW bodies to clipboard")

def on_tree_double_click(self, index: QtCore.QModelIndex):
    model = self.tree_wrapper.model
    path = model.filePath(index)
    if path:
        self._log(f"Double-clicked: {path}")
        self.drop_area.process_files([path])

def on_function_selected(self, function_info: dict):
    """
    Handle function selection: map imports and project reach, then copy to clipboard.
    """
    self._log(f"Function selected: {function_info['name']} from {function_info['file']}")
    self.drop_area.map_function_dependencies(function_info)

def on_file_selected(self, file_info: dict):
    """
    Handle Python file selection: map import chain, then copy to clipboard.
    """
    self._log(f"Python file selected: {file_info['path']}")
    self.drop_area.map_import_chain(file_info)

def _log(self, message: str):
    """Write to the shared log widget with a timestamp."""
    log_it(self=self, message=message)
