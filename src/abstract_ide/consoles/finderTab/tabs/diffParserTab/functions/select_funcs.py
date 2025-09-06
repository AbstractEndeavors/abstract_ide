from ..imports import *
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidget, QListWidget, QTreeWidgetItem, QListWidgetItem

def _get_selected_path_from_tree(self) -> str | None:
    it: QTreeWidgetItem | None = self.files_list.currentItem()
    if not it: 
        return None
    # Only consider if Apply checked
    if it.checkState(1) != Qt.CheckState.Checked:
        return None
    return it.data(0, Qt.ItemDataRole.UserRole) or it.text(0)

def _get_first_apply_checked_from_tree(self) -> str | None:
    for i in range(self.files_list.topLevelItemCount()):
        it = self.files_list.topLevelItem(i)
        if it.checkState(1) == Qt.CheckState.Checked:
            return it.data(0, Qt.ItemDataRole.UserRole) or it.text(0)
    return None

def _get_selected_path_from_list(self) -> str | None:
    # For QListWidget variant (not used here, but kept for parity)
    sel: list[QListWidgetItem] = self.files_list.selectedItems()  # type: ignore[attr-defined]
    if sel:
        return sel[0].data(Qt.ItemDataRole.UserRole) or sel[0].text()
    if getattr(self.files_list, "count", None) and self.files_list.count() > 0:
        it = self.files_list.item(0)  # type: ignore[attr-defined]
        return it.data(Qt.ItemDataRole.UserRole) or it.text()
    return None

def _on_tree_selection_changed(self):
    """If diff is present, preview the selected (Apply-checked) file, or first Apply-checked."""
    diff = self.diff_text.toPlainText().strip()
    if not diff:
        return
    path = _get_selected_path_from_tree(self) or _get_first_apply_checked_from_tree(self)
    if path and os.path.exists(path):
        self._preview_for_path(path)

def _pick_preview_target(self, files_from_filters: list[str], hunks) -> str | None:
    # Priority A/B/C as before
    path = _get_selected_path_from_tree(self)
    if path and os.path.exists(path): return path
    path = _get_first_apply_checked_from_tree(self)
    if path and os.path.exists(path): return path

    # fallback: match first hunk
    first = next((h for h in hunks if h.subs), None)
    candidates = files_from_filters[:]
    if first and first.subs:
        _, found = getPaths(files_from_filters, first.subs)
        candidates = sorted({fp['file_path'] for fp in found}) or files_from_filters

    # last resort: ask
    return self._ask_user_to_pick_file(candidates, title="Pick a file to preview")
