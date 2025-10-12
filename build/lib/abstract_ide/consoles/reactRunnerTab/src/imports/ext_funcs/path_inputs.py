"""Robust, drop-in helpers for filesystem path inputs (Qt).

- Works with your `abstract_gui` wrapper, with graceful fallback to PyQt5/PySide6.
- Two entry points:
    - `make_path_input(...) -> QLineEdit`
    - `make_path_input_with_browse(...) -> QWidget` (composite: [QLineEdit | Browse…])
- Extras:
    - `require_package_json(path) -> (ok, msg)` validator
    - `set_project_path(line_edit, new_path, fire_handler=False, handler=None)` safe setter
    - `add_fs_completer(line_edit, root="/")` for filesystem autocompletion

Usage example (inside your class):

    from path_inputs import make_path_input, require_package_json, add_fs_completer

    def _on_path_changed(self, text: str):
        self.init_path = text

    self.path_in = make_path_input(
        init_value=getattr(self, "init_path", ""),
        on_change=self._on_path_changed,
        user_only=True,
        parent=self,
        placeholder="Project path (folder with package.json)",
        validate=require_package_json,
    )
    add_fs_completer(self.path_in)
    self.layout().addWidget(self.path_in)

"""
from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional, Tuple

# --- Qt imports: prefer your wrapper, gracefully fall back ---
try:  # your wrapper (preferred)
    from abstract_gui import *  # noqa: F401,F403
except Exception:
    # Lightweight fallback so this module still works in isolation
    try:
        from PyQt5.QtCore import Qt, QSignalBlocker
        from PyQt5.QtGui import QPalette, QColor
        from PyQt5.QtWidgets import (
            QWidget, QLineEdit, QPushButton, QHBoxLayout, QFileDialog,
            QApplication, QCompleter, QFileSystemModel,
        )
    except Exception:  # PySide6 fallback
        from PySide6.QtCore import Qt, QSignalBlocker
        from PySide6.QtGui import QPalette, QColor
        from PySide6.QtWidgets import (
            QWidget, QLineEdit, QPushButton, QHBoxLayout, QFileDialog,
            QApplication, QCompleter, QFileSystemModel,
        )

__all__ = [
    "make_path_input",
    "make_path_input_with_browse",
    "require_package_json",
    "set_project_path",
    "add_fs_completer",
]

def _on_path_changed(self, new_text: str):
    self.init_path = new_text.strip()
def _apply_validation_feedback(line_edit: QLineEdit, ok: bool, msg: Optional[str]) -> None:
    """Minimal visual feedback: tooltip + base color tweak. Non-destructive."""
    try:
        line_edit.setToolTip("" if ok else (msg or "Invalid path"))
        pal = line_edit.palette()
        base = QApplication.palette().base().color()
        warn = QColor(255, 240, 240)
        pal.setColor(QPalette.Base, base if ok else warn)
        line_edit.setPalette(pal)
    except Exception:
        # Fallback to stylesheet if palette APIs differ
        if ok:
            line_edit.setStyleSheet("")
            line_edit.setToolTip("")
        else:
            line_edit.setStyleSheet("QLineEdit{background:#FFF0F0}")
            line_edit.setToolTip(msg or "Invalid path")


def make_path_input(
    init_value: str = "",
    on_change: Optional[Callable[[str], None]] = None,
    user_only: bool = True,  # True => textEdited; False => textChanged
    parent: Optional[QWidget] = None,
    placeholder: str = "Project path (folder with package.json)",
    validate: Optional[Callable[[str], Tuple[bool, Optional[str]]]] = None,
) -> QLineEdit:
    """
    Create a path QLineEdit with optional validation and change callback.

    Args:
        init_value: initial text
        on_change: called with normalized text whenever it changes
        user_only: if True, connect textEdited (user typing only). If False, textChanged
        parent: QWidget parent
        placeholder: placeholder text
        validate: callable(text) -> (ok, message). If provided, UI shows feedback

    Returns:
        QLineEdit
    """
    le = QLineEdit(parent)
    if init_value:
        le.setText(init_value)
    le.setPlaceholderText(placeholder)

    signal = le.textEdited if user_only else le.textChanged

    if on_change is not None or validate is not None:
        def _slot(text: str) -> None:
            text = text.strip()
            if validate is not None:
                ok, msg = validate(text)
                _apply_validation_feedback(le, ok, msg)
            if on_change is not None:
                on_change(text)
        signal.connect(_slot)

    return le


def make_path_input_with_browse(
    init_value: str = "",
    on_change: Optional[Callable[[str], None]] = None,
    user_only: bool = True,
    parent: Optional[QWidget] = None,
    placeholder: str = "Project path (folder with package.json)",
    validate: Optional[Callable[[str], Tuple[bool, Optional[str]]]] = None,
) -> QWidget:
    """Composite widget: [ QLineEdit | Browse… ] with same behavior as make_path_input."""
    w = QWidget(parent)
    layout = QHBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)

    le = make_path_input(init_value, on_change, user_only, w, placeholder, validate)
    btn = QPushButton("Browse…", w)

    def _browse() -> None:
        start = le.text() or str(Path.home())
        d = QFileDialog.getExistingDirectory(w, "Select Project Directory", start)
        if d:
            d = str(Path(d).expanduser())
            if user_only:
                # textEdited won’t fire for setText; call handler manually if provided
                try:
                    blocker = QSignalBlocker(le)
                    le.setText(d)
                finally:
                    del blocker
                if on_change:
                    on_change(d)
            else:
                # textChanged will emit and hit the handler
                le.setText(d)

    btn.clicked.connect(_browse)
    layout.addWidget(le, 1)
    layout.addWidget(btn, 0)

    # expose the line edit handle for callers
    w.line_edit = le  # type: ignore[attr-defined]
    return w


def require_package_json(path_str: str) -> Tuple[bool, Optional[str]]:
    """Validator: path must be an existing directory containing package.json."""
    p = Path(path_str).expanduser()
    if not p.exists():
        return False, "Path does not exist"
    if not p.is_dir():
        return False, "Not a directory"
    if not (p / "package.json").exists():
        return False, "package.json not found in directory"
    return True, None


def set_project_path(
    line_edit: QLineEdit,
    new_path: str,
    *,
    fire_handler: bool = False,
    handler: Optional[Callable[[str], None]] = None,
) -> None:
    """Programmatically set the path safely.

    If the widget is connected via textEdited (user_only=True), programmatic setText
    does not emit; use fire_handler=True or call your handler manually.
    """
    new_path = str(Path(new_path).expanduser())
    try:
        blocker = QSignalBlocker(line_edit)
        line_edit.setText(new_path)
    finally:
        try:
            del blocker
        except Exception:
            pass
    if fire_handler and handler is not None:
        handler(new_path)


def add_fs_completer(
    line_edit: QLineEdit,
    root: str = "/",
    *,
    case_insensitive: bool = True,
    contains_match: bool = False,
) -> QCompleter:
    """Attach a filesystem completer to the line edit and return it (Qt5/Qt6 safe)."""
    model = QFileSystemModel(line_edit)
    model.setRootPath(root)
    comp = QCompleter(model, line_edit)

    # --- Qt5/Qt6 enum compatibility ---
    # Case sensitivity
    try:
        # Qt6 style: Qt.CaseSensitivity.CaseInsensitive
        CS = Qt.CaseSensitivity  # type: ignore[attr-defined]
        CASE_INS = CS.CaseInsensitive
        CASE_SENS = CS.CaseSensitive
    except AttributeError:
        # Qt5 style: Qt.CaseInsensitive, Qt.CaseSensitive
        CASE_INS = getattr(Qt, "CaseInsensitive", 0)
        CASE_SENS = getattr(Qt, "CaseSensitive", 1)

    comp.setCaseSensitivity(CASE_INS if case_insensitive else CASE_SENS)

    # Match mode (only applied when requested)
    if contains_match:
        try:
            MF = Qt.MatchFlag  # Qt6
            match_contains = MF.MatchContains
        except AttributeError:
            match_contains = getattr(Qt, "MatchContains", 0)  # Qt5
        comp.setFilterMode(match_contains)

    line_edit.setCompleter(comp)
    return comp

