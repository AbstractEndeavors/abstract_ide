from PyQt6.QtWidgets import QTextEdit, QPlainTextEdit
from PyQt6.QtGui import QTextCharFormat, QTextCursor, QColor

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
