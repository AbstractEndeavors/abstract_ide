# ─── Third-party ──────────────────────────────────────────────────────────────
from .imports import *
logger = get_logFile('clipit_logs')
def copy_to_clipboard(text=None):
    clipboard.copy(text)

def log_it(self, message: str):
    """Append a line to the shared log widget, with timestamp."""
    timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
    logger.info(f"[{timestamp}] {message}")
    self.log_widget.append(f"[{timestamp}] {message}")
    
def _log(self, m: str):
    """Helper to write to both QTextEdit and Python logger."""
    logger.debug(m)
    log_it(self, m)

def _clear_layout(layout: QtWidgets.QLayout):
    """Recursively delete all widgets in a layout (Qt-safe)."""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().setParent(None)      # detach
            item.widget().deleteLater()        # mark for deletion
        elif item.layout():
            _clear_layout(item.layout())
def unlist(obj):
    if obj and isinstance(obj, list):
        obj = obj[0]
    return obj
def get_all_dir_pieces(file_paths: List[str]) -> List[str]:
    """Extract unique directory components, excluding root-like components."""
    all_pieces = set()
    for file_path in file_paths:
        path = Path(file_path)
        for parent in path.parents:
            name = parent.name
            if name:
                all_pieces.add(name)
    return sorted(list(all_pieces))
def is_string_in_dir(path,strings):
    dirname =  path
    if os.path.isfile(path):
        dirname = os.path.dirname(path)
    pieces = [pa for pa in dirname.split('/') if pa and pa in strings]
    logger.info(f"pieces = {pieces}\nstrings == {strings}")
    if pieces:
        return True
    return False
def is_in_exts(path,exts,visible_dirs):
    logger.info(f"path = {path}\nexts == {exts}")
    if is_string_in_dir(path,visible_dirs):
        return True
    if os.path.isdir(path):
        return True
    ext = os.path.splitext(path)[1].lower()
    if ext in exts:
        return True
    return 
