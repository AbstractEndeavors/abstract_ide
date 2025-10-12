def _update_dict_preview(self, item):
        # show the dict of the highlighted row
        ['msg','vars']
        if not item:
            self.dict_view.clear()
            return
        data = item.data(0, QtCore.Qt.ItemDataRole.UserRole) or {}
            # children store {'role':'child','entry': <dict>}; parents store {'role':'parent','path':..., 'entries':[dict,...]}
        payload = data.get('entry', data)
        entries = make_list(payload.get('entries',payload))
        string = ""
        for i,entry in enumerate(entries):
            path = entry.get('path')
            if string == "":
                string+=f"path == {path}\n"
            string+=f"entry {i}:\n"
            variables = entry.get('vars')
            message = entry.get('msg')
            string+=f"vars == {variables}\n"
            string+=f"msg == {message}\n"


        self.dict_view.setPlainText(string)

def init_dict_panel_creation(self):
    dict_panel = QtWidgets.QWidget(self)
    dict_row   = QtWidgets.QHBoxLayout(dict_panel)
    self.dict_view = QtWidgets.QPlainTextEdit()
    self.dict_view.setReadOnly(True)
    self.dict_view.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
    self.dict_view.setMinimumHeight(120)
    # keep it short by default (grows only if you drag the splitter)
    self.dict_view.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                 QtWidgets.QSizePolicy.Policy.Preferred)
    mono = self.dict_view.font(); mono.setFamily("monospace"); self.dict_view.setFont(mono)
    dict_row.addWidget(self.dict_view)   # <- addWidget, not addLayout
    # connect once after trees are created:
    for t in (self.errors_tree, self.warnings_tree, self.all_tree):
        t.currentItemChanged.connect(lambda cur, prev: self._update_dict_preview(cur))
        t.itemClicked.connect(lambda it, col: self._update_dict_preview(it))
    
    return dict_panel
def start_work(self):
    try:
        self.run_btn.setEnabled(False)
        user = self.user_in.text().strip() or 'solcatcher'   # <- swap order (yours hard-coded the default)
        path = self.path_in.text().strip()
        if not path or not os.path.isdir(path):
            QMessageBox.critical(self, "Error", "Invalid project path.")
            self.run_btn.setEnabled(True)
            return

        # Clear old UI bits
        self.errors_tree.clear()
        self.warnings_tree.clear()
        
        # Kick off non-blocking build
        self._run_build_qprocess(path)
        
    except Exception:
        self.append_log("start_work error:\n" + traceback.format_exc() + "\n")
        self.run_btn.setEnabled(True)

def clear_ui(self):
    self.log_view.clear()
    self.errors_tree.clear()
    self.warnings_tree.clear()
    self.last_output = ""
    self.last_errors_only = ""
    self.last_warnings_only = ""


# ── helpers ──────────────────────────────────────────────────────────────
def _replace_log(self, text: str):
    try:
        self.log_view.clear()
        self.log_view.insertPlainText(text)
    except Exception as e:
        print(f"{e}")

def _parse_item(self, info: str):
    try:
        parts = info.rsplit(":", 2)
        if len(parts) == 3:
            path, line, col = parts[0], parts[1], parts[2]
        else:
            path, line, col = parts[0], parts[1], "1"
        return path, int(line), int(col)
    except Exception as e:
        print(f"{e}")

def _extract_errors_for_file(self, combined_text: str, abs_path: str, project_root: str) -> str:
    try:
        text = combined_text or ""
        if not text:
            return ""
        try:
            rel = os.path.relpath(abs_path, project_root) if (project_root and abs_path.startswith(project_root)) else os.path.basename(abs_path)
        except Exception:
            rel = os.path.basename(abs_path)
        rel_alt = rel.replace("\\", "/")
        abs_alt = abs_path.replace("\\", "/")
        base = os.path.basename(abs_alt)
        lines = text.splitlines()
        blocks = []
        for i, ln in enumerate(lines):
            if (abs_alt in ln) or (rel_alt in ln) or (("src/" + base) in ln):
                start = max(0, i - 3)
                end = min(len(lines), i + 6)
                block = "\n".join(lines[start:end])
                blocks.append(f"\n— context @ log line {i+1} —\n{block}\n")
        return "\n".join(blocks).strip()
    except Exception as e:
        print(f"{e}")

def create_radio_group(self, labels, default_index=0, slot=None):
    group = QButtonGroup(self)
    buttons = []
    for i, label in enumerate(labels):
        rb = QRadioButton(label)
        if i == default_index:
            rb.setChecked(True)
        group.addButton(rb)
        buttons.append(rb)
        if slot:
            rb.toggled.connect(slot)
    return group, buttons
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

# ────────────────────────── basic logging ──────────────────────────
def append_log(self, text):
    cursor = self.log_view.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    self.log_view.setTextCursor(cursor)
    self.log_view.insertPlainText(text)
    logging.getLogger("reactRunner.ui").info(text.rstrip("\n"))
# ────────────────────────── formatters ─────────────────────────────
def _format_entry_for_log(e: dict) -> str:
    code = f" {e['code']}" if e.get('code') else ""
    return f"{e['severity'].upper()}{code}: {e['path']}:{e['line']}:{e['col']} — {e['message']}"

def set_last_output(self, text: str):
    def _fmt(e: dict) -> str:
        code = f" {e['code']}" if e.get('code') else ""
        return f"{e['severity'].upper()}{code}: {e['path']}:{e['line']}:{e['col']} — {e['message']}"
    
    run_build_get_errors()
    self.parsed_logs = run_build_get_errors(self.init_path)  # returns dicts
  
    self.append_log('habbening')
    self.last_errors_only   = self.parsed_logs["errors_only"]
    self.last_warnings_only = self.parsed_logs["warnings_only"]
    self.last_all_only      = self.parsed_logs["all_only"]

    self.show_error_entries(self.parsed_logs["errors"])      # ← dicts
    self.show_warning_entries(self.parsed_logs["warnings"])  # ← dicts
    self.show_all_entries(self.parsed_logs["entries"])       # ← dicts
    self.apply_log_filter()



def setup_issue_tree(self,tree):
    tree.setRootIsDecorated(False)
    tree.setUniformRowHeights(True)
    tree.setAlternatingRowColors(True)
    hdr = tree.header()
    # 0 = File/Issue (parent shows file path), 1 = Line, 2 = Msg
    hdr.setStretchLastSection(False)
    hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

def _ensure_alt_ext(self, e: dict, *, keys=DEFAULT_KEYS):
    """Optional: flip .ts → .tsx etc when the checkbox is on."""
    if not getattr(self.cb_try_alt_ext, 'isChecked', lambda: False)():
        return e
    try:
        project = self.path_in.text().strip()
        e = dict(e)  # shallow copy
        e[keys['path']] = self.resolve_alt_ext(e.get(keys['path'], ''), project)
        return e
    except Exception:
        return e

def _editor_open_file(self, path: str, line: int, col: int | None):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        self.current_file_path = path
        self.original_text = text
        self.editor.setPlainText(text)
        self._editor_clear_highlights()
        self._editor_goto_and_mark(line, col)
    except Exception as e:
        self.append_log(f"[editor] open error: {e}\n")

# ────────────────────────── tree helpers ───────────────────────────
def _group_by_path_dict(self, entries: list[dict], *, keys=DEFAULT_KEYS):
    """Group dict entries by file path; sort each group by (line,col)."""
    out: dict[str, list[dict]] = {}
    for e in entries or []:
        e = _ensure_alt_ext(self, e, keys=keys)
        p = e.get(keys['path'], '')
        out.setdefault(p, []).append(e)
    # stable sort per file
    for p, lst in out.items():
        lst.sort(key=lambda d: (int(d.get(keys['line'], 1) or 1),
                                int(d.get(keys['col'],  1) or 1)))
    return out

def _populate_tree_dict(tree, groups: dict[str, list[dict]], *, keys=DEFAULT_KEYS):
    """Build parent=path row; child rows carry the full entry dict in UserRole."""
    tree.clear()
    for path, items in sorted(groups.items()):
        parent = QTreeWidgetItem([path, str(len(items)), ""])
        parent.setData(0, Qt.ItemDataRole.UserRole, {'role':'parent',
                                                     'path': path,
                                                     'entries': items})
        parent.setToolTip(0, path)
        for e in items:
            ln  = int(e.get(keys['line'], 1) or 1)
            col = int(e.get(keys['col'],  1) or 1)
            code = e.get(keys['code']) or ""
            msg  = e.get(keys['msg'], "") or ""
            # Columns: [File/Issue(empty for child), Line, Msg]
            child = QTreeWidgetItem(["", f"{ln}:{col}", f"{('['+code+'] ') if code else ''}{msg}"])
            child.setToolTip(2, msg)
            child.setData(0, Qt.ItemDataRole.UserRole, {'role':'child', 'entry': e})
            parent.addChild(child)
        tree.addTopLevelItem(parent)
    tree.expandToDepth(0)

def _normalize_entries(self, entries):
    """Ensure (path,line,col,msg,code) and optionally resolve alt ext."""
    norm = []
    try_alt = self.cb_try_alt_ext.isChecked()
    project = self.path_in.text().strip()
    for it in entries or []:
        path, line, col = it[0], it[1], (it[2] or 1)
        msg  = it[3] if len(it) > 3 else ""
        code = it[4] if len(it) > 4 else ""
        if try_alt:
            # use global resolve_alt_ext imported in helpers
            path = self.resolve_alt_ext(path, project)
        norm.append((path, line, col, msg, code))
    return norm
 
def show_error_entries(self, entries):
    groups = _group_by_path_dict(self, entries, keys=DEFAULT_KEYS)
    _populate_tree_dict(self.errors_tree, groups, keys=DEFAULT_KEYS)

def show_warning_entries(self, entries):
    groups = _group_by_path_dict(self, entries, keys=DEFAULT_KEYS)
    _populate_tree_dict(self.warnings_tree, groups, keys=DEFAULT_KEYS)

def show_all_entries(self, entries):
    groups = _group_by_path_dict(self, entries, keys=DEFAULT_KEYS)
    _populate_tree_dict(self.all_tree, groups, keys=DEFAULT_KEYS)
def apply_log_filter(self):
     if self.rb_err.isChecked():
         self._replace_log(self.last_errors_only or "(no errors)")
     elif self.rb_wrn.isChecked():
         self._replace_log(self.last_warnings_only or "(no warnings)")
     elif self.rb_all.isChecked():
         self._replace_log(self.last_all_only or "(all entries)")
     else:
        self._replace_log(self.last_output or "")

# ────────────────────────── optional: click hookup ─────────────────
# In your build_ui, make sure you connect the trees to an item click:
#   self.errors_tree.itemClicked.connect(self._on_tree_item_clicked)
#   self.warnings_tree.itemClicked.connect(self._on_tree_item_clicked)
# and implement (in clickHandlers_utils.py or here):
def get_ranges_from_item(item, *, keys=DEFAULT_KEYS):
    """
    Returns (path, entries, ranges) for the clicked item's file group.
    ranges = [{'line','col','message','code'}, ...]
    """
    data = item.data(0, Qt.ItemDataRole.UserRole) or {}
    if data.get('role') == 'parent':
        path    = data.get('path', '')
        entries = data.get('entries', []) or []
    else:
        # child → go to its parent container
        parent  = item.parent()
        pdata   = parent.data(0, Qt.ItemDataRole.UserRole) or {}
        path    = pdata.get('path', '')
        entries = pdata.get('entries', []) or []

    ranges = []
    for e in entries:
        ranges.append({
            'line':    int(e.get(keys['line'], 1) or 1),
            'col':     int(e.get(keys['col'],  1) or 1),
            'message': e.get(keys['msg'], "") or "",
            'code':    e.get(keys['code']) or "",
        })
    return path, entries, ranges
def on_tree_item_clicked(self, item, col, *, keys=DEFAULT_KEYS):
    data = item.data(0, Qt.ItemDataRole.UserRole) or {}
    if data.get('role') == 'child':
        e   = data['entry']
        p   = e.get(keys['path'], '')
        ln  = int(e.get(keys['line'], 1) or 1)
        cl  = int(e.get(keys['col'],  1) or 1)
        # open/jump
        if p != getattr(self, "current_file_path", None):
            self._editor_open_file(p, ln, cl)
        else:
            self._editor_goto_and_mark(ln, cl)
        # show all ranges for this file, centered on clicked row
        path, _entries, ranges = get_ranges_from_item(item, keys=keys)
        self._editor_show_ranges(path, ranges, center=(ln, cl))
        return

    if data.get('role') == 'parent':
        path, _entries, ranges = get_ranges_from_item(item, keys=keys)
        center = (ranges[0]['line'], ranges[0]['col']) if ranges else (1, 1)
        self._editor_show_ranges(path, ranges, center=center)


def initializeInit(self):
    self.fn_filter_mode = "io"   # "source" | "io" | "all"
    self.current_fn = None       # last clicked function name

    self.setWindowTitle("🔍 React Build Finder")
    self.resize(1100, 720)

    self.cb_try_alt_ext = QCheckBox("Try alternate extensions")
    self.cb_try_alt_ext.setChecked(True)

    # state
    self.last_output = ""
    self.last_errors_only = ""
    self.last_warnings_only = ""
    self.last_all_only = ""
    self.parsed_logs = {'entries': [], 'by_file': {}}

    # editor state
    self.current_file_path = None
    self.original_text = ""

    # editor widgets (wired into layout in runnerTab/main.py)
    self.editor = QPlainTextEdit()
    self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    try:
        f = self.editor.font(); f.setFamily("Fira Code"); f.setStyleHint(QFont.StyleHint.Monospace); f.setFixedPitch(True)
        self.editor.setFont(f)
    except Exception:
        pass
    self.btn_save   = QPushButton("Save")
    self.btn_revert = QPushButton("Revert")
    self.btn_save.clicked.connect(self._editor_save_current)
    self.btn_revert.clicked.connect(self._editor_revert_current)
    default_user = "solcatcher"
##    # inputs
##    try:
##        default_user = os.getlogin()
##    except Exception:
##        default_user = "solcatcher"
    self.user_in = QLineEdit(default_user)
    self.user_in.setPlaceholderText("ssh solcatcher")
    self.path_in = QLineEdit(self.init_path)
    self.path_in.setPlaceholderText("Project path (folder with package.json)")

    # buttons
    self.run_btn = QPushButton("Run");    self.run_btn.clicked.connect(self.start_work)
    self.rerun_btn = QPushButton("Re-run build"); self.rerun_btn.clicked.connect(self.start_work)
    self.clear_btn = QPushButton("Clear"); self.clear_btn.clicked.connect(self.clear_ui)

    # log + filter
    self.log_view = QTextEdit(); self.log_view.setReadOnly(True);
    self.log_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    self.filter_group, rbs = self.create_radio_group(["All", "Errors only", "Warnings only"], 0, self.apply_log_filter)
    self.rb_all, self.rb_err, self.rb_wrn = rbs

    # lists
    # trees (grouped by file)
    
    # trees (grouped by file)
    self.errors_tree   = self.build_group_tree()
    self.warnings_tree = self.build_group_tree()
    self.all_tree = self.build_group_tree()
    # clicks -> open in editor / highlight
    self.errors_tree.itemClicked.connect(lambda i,c: self.on_tree_item_clicked(i, c))
    self.warnings_tree.itemClicked.connect(lambda i,c: self.on_tree_item_clicked(i, c))
    self.all_tree.itemClicked.connect(lambda i,c: self.on_tree_item_clicked(i, c))
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

def _editor_clear_highlights(self):
    try:
        self._hi_ranges = []
        self.editor.setExtraSelections([])  # replaces any previous overlays
    except Exception:
        pass

def _make_line_selection(self, line: int, bg: QColor):
    # IMPORTANT: use QTextEdit.ExtraSelection even with QPlainTextEdit
    sel = QTextEdit.ExtraSelection()
    tc = self.editor.textCursor()
    blk = self.editor.document().findBlockByNumber(max(1, int(line)) - 1)
    tc.setPosition(blk.position())
    tc.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                    QTextCursor.MoveMode.KeepAnchor)
    sel.cursor = tc
    fmt = QTextCharFormat()
    fmt.setBackground(bg)
    sel.format = fmt
    return sel

def _editor_goto_and_mark(self, line: int, col: int | None):
    try:
        line = max(1, int(line)); col = max(1, int(col or 1))
        doc = self.editor.document()
        blk = doc.findBlockByNumber(line - 1)
        pos = blk.position() + (col - 1)

        tc = self.editor.textCursor()
        tc.setPosition(pos)
        self.editor.setTextCursor(tc)
        self.editor.centerCursor()

        focused = self._make_line_selection(line, QColor(255, 255, 0, 90))
        self.editor.setExtraSelections([focused])
    except Exception as e:
        self.append_log(f"[editor] mark error: {e}\n")

def _editor_show_ranges(self, path: str, ranges: list[dict], center: tuple[int,int]|None=None):
    try:
        if path != getattr(self, "current_file_path", None):
            first = ranges[0] if ranges else {"line": 1, "col": 1}
            self._editor_open_file(path, int(first["line"]), int(first["col"]))

        extras = []
        for r in ranges:
            ln = max(1, int(r.get("line", 1)))
            extras.append(self._make_line_selection(ln, QColor(255, 200, 0, 70)))

        if center:
            extras.append(self._make_line_selection(center[0], QColor(255, 255, 0, 110)))
            # move caret to the focused position for scrolling/column
            self._editor_goto_and_mark(center[0], center[1])

        self.editor.setExtraSelections(extras)
    except Exception as e:
        self.append_log(f"[editor] ranges error: {e}\n")
# Call this whenever you refresh issues:
def update_issues(self, errors_rows, warnings_rows,all_rows):
    """
    errors_rows / warnings_rows formats accepted:
      - ["file or issue", "line", "msg"]
      - or grouped: [[topCols...], [child1...], [child2...], ...]
    """
    self._fill_tree(self.errors_tree, errors_rows)
    self._fill_tree(self.warnings_tree, warnings_rows)
    self._fill_tree(self.all_tree, all_rows)
    # keep “All” page in sync
    self._fill_tree(self.errors_tree_all, errors_rows)
    self._fill_tree(self.warnings_tree_all, warnings_rows)
    self._fill_tree(self.all_tree_all, all_rows)
def init_set_buttons(self,tree_stack):
    self.rb_err.toggled.connect(lambda on: on and tree_stack.setCurrentIndex(0))
    self.rb_wrn.toggled.connect(lambda on: on and tree_stack.setCurrentIndex(1))
    self.rb_all.toggled.connect(lambda on: on and tree_stack.setCurrentIndex(2))

    # Initial page
    if getattr(self.rb_err, "isChecked", lambda: False)():
        tree_stack.setCurrentIndex(0)
    elif getattr(self.rb_wrn, "isChecked", lambda: False)():
        tree_stack.setCurrentIndex(1)
    else:
        tree_stack.setCurrentIndex(2)
def init_tree_creation(self,layout=None):
    if layout is None:
        layout = QStackedWidget(self)
    # Primary trees (used by Errors page and Warnings page)
    # If initializeInit already created them, keep yours. Otherwise create here:
    if not hasattr(self, "errors_tree"):
        self.errors_tree = QTreeWidget()
        self.errors_tree.setHeaderLabels(["File / Issue", "Line", "Msg"])
    if not hasattr(self, "warnings_tree"):
        self.warnings_tree = QTreeWidget()
        self.warnings_tree.setHeaderLabels(["File / Issue", "Line", "Msg"])
    if not hasattr(self, "all_tree"):
        self.all_tree = QTreeWidget()
        self.all_tree.setHeaderLabels(["File / Issue", "Line", "Msg"])
    self.setup_issue_tree(self.errors_tree)
    self.setup_issue_tree(self.warnings_tree)
    self.setup_issue_tree(self.all_tree)
    
    # Page 0: Errors
    p_err = QWidget(); l_err = QVBoxLayout(p_err)
    l_err.addWidget(QLabel("Errors (grouped by file):"))
    l_err.addWidget(self.errors_tree)
    layout.addWidget(p_err)

    # Page 1: Warnings
    p_wrn = QWidget(); l_wrn = QVBoxLayout(p_wrn)
    l_wrn.addWidget(QLabel("Warnings (grouped by file):"))
    l_wrn.addWidget(self.warnings_tree)
    layout.addWidget(p_wrn)

            # Page 1: Warnings
    p_all = QWidget(); l_all = QVBoxLayout(p_all)
    l_all.addWidget(QLabel("all Entries (grouped by file):"))
    l_all.addWidget(self.all_tree)
    layout.addWidget(p_all)

    # Page 2: All (use separate trees to avoid reparenting)
    self.errors_tree_all = QTreeWidget();  self.errors_tree_all.setHeaderLabels(["File / Issue", "Line", "Msg"])
    self.warnings_tree_all = QTreeWidget(); self.warnings_tree_all.setHeaderLabels(["File / Issue", "Line", "Msg"])
    self.all_tree_all = QTreeWidget(); self.warnings_tree_all.setHeaderLabels(["File / Issue", "Line", "Msg"])
    self.setup_issue_tree(self.errors_tree_all)
    self.setup_issue_tree(self.warnings_tree_all)
    self.setup_issue_tree(self.all_tree_all)

    # Expose a simple API you can call after parsing output:

    self._setup_issue_tree = self.setup_issue_tree
    return layout

# ── click handlers ───────────────────────────────────────────────────────


def _pick_build_cmd(self, project_dir: str=None):
    # choose yarn/pnpm/npm by lockfile
    project_dir = project_dir or self.path_in
    if os.path.exists(os.path.join(project_dir, "yarn.lock")):
        return "yarn", ["build"]
    if os.path.exists(os.path.join(project_dir, "pnpm-lock.yaml")):
        return "pnpm", ["build"]
    return "npm", ["run", "build"]

def _run_build_qprocess(self, project_dir: str=None):
    # keep GUI responsive
    project_dir = project_dir or self.path_in
    self.proc = QProcess(self)
    self.proc.setWorkingDirectory(project_dir)
    self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

    # Ensure PATH is sane inside QProcess (common issue with GUI apps)
    env = QProcessEnvironment.systemEnvironment()
    # Augment PATH with common user bins and nvm locations
    path = env.value("PATH") or ""
    extras = [
        os.path.expanduser("~/.local/bin"),
        os.path.expanduser("~/.yarn/bin"),
        os.path.expanduser("~/.config/yarn/global/node_modules/.bin"),
        "/usr/local/bin", "/usr/bin", "/bin",
    ]
    # include nvm default if present
    nvm_default = os.path.expanduser("~/.nvm/versions/node")
    if os.path.isdir(nvm_default):
        # grab the highest version bin
        try:
            versions = sorted(os.listdir(nvm_default))
            if versions:
                extras.insert(0, os.path.join(nvm_default, versions[-1], "bin"))
        except Exception:
            pass
    env.insert("PATH", ":".join(extras + [path]))
    self.proc.setProcessEnvironment(env)

    tool, args = self._pick_build_cmd(project_dir)
    self.append_log(f"[build] tool={tool} args={' '.join(args)}\n")

    # build script as a temp file so we can reproduce it outside the GUI
    sh = f'''
set -exo pipefail
cd {shlex.quote(project_dir)}
if [ -s "$HOME/.nvm/nvm.sh" ]; then . "$HOME/.nvm/nvm.sh"; fi
command -v corepack >/dev/null 2>&1 && corepack enable >/dev/null 2>&1 || true
echo "[env] PATH=$PATH"
node -v || true; npm -v || true; yarn -v || true; pnpm -v || true
test -f package.json || (echo ":: No package.json in $(pwd)"; exit 66)
{ "yarn install --frozen-lockfile" if tool=="yarn" else ("pnpm install --frozen-lockfile" if tool=="pnpm" else "npm ci") }
{tool} {" ".join(args)}
'''.strip()

    # write the script to /tmp and chmod +x
    script_path = os.path.join(tempfile.gettempdir(), f"react-build-{os.getpid()}.sh")
    with open(script_path, "w") as _f:
        _f.write(sh + "\n")
    os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    self.append_log(f"[build] script -> {script_path}\n")

    # wire output/finish/error (Qt6 signal enums)
    self.proc.readyRead.connect(self._on_build_output)  # MergedChannels
    self.proc.finished.connect(self._on_build_finished)
    self.proc.errorOccurred.connect(self._on_build_error)

    self.run_btn.setEnabled(False)
    # run the temp script via bash -lc (MergedChannels collects stderr too)
    self.proc.setProgram("bash")
    self.proc.setArguments(["-lc", f"bash {shlex.quote(script_path)} 2>&1"])
    self.proc.start()

def _on_build_finished(self, code: int, status):
    # status is QProcess.ExitStatus
    self.append_log(f"\n\n[build] exited with code {code}\n")
    if code in (66, 67):
        hint = "No package.json" if code == 66 else "No scripts.build in package.json"
        self.append_log(f"[build] preflight failed: {hint}\n")
    self.run_btn.setEnabled(True)
    # One last sync (in case the final lines arrived very late)
    self.set_last_output(self.last_output)

def _on_build_output(self):
     try:
         chunk = bytes(self.proc.readAll()).decode("utf-8", "ignore")
         if chunk:
             # accumulate full log text
             self.last_output = (self.last_output or "") + chunk
             # update raw log view according to current filter choice
             self.apply_log_filter()
             # parse and refresh lists
             
             
             
             
             # local tiny formatter to avoid any circular imports
             def _fmt(e: dict) -> str:
                code = f" {e['code']}" if e.get('code') else ""
                return f"{e['severity'].upper()}{code}: {e['path']}:{e['line']}:{e['col']} — {e['message']}"
             self.set_last_output(self.last_output)
             # also mirror to logger
             logging.getLogger("reactRunner.build").info(chunk.rstrip("\n"))
     except Exception:
         self.append_log("readAllStandardOutput error:\n" + traceback.format_exc() + "\n")


def _on_build_error(self, err):
    # err is QProcess.ProcessError
    self.append_log(f"\n[build] QProcess error: {err} (0=FailedToStart,1=Crashed,2=TimedOut,3=WriteError,4=ReadError,5=Unknown)\n")
    self.run_btn.setEnabled(True)
    # One last sync (in case the final lines arrived very late)
    self.set_last_output(self.last_output)

def show_error_for_item(self, item):
    info = item.text()
    try:
        path, line, col = self._parse_item(info)
        if self.cb_try_alt_ext.isChecked():
            path = resolve_alt_ext(path, self.path_in.text().strip())
        # open in embedded editor instead of VS Code
        self._editor_open_file(path, line, col)
        snippet = self._extract_errors_for_file(self.last_output, path, self.path_in.text().strip())
        self._replace_log(snippet if snippet else f"(No specific lines found for {path})\n\n{self.last_output}")
    except Exception:
        self.append_log("show_error_for_item error:\n" + traceback.format_exc() + "\n")

def init_vertical_split_creation(self,*widgets):
    stack_split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self)
    for widget in widgets:
        stack_split.addWidget(widget)     # your left panel QWidget
    # optional: make the bottom get most of the space
    stack_split.setStretchFactor(0, 0)
    stack_split.setStretchFactor(1, 1)
    # optional: allow collapsing the preview if the user drags it shut
    stack_split.setChildrenCollapsible(True)
    return stack_split
def init_horizontal_split(self,*widgets):
    content_split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self)
    for widget in widgets:
        content_split.addWidget(widget)     # your left panel QWidget
    content_split.setStretchFactor(0, 1)
    content_split.setStretchFactor(1, 2)
    return content_split
def init_text_editor_creation(self):
    right_panel = QWidget(); right_lay = QVBoxLayout(right_panel)
    editor_hdr = QHBoxLayout()
    editor_hdr.addWidget(QLabel("Editor:")); editor_hdr.addStretch(1)
    editor_hdr.addWidget(self.btn_revert); editor_hdr.addWidget(self.btn_save)
    right_lay.addLayout(editor_hdr)
    right_lay.addWidget(self.editor, 1)   # editor fills remaining space
    return right_panel
def init_view_row_create(self):
    view_row = QHBoxLayout()
    view_row.addWidget(QLabel("View:")); view_row.addStretch(1)
    view_row.addWidget(self.rb_all); view_row.addWidget(self.rb_err); view_row.addWidget(self.rb_wrn)
    view_row.addWidget(self.cb_try_alt_ext)
    return view_row
def init_top_row_create(self):
    top = QHBoxLayout()
    top.addWidget(QLabel("User:")); top.addWidget(self.user_in, 2)
    top.addWidget(QLabel("Path:")); top.addWidget(self.path_in, 3)
    top.addWidget(self.run_btn); top.addWidget(self.rerun_btn); top.addWidget(self.clear_btn)
    return top



def build_group_tree(self):
    """
    Create a grouped QTreeWidget. Population is done later by show_error_entries / show_warning_entries.
    """
    tree = QTreeWidget()
    tree.setColumnCount(2)
    tree.setHeaderLabels(["File / Issue", "Details"])
    tree.setUniformRowHeights(True)
    tree.setRootIsDecorated(True)
    # connect to the unified tree-item handler
    tree.itemClicked.connect(self.on_tree_item_clicked)
    return tree
