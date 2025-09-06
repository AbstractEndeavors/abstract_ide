from ..imports import *
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QTreeWidgetItem

def _clear_files_tree(self):
    self.files_list.clear()

def _add_file_row(self, path: str, apply_checked: bool = True, overwrite_checked: bool = False):
    it = QTreeWidgetItem(self.files_list)
    it.setText(0, path)
    it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    it.setCheckState(1, Qt.CheckState.Checked if apply_checked else Qt.CheckState.Unchecked)
    it.setCheckState(2, Qt.CheckState.Checked if overwrite_checked else Qt.CheckState.Unchecked)
    it.setData(0, Qt.ItemDataRole.UserRole, path)

def _fill_files_tree(self, files: list[str], *, default_apply=True, default_overwrite=False):
    self._clear_files_tree()
    if not files:
        return
    self.files_list.setUpdatesEnabled(False)
    for fp in files:
        self._add_file_row(fp, apply_checked=default_apply, overwrite_checked=default_overwrite)
    self.files_list.setUpdatesEnabled(True)

def _collect_checked_files(self) -> tuple[list[str], list[str]]:
    apply_list, overwrite_list = [], []
    for i in range(self.files_list.topLevelItemCount()):
        it = self.files_list.topLevelItem(i)
        path = it.data(0, Qt.ItemDataRole.UserRole) or it.text(0)
        if it.checkState(1) == Qt.CheckState.Checked:
            apply_list.append(path)
        if it.checkState(2) == Qt.CheckState.Checked:
            overwrite_list.append(path)
    return apply_list, overwrite_list

def _open_file_from_row(self, item: QTreeWidgetItem, column: int):
    path = item.data(0, Qt.ItemDataRole.UserRole) or item.text(0)
    if path and os.path.exists(path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def get_files(self) -> list[str]:
    params = make_params(self)
    dirs, files = get_files_and_dirs(**params)
    return files
