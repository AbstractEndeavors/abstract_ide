

from .functions import (_add_fn_button, _add_var_button, _build_ui, _clear_fn_buttons, _clear_var_buttons, _filter_fn_buttons, _filter_var_buttons, _on_filter_mode_changed, _on_fn_filter_mode_changed, _on_function_clicked, _on_map_ready, _on_symbol_clicked, _on_var_filter_mode_changed, _on_variable_clicked, _rebuild_fn_buttons, _rebuild_var_buttons, _render_fn_lists_for, _render_symbol_lists_for, _render_var_lists_for, _start_func_scan, appendLog, append_log, create_radio_group, expandingDirections, get_tabs_attr, init_functions_button_tab, init_variables_button_tab)

def initFuncs(self):
    try:
        for f in (_add_fn_button, _add_var_button, _build_ui, _clear_fn_buttons, _clear_var_buttons, _filter_fn_buttons, _filter_var_buttons, _on_filter_mode_changed, _on_fn_filter_mode_changed, _on_function_clicked, _on_map_ready, _on_symbol_clicked, _on_var_filter_mode_changed, _on_variable_clicked, _rebuild_fn_buttons, _rebuild_var_buttons, _render_fn_lists_for, _render_symbol_lists_for, _render_var_lists_for, _start_func_scan, appendLog, append_log, create_radio_group, expandingDirections, get_tabs_attr, init_functions_button_tab, init_variables_button_tab):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
