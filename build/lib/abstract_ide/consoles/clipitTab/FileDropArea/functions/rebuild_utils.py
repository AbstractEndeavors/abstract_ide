from ..imports import *
import os
def _apply_ext_filter(self) -> None:
    if self._last_raw_paths:
        self.process_files(self._last_raw_paths)
def _rebuild_ext_row(self, paths: list[str]) -> None:
    exts = {os.path.splitext(p)[1].lower() for p in paths if os.path.isfile(p)}
    exts.discard("")
    self._log(f"Found extensions: {exts}")
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
    self.ext_row_lay.addStretch()
    self.ext_checks = new_checks
    self.ext_row.setVisible(True)
def _rebuild_dir_row(self, paths: list[str]) -> None:
    """Rebuild directory filter row with checkboxes for directory pieces."""
    self.dir_pieces = get_all_dir_pieces(paths)
    self.dir_pieces = set(list(self.dir_pieces))
    dir_pieces = self.dir_pieces
    self._log(f"Directory pieces: {dir_pieces}")
    if not dir_pieces:
        self.dir_row.setVisible(False)
        self.dir_checks.clear()
        self._log("No directory pieces found; hiding dir_row.")
        return
    self._clear_layout(self.dir_row_lay)
    new_checks: dict[str, QtWidgets.QCheckBox] = {}
    for dir_name in dir_pieces:
        cb = QtWidgets.QCheckBox(dir_name)
        prev_cb = self.dir_checks.get(dir_name)
        cb.setChecked(prev_cb.isChecked() if prev_cb else False)
        cb.stateChanged.connect(self._apply_ext_filter)
        self.dir_row_lay.addWidget(cb)
        new_checks[dir_name] = cb
    self.dir_row_lay.addStretch()
    self.dir_checks = new_checks
    self.dir_row.setVisible(True)
