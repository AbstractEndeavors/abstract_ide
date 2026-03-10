# abstract_x11/selection_utils.py

from ..src import *
from .platform_utils import *
def clear_primary_selection(status_bar=None) -> None:
    """Clears PRIMARY selection on X11."""
    if is_wayland():
        if status_bar:
            status_bar.showMessage("Cannot clear selection on Wayland", 3000)
        return

    cb = QGuiApplication.clipboard()
    try:
        cb.setText("", QClipboard.Mode.Selection)
        if status_bar:
            status_bar.showMessage("Highlight cleared", 2000)
    except Exception as e:
        if status_bar:
            status_bar.showMessage(f"Error clearing selection: {e}", 3000)

def detect_primary_owner(run_cmd) -> Optional[str]:
    """
    Returns hex window id like '0x3c00007'.
    """
    try:
        out = run_cmd("xprop -root | grep PRIMARY_SELECTION")
    except Exception:
        return None

    m = re.search(r"window id # (0x[0-9a-fA-F]+)", out)
    return m.group(1).lower() if m else None
