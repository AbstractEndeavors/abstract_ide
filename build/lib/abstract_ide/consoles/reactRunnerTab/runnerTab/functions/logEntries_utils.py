from ...imports import *
import logging
from abstract_react import *
from abstract_utilities import *

from abstract_apis import *
MAIN_DIR = os.getcwd()

 

# One place to define field names (override per-call if you ever change schema)
DEFAULT_KEYS = dict(path='path', line='line', col='col', msg='msg', code='code')
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
