# abstract_x11/platform_utils.py
from ..src import *
def is_wayland() -> bool:
    plat = os.environ.get("QT_QPA_PLATFORM", "").lower()
    if not plat and os.environ.get("XDG_SESSION_TYPE") == "wayland":
        plat = "wayland"
    return plat.startswith("wayland")

def compute_self_ids(widget) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (pid, win_hex).
    win_hex is None on Wayland.
    """
    pid = str(os.getpid())
    win_hex = None

    if is_wayland():
        return pid, win_hex

    try:
        wid = int(widget.winId() or 0)
        if wid:
            win_hex = f"0x{wid:08x}"
    except Exception:
        pass

    return pid, win_hex
