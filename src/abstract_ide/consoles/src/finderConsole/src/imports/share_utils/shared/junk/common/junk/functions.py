from PyQt6.QtWidgets import QListWidgetItem
def make_string(x):
    if isinstance(x, (list, tuple, set)):
        return ",".join(str(i) for i in x)
    return "" if x is None else str(x)

def _norm_csv(val, *, lower=True, split_chars=(",","|")):
    """Normalize a CSV/pipe string or iterable to a sorted tuple for stable compare."""
    if not val or val is False:
        return tuple()
    if isinstance(val, (list, tuple, set)):
        items = [str(v) for v in val]
    else:
        s = str(val)
        for ch in split_chars[1:]:
            s = s.replace(ch, split_chars[0])
        items = [p.strip() for p in s.split(split_chars[0]) if p.strip()]
    if lower:
        items = [i.lower() for i in items]
    return tuple(sorted(items))

def _filters_subset(state: dict) -> dict:
    """Just the filter fields (the ones you care about for auto-unlink)."""
    return {
        "allowed_exts":    _norm_csv(state.get("allowed_exts", "")),
        "unallowed_exts":  _norm_csv(state.get("unallowed_exts", "")),
        "exclude_types":   _norm_csv(state.get("exclude_types", ""), lower=False),
        "exclude_dirs":    _norm_csv(state.get("exclude_dirs", ""),  lower=False),
        "exclude_patterns":_norm_csv(state.get("exclude_patterns",""),lower=False),
    }

def _read_state(h) -> dict:
    return dict(
        directory=h.dir_in.text(),
        strings=h.strings_in.text(),
        allowed_exts=h.allowed_exts_in.text(),
        unallowed_exts=h.unallowed_exts_in.text(),
        exclude_types=h.exclude_types_in.text(),
        exclude_dirs=h.exclude_dirs_in.text(),
        exclude_patterns=h.exclude_patterns_in.text(),
        add=h.chk_add.isChecked(),
        recursive=h.chk_recursive.isChecked(),
        total_strings=h.chk_total.isChecked(),
        parse_lines=h.chk_parse.isChecked(),
        get_lines=h.chk_getlines.isChecked(),
        spec_line=h.spec_spin.value(),
    )

def _write_state(h, s: dict):
    h._applying_remote = True
    try:
        for w, val, setter in (
            (h.dir_in,              s.get("directory",""), lambda w,v: w.setText(v)),
            (h.strings_in,          s.get("strings",""),   lambda w,v: w.setText(v)),
            (h.allowed_exts_in,     s.get("allowed_exts",""), lambda w,v: w.setText(v)),
            (h.unallowed_exts_in,   s.get("unallowed_exts",""), lambda w,v: w.setText(v)),
            (h.exclude_types_in,    s.get("exclude_types",""), lambda w,v: w.setText(v)),
            (h.exclude_dirs_in,     s.get("exclude_dirs",""), lambda w,v: w.setText(v)),
            (h.exclude_patterns_in, s.get("exclude_patterns",""), lambda w,v: w.setText(v)),
        ):
            with QSignalBlocker(w): setter(w, val)

        for w, val in (
            (h.chk_add,       s.get("add", False)),
            (h.chk_recursive, s.get("recursive", True)),
            (h.chk_total,     s.get("total_strings", False)),
            (h.chk_parse,     s.get("parse_lines", False)),
            (h.chk_getlines,  s.get("get_lines", True)),
        ):
            with QSignalBlocker(w): w.setChecked(val)

        with QSignalBlocker(h.spec_spin):
            h.spec_spin.setValue(int(s.get("spec_line", 0)) or 0)
    finally:
        h._applying_remote = False

def init_results_ui(self):
    # Wire helpers
    self.browse_dir = browse_dir

    self.make_params = make_params  # still returns dict of knobs (optional if you use _compute_files_from_self)

    # Log  Results UI
    
    self.layout().addWidget(QLabel("Results"))
    self.layout().addWidget(self.log, stretch=2)

    self.results_list = QListWidget()
    self.results_list.setUniformItemSizes(True)
    self.results_list.setSelectionMode(self.results_list.SelectionMode.ExtendedSelection)

    # bind as a free function with self
    self.results_list.itemDoubleClicked.connect(lambda it: _open_result(self, it))
    self.layout().addWidget(self.results_list, stretch=3)

    self._last_results = []
    attach_textedit_to_logs(self.log, tail_file=get_log_file_path())

    # Refresh when the shared bus broadcasts changes (and we’re linked)
    def _on_bus_change(sender, state):
        if getattr(self, "link_btn", None) and not self.link_btn.isChecked():
            return
        self._refresh_results()
    self._bus.stateBroadcast.connect(_on_bus_change)

    # Initial fill
    self._refresh_results()
    self = set_self_log(self)
    return self

def _open_result(self, item: QListWidgetItem):
    path = item.data(Qt.ItemDataRole.UserRole) or item.text()
    if not path:
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def _refresh_results(self):
    """Recompute the filtered files and (re)populate the list."""
    try:
        files = self.make_params()  # pulls from all current filters
    except Exception as e:
        if hasattr(self, "log"):
            self.log.append(f"Search failed: {e}\n")
        return

    self._last_results = files
    self.results_list.clear()

    for path in files:
        it = QListWidgetItem(path)  # show the path (or os.path.basename(path) if you prefer)
        it.setData(Qt.ItemDataRole.UserRole, path)  # keep full path
        self.results_list.addItem(it)

    if hasattr(self, "status_label"):
        n = len(files)
        self.status_label.setText(f"Found {n} file{'s' if n != 1 else ''}.")
        self.status_label.setStyleSheet("color: #2196f3;")  # blue




##def getSearchFilters(self):
##
##    self.browse_dir = browse_dir
##    self.make_params = make_params
##    set_self_log(self)
##    self.layout().addWidget(QLabel("Results"))
##    self.layout().addWidget(self.log, stretch=2)
##    self.list = QListWidget()
##    self.list.itemDoubleClicked.connect(self.open_one)
##    self.layout().addWidget(self.list, stretch=3)
##    self._last_results = []
##    attach_textedit_to_logs(self.log, tail_file=get_log_file_path())
##    return self

