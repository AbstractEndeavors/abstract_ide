# windowManagerTab/functions/wmctrl_utils.py
"""
This module becomes ONLY a convenience wrapper around the modular subsystem.
No more duplicate logic inside this file.
"""
from .imports import *



# -------------------------
# BOUND METHODS FOR CLASS
# -------------------------

def wm_compute_self_ids(self):
    """Compute PID + window ID via modular platform utils."""
    pid, win_hex = compute_self_ids(self)
    self._self_pid = pid
    self._self_win_hex = win_hex


def wm_refresh_windows(self):
    """Update the cached window list using modular utilities."""
    self.windows = get_windows(
        run_cmd=self.run_command,
        self_pid=self._self_pid,
        self_win_hex=self._self_win_hex
    )
    return self.windows


def wm_refresh_monitors(self):
    """Retrieve monitor geometry list."""
    self.monitors = get_monitors(self.run_command)
    return self.monitors


def wm_clear_highlights(self):
    """Wrap the modular clear_primary_selection with UI feedback."""
    clear_primary_selection(self.statusBar())
