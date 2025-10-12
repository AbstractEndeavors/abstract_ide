

from .functions import (_build_ui, _compute_self_ids, _selected_rows, activate_window, close_selected, control_window, get_monitors, get_self, get_windows, is_self, move_window, open_file, refresh, run_command, select_all_by_type, should_close, update_monitor_dropdown, update_table)

def initFuncs(self):
    try:
        for f in (_build_ui, _compute_self_ids, _selected_rows, activate_window, close_selected, control_window, get_monitors, get_self, get_windows, is_self, move_window, open_file, refresh, run_command, select_all_by_type, should_close, update_monitor_dropdown, update_table):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
