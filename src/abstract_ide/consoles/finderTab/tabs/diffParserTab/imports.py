from ..imports import *
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Union, Set
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QTreeWidgetItem
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtCore import Qt
import os
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)
from ..imports import *  # your app-wide helpers: install_common_inputs, make_params, get_files_and_dirs, etc.

import os, re, logging
from dataclasses import dataclass, field
from typing import Any, List, Dict, Tuple

logger = logging.getLogger(__name__)
##
# ───────────────────────── Models ─────────────────────────

@dataclass
class Hunk:
    subs: List[str] = field(default_factory=list)             # lines to match (no '-')
    adds: List[str] = field(default_factory=list)             # lines to insert (no '+')
    content: List[Dict[str, Any]] = field(default_factory=list)

    def is_multiline(self) -> bool:
        return len(self.subs) > 1 or len(self.adds) > 1

@dataclass
class ApplyReport:
    changed_files: List[str] = field(default_factory=list)
    skipped_files: List[str]  = field(default_factory=list)
    hunks_applied: int        = 0
    hunks_skipped: int        = 0

    def extend_changed(self, path: str): 
        if path not in self.changed_files: self.changed_files.append(path)

    def extend_skipped(self, path: str): 
        if path not in self.skipped_files: self.skipped_files.append(path)

# ───────────────────── Status helper ──────────────────────

def set_status(self, text: str, kind: str = "info"):
    colors = {
        "info":  "#2196f3",
        "ok":    "#4caf50",
        "warn":  "#ff9800",
        "error": "#f44336",
    }
    self.status_label.setText(text)
    self.status_label.setStyleSheet(f"color: {colors.get(kind,'#2196f3')}; padding: 4px 0;")

# ─────────────────────── File I/O ─────────────────────────

def read_any_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def write_to_file(data: str, file_path: str):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data)

# ─────────────────────── Utilities ─────────────────────────

def make_list(strings: Any) -> List[str]:
    if isinstance(strings, list): return strings
    return [strings]

def getPaths(files: List[str], strings: List[str] | str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Find files and positions where the contiguous block `strings` matches exactly.
    Returns (unique_files, found_paths). Each found_paths item:
      {'file_path': str, 'lines': [{'line': int, 'content': str}, ...]}
    """
    strings_list = make_list(strings)
    tot = "\n".join(strings_list) if len(strings_list) > 1 else (strings_list[0] if strings_list else "")
    if not tot: 
        return [], []

    found_paths: List[Dict[str, Any]] = []
    uniq = set()
    for fp in files:
        try:
            txt = read_any_file(fp)
            if tot not in txt: 
                continue
            uniq.add(fp)
            lines = txt.split("\n")
            for m in re.finditer(re.escape(tot), txt):
                start_byte = m.start()
                start_line = txt[:start_byte].count("\n")
                block = []
                ok = True
                for j in range(len(strings_list)):
                    ln = start_line + j
                    if ln >= len(lines): ok = False; break
                    block.append({"line": ln, "content": lines[ln]})
                if ok:
                    found_paths.append({"file_path": fp, "lines": block})
        except Exception as e:
            logger.error(f"Error in getPaths for {fp}: {e}")
    return sorted(uniq), found_paths

# ───────────────────── Diff parsing ───────────────────────

_HUNK_HEADER = re.compile(r'^@@\s*-?\d+(?:,\d+)?\s+\+?\d+(?:,\d+)?\s*@@')

def _is_header_line(s: str) -> bool:
    return (
        s.startswith("diff --git ") or
        s.startswith("index ") or
        s.startswith("--- ") or
        s.startswith("+++ ")
    )

def parse_unified_diff(diff_text: str) -> List[Hunk]:
    """Tolerant unified diff parser (works with or without @@ headers)."""
    lines = diff_text.splitlines()
    hunks: List[Hunk] = []
    current: Hunk | None = None
    in_hunk = False

    def flush():
        nonlocal current, in_hunk
        if current and (current.subs or current.adds):
            hunks.append(current)
        current, in_hunk = None, False

    for raw in lines:
        line = raw.rstrip("\r")

        if _HUNK_HEADER.match(line):
            flush()
            current = Hunk()
            in_hunk = True
            continue

        if not in_hunk:
            if _is_header_line(line) or not line.strip():
                continue
            if line.startswith((" ", "+", "-")):
                current = current or Hunk()
                in_hunk = True
            else:
                continue

        if line.startswith(" "):
            content = line[1:]
            current.subs.append(content)
            current.adds.append(content)
        elif line.startswith("-"):
            current.subs.append(line[1:])
        elif line.startswith("+"):
            current.adds.append(line[1:])
        elif line == r"\ No newline at end of file":
            continue
        else:
            flush()

    flush()
    logger.debug("parse_unified_diff -> %d hunks", len(hunks))
    return hunks
