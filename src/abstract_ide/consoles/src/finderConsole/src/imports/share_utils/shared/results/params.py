from PyQt6.QtWidgets import QFileDialog,QListWidgetItem
from abstract_utilities import define_defaults
from .resolve_directory import resolve_directory_input
import os,sys
# — UI helpers —
def browse_dir(self):
    d = QFileDialog.getExistingDirectory(
        self,
        "Choose directory",
        self.dir_in.text() or os.getcwd(),
    )
    if not d:
        return

    try:
        d = resolve_directory_input(d)
    except Exception:
        return  # or show QMessageBox

    self.dir_in.setText(d)
def on_dir_edit_finished(self):
    try:
        resolved = resolve_directory_input(self.dir_in.text())
        self.dir_in.setText(resolved)
    except Exception:
        pass  # let validation handle it later
def make_params(self):
    directory = resolve_directory_input(self.dir_in.text())

    # strings
    s_raw = [s.strip() for s in self.strings_in.text().split(",") if s.strip()]

    # allowed_exts
    e_raw = self.allowed_exts_in.text().strip()
    allowed_exts: Union[bool, Set[str]] = None
    if e_raw:
        splitter = "|" if "|" in e_raw else ","
        allowed_exts = {
            "." + e if not e.startswith(".") else e
            for e in (x.strip() for x in e_raw.split(splitter))
            if e
        }

    # exclude_exts
    ee_raw = self.exclude_exts_in.text().strip()
    exclude_exts: Union[bool, Set[str]] = None
    if ee_raw:
        splitter = "|" if "|" in ee_raw else ","
        exclude_exts = {
            "." + e if not e.startswith(".") else e
            for e in (x.strip() for x in ee_raw.split(splitter))
            if e
        }

    # allowed_types
    at_raw = self.allowed_types_in.text().strip()
    allowed_types = {e.strip() for e in at_raw.split(",") if e.strip()} if at_raw else None

    # exclude_types
    et_raw = self.exclude_types_in.text().strip()
    exclude_types = {e.strip() for e in et_raw.split(",") if e.strip()} if et_raw else None

    # allowed_dirs
    ad_raw = self.allowed_dirs_in.text().strip()
    allowed_dirs = [e.strip() for e in ad_raw.split(",") if e.strip()] if ad_raw else None

    # exclude_dirs
    ed_raw = self.exclude_dirs_in.text().strip()
    exclude_dirs = [e.strip() for e in ed_raw.split(",") if e.strip()] if ed_raw else None

    # allowed_patterns
    ap_raw = self.allowed_patterns_in.text().strip()
    allowed_patterns = [e.strip() for e in ap_raw.split(",") if e.strip()] if ap_raw else None

    # exclude_patterns
    ep_raw = self.exclude_patterns_in.text().strip()
    exclude_patterns = [e.strip() for e in ep_raw.split(",") if e.strip()] if ep_raw else None

    add = self.chk_add.isChecked()

    spec_line_val = self.spec_spin.value()
    spec_line = False if spec_line_val == 0 else int(spec_line_val)

    cfg = define_defaults(
        allowed_exts=allowed_exts,
        exclude_exts=exclude_exts,
        allowed_types=allowed_types,
        exclude_types=exclude_types,
        allowed_dirs=allowed_dirs,
        exclude_dirs=exclude_dirs,
        allowed_patterns=allowed_patterns,
        exclude_patterns=exclude_patterns,
        add=add,
    )

    return {
        "directory": directory,
        "get_lines": self.chk_getlines.isChecked(),
        "spec_line": spec_line,
        "parse_lines": self.chk_parse.isChecked(),
        "total_strings": self.chk_total.isChecked(),
        "strings": s_raw,
        "recursive": self.chk_recursive.isChecked(),
        "cfg": cfg,
    }
