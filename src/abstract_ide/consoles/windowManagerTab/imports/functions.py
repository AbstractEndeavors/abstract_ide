# -----------------------------------------------------------------------------
#  helper heuristics -----------------------------------------------------------
# -----------------------------------------------------------------------------
from typing import *
def classify_type(title: str) -> str:
    t = title.lower()
    if any(b in t for b in ("chrome", "firefox", "edge", "safari")):
        return "Browser"
    if any(e in t for e in ("code", "sublime", "pycharm", "notepad", "vim")):
        return "Editor"
    if any(term in t for term in ("terminal", "xterm", "cmd", "powershell")):
        return "Terminal"
    return "Other"


def looks_unsaved(title: str) -> bool:
    return (
        any(mark in title for mark in ("*", "●", "•"))
        or title.lower().startswith("untitled")
    )

