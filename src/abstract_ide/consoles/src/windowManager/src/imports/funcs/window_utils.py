# abstract_x11/window_utils.py
from ..src import *
from .monitor_utils import *
from .selection_utils import *
from .platform_utils import *
from .selection_utils import *
def classify_type(title: str) -> str:
    """Stub — replace with your real classification logic."""
    title = title.lower()
    if "terminal" in title:
        return "Terminal"
    if "code" in title:
        return "Editor"
    return "Window"

def get_windows(run_cmd, self_pid=None, self_win_hex=None) \
        -> List[Tuple[str, str, str, str, str, bool]]:
    """
    Returns [(id, pid, title, monitor, type, has_selection)]
    """
    windows = []

    mons = get_monitors(run_cmd)
    primary_owner = detect_primary_owner(run_cmd)

    out = run_cmd("wmctrl -l -p -G")

    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 8:
            continue

        win_id, desktop, pid, x, y, w, h = parts[:7]
        title = " ".join(parts[8:])

        # Skip self window
        if self_pid and pid == self_pid:
            continue
        if self_win_hex and win_id.lower() == self_win_hex.lower():
            continue

        x, y = int(x), int(y)

        # Determine monitor
        monitor_name = "Unknown"
        for name, mx, my, mw, mh in mons:
            if mx <= x < mx + mw and my <= y < my + mh:
                monitor_name = name
                break

        win_type = classify_type(title)
        has_selection = (win_id.lower() == primary_owner)

        windows.append((win_id, pid, title, monitor_name, win_type, has_selection))

    return windows
