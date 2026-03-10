texts= '''from ..imports import *
import tempfile, os, sys
def _on_run(self):
    cmd = self.cmd_edit.text().strip()
    if not cmd:
        QtWidgets.QMessageBox.warning(self, "No command", "Please enter a command to run.")
        return
    # Example: bias environment for Python targets
    env = {"PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1"}
    self.runner.start(cmd, cwd=None, env=env)
def _set_mono_font(self,widget: QtWidgets.QPlainTextEdit):
    font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
    font.setPointSize(11)
    widget.setFont(font)

def _write_temp_script(text: str) -> str:
    # Keep file to allow re-runs; user can inspect tmp if wanted
    fd, path = tempfile.mkstemp(prefix="abstract_ide_", suffix=".py")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def _guess_cwd(self) -> str | None:
    # Prefer directory of current file if any
    if getattr(self, "_current_path", None):
        return os.path.dirname(self._current_path)
    # Else, fall back to project-ish cwd if your app tracks one
    return None

# ---- UI actions bound via initFuncs -----------------------------------------

def _on_new_buffer(self):
    self._current_path = None
    self.editor.setPlainText("# New buffer\nprint('Hello from Abstract IDE')\n")
    self.statusBar().showMessage("New buffer", 2000)

def _on_open_file(self):
    path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Python file", "", "Python (*.py);;All (*)")
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            self.editor.setPlainText(f.read())
        self._current_path = path
        self.statusBar().showMessage(f"Opened {path}", 3000)
    except Exception as e:
        QtWidgets.QMessageBox.critical(self, "Open failed", str(e))

def _on_save_file_as(self):
    path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save As", self._current_path or "", "Python (*.py);;All (*)")
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.editor.toPlainText())
        self._current_path = path
        self.statusBar().showMessage(f"Saved {path}", 3000)
    except Exception as e:
        QtWidgets.QMessageBox.critical(self, "Save failed", str(e))

def _on_run_code(self):
    code_text = self.editor.toPlainText()
    if not code_text.strip():
        QtWidgets.QMessageBox.information(self, "Nothing to run", "The editor is empty.")
        return
    # Save to a tmp script (don’t overwrite user file unless they Save As)
    script_path = _write_temp_script(code_text)
    env = {"PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1"}
    py = sys.executable or "python3"
    cmd = f"{py} -u {shlex.quote(script_path)}"
    self.runner.start(cmd, cwd=_guess_cwd(self), env=env)

def _on_run_selection(self):
    cursor = self.editor.textCursor()
    selected = cursor.selectedText().replace('\u2029', '\n')  # QTextEdit selection line sep → newline
    if not selected.strip():
        QtWidgets.QMessageBox.information(self, "No selection", "Select some code and try again.")
        return
    script_path = _write_temp_script(selected)
    env = {"PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1"}
    py = sys.executable or "python3"
    cmd = f"{py} -u {shlex.quote(script_path)}"
    self.runner.start(cmd, cwd=_guess_cwd(self), env=env)

'''
# --- Indent ratio tracker & normalizer ---
# Keeps your abstract_utilities, but note you could use: line.lstrip(" \t")
from abstract_utilities import *  # noqa

TABSTOP_DEFAULT = 4  # can be auto-inferred below

def leading_ws(s: str) -> str:
    """Return the leading whitespace prefix (spaces/tabs)."""
    i = 0
    lens = len(s) if isinstance(s,str) else s
    while i < lens and s[i] in (" ", "\t"):
        i += 1
    return s[:i]

def measure_indent(ws: str, tabstop: int) -> int:
    """
    Convert leading whitespace to a numeric indent level in 'spaces'.
    For leading region starting at col 0, treating each '\t' as tabstop is fine.
    """
    cols = 0
    for ch in ws:
        if ch == "\t":
            cols += tabstop
        else:
            cols += 1
    return cols

def infer_unit(levels: list[int]) -> int:
    """
    Try to infer a minimal indent unit (like 2 or 4 spaces).
    Falls back to TABSTOP_DEFAULT when uncertain.
    """
    import math
    diffs = [abs(b - a) for a, b in zip(levels, levels[1:]) if b != a]
    diffs = [d for d in diffs if d > 0]
    if not diffs:
        return TABSTOP_DEFAULT
    g = diffs[0]
    for d in diffs[1:]:
        g = math.gcd(g, d)
        if g == 1:
            break
    # clamp to a reasonable range
    return g if 1 <= g <= 8 else TABSTOP_DEFAULT

class IndentManager:
    def __init__(self, tabstop: int | None = None):
        self.tabstop = tabstop or TABSTOP_DEFAULT
        self.rows: list[dict] = []
        self._levels: list[int] = []
        
    def feed_line(self, raw_line: str) -> dict:
        ws = leading_ws(raw_line)
        # you used eatAll(..., [' ','\n','\t']); stdlib alt: raw_line.lstrip(" \n\t")
        line = eatAll(raw_line, [' ', '\n', '\t'])
        lvl_spaces = measure_indent(ws, self.tabstop)
        self._levels.append(lvl_spaces)

        if len(self._levels) == 1:
            delta = 0
        else:
            delta = self._levels[-1] - self._levels[-2]

        dirn = 0 if delta == 0 else (1 if delta > 0 else -1)
        row = {"ws": ws, "line": line, "level_spaces": lvl_spaces, "delta": delta, "dir": dirn}
        self.rows.append(row)
        return row

    def finalize(self):
        # If tabstop wasn't provided, we can refine “unit” for display output.
        unit = infer_unit([r["level_spaces"] for r in self.rows])
        return unit

def retab(rows: list[dict], unit: int, use_tabs: bool = True) -> list[str]:
    """
    Make a normalized re-indented version of the text.
    If use_tabs=True, each unit is a '\t'; else we emit spaces.
    """
    out = []
    for r in rows:
        lvl_units = 0 if unit == 0 else r["level_spaces"] // max(unit, 1)
        prefix = ("\t" * lvl_units) if use_tabs else (" " * (lvl_units * unit))
        out.append(prefix + r["line"])
    return out

# ---- Example driver over `texts` ----
def compute_indent_ratios(texts: str, tabstop: int | None = None, reindent: bool = False):
    mgr = IndentManager(tabstop=tabstop)
    lines = []
    for raw in texts.splitlines():
        mgr.feed_line(raw)
        lines.append(eatAll(raw,[' ','\n','\t']))

    unit = mgr.finalize()

    # Your “ratio” stream (±1/0 per line) and cumulative ratio if you want similar behavior
    directions = [r["dir"] for r in mgr.rows]
    deltas = [r["delta"] for r in mgr.rows]
    levels = [r["level_spaces"] for r in mgr.rows]

    # Rebuild with normalized tabs (or spaces) if desired
    rebuilt = retab(mgr.rows, unit=unit, use_tabs=True) if reindent else None

    return {
        "unit": unit,
        "levels": levels,
        "deltas": deltas,
        "directions": directions,
        "rebuilt": rebuilt,
        "lines":lines
    }
def get_spec_result(result,i):
    starting_indent = result['directions'][i]
    total_dir = 0
    result['lines'][i+1]+= '\ntry:\n'+result['lines'][i]
    for j,indent in enumerate(result['directions'][i+1:]):
        total_dir += indent
        result['lines'][j+i+1] ='\t'+result['lines'][j+i+1]
        if total_dir == 0:
            result['lines'][j+i+1] +='\nexcept Exception as e:\n\tprint(f"{e}")\n'
            
            
            return

def measure_indent(ws: str, tabstop: int = TABSTOP_DEFAULT) -> int:
    cols = 0
    for ch in ws:
        cols += tabstop if ch == "\t" else 1
    return cols

def compute_levels(lines: list[str], tabstop: int = TABSTOP_DEFAULT):
    """Return (raw_cols, logical_cols, stripped) for block detection only."""
    raw = []
    stripped = []
    for s in lines:
        ws = leading_ws(s)
        raw.append(measure_indent(ws, tabstop))
        stripped.append(eatAll(s, [' ', '\t', '\n']))
    logical = raw[:]
    last = 0
    for i, (lvl, txt) in enumerate(zip(raw, stripped)):
        if txt == "" or txt.lstrip().startswith("#"):
            logical[i] = last
        else:
            last = lvl
    return raw, logical, stripped

def body_span_after_header(i: int, logical: list[int], stripped: list[str]) -> tuple[int, int] | None:
    """Return (body_start, body_end_exclusive) for a header line i, else None."""
    base = logical[i]
    n = len(logical)
    j = i + 1
    # skip empty lines right after header
    while j < n and stripped[j] == "":
        j += 1
    if j >= n:
        return None
    if logical[j] <= base:
        return None  # one-liner like 'def f(): pass'
    body_start = j
    j += 1
    while j < n:
        if stripped[j] != "" and logical[j] <= base:
            break
        j += 1
    return (body_start, j)

def delta_ws(parent_ws: str, child_ws: str, tabstop: int = TABSTOP_DEFAULT) -> str:
    """
    Compute the literal whitespace suffix that takes parent_ws -> child_ws.
    If child_ws startswith parent_ws, return the exact suffix.
    Else, fall back to best-effort (match child's dominant char).
    """
    if child_ws.startswith(parent_ws):
        return child_ws[len(parent_ws):]

    # Fallback: synthesize suffix matching the column delta
    parent_c = measure_indent(parent_ws, tabstop)
    child_c  = measure_indent(child_ws, tabstop)
    d = max(child_c - parent_c, 0)
    # Heuristic: if child contains tabs, prefer a single tab; else spaces
    return ("\t" if "\t" in child_ws else " ") * (1 if "\t" in child_ws and d >= tabstop else d or tabstop)

def add_try_except_preserving_ws(texts: str,
                                 tabstop: int | None = None,
                                 except_body: str = 'print(f"{e}")') -> str:
    """
    Wrap each def-body with:
        try:
            <original body>
        except Exception as e:
            print(f"{e}")
    while preserving existing indentation characters.
    """
    tabstop = tabstop or TABSTOP_DEFAULT
    lines = texts.splitlines()

    raw, logical, stripped = compute_levels(lines, tabstop)

    i = 0
    while i < len(lines):
        txt = stripped[i]
        # treat only proper block headers; leave async def similarly if you wish: (txt.startswith("async def ") and txt.rstrip().endswith(":"))
        if txt.startswith("def ") and txt.rstrip().endswith(":"):
            span = body_span_after_header(i, logical, stripped)
            if not span:
                i += 1
                continue

            body_start, body_end = span
            header_ws = leading_ws(lines[i])
            first_body_ws = leading_ws(lines[body_start])
            step_ws = delta_ws(header_ws, first_body_ws, tabstop)

            # 1) insert 'try:' at the body_start, with same ws as first body line
            try_line = f"{first_body_ws}try:"
            lines.insert(body_start, try_line)
            stripped.insert(body_start, "try:")
            new_logical = measure_indent(first_body_ws, tabstop)
            logical.insert(body_start, new_logical)
            raw.insert(body_start, new_logical)

            # 2) shift original body lines by literally prefixing step_ws
            #    Note: original body now begins at body_start+1; end index moves by +1
            for k in range(body_start + 1, body_end + 1):
                lines[k] = step_ws + lines[k]
                # Update tracking (only needed if more edits later in the pass)
                raw[k] += measure_indent(step_ws, tabstop)
                logical[k] += measure_indent(step_ws, tabstop)
                stripped[k] = eatAll(lines[k], [' ', '\t', '\n'])

            # 3) insert except at the end of this (shifted) body
            body_end += 1  # account for inserted 'try:'
            except_hdr  = f"{first_body_ws}except Exception as e:"
            except_line = f"{first_body_ws}{step_ws}{except_body}"
            lines.insert(body_end, except_hdr)
            stripped.insert(body_end, "except Exception as e:")
            val = measure_indent(first_body_ws, tabstop)
            logical.insert(body_end, val)
            raw.insert(body_end, val)

            lines.insert(body_end + 1, except_line)
            stripped.insert(body_end + 1, except_body)
            val2 = measure_indent(first_body_ws + step_ws, tabstop)
            logical.insert(body_end + 1, val2)
            raw.insert(body_end + 1, val2)

            # jump past what we just inserted
            i = body_end + 2
        else:
            i += 1

    return "\n".join(lines)

# --- usage on your `texts` ---
# new_text = add_try_except_to_defs(texts, tabstop=None, use_tabs=True)
# print(new_text)
input(add_try_except_preserving_ws(texts, tabstop=4))
