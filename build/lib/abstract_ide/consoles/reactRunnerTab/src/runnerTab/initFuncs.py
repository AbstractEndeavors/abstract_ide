

from .functions import (_editor_clear_highlights, _editor_goto_and_mark, _editor_open_file, _editor_revert_current, _editor_save_current, _editor_show_ranges, _ensure_alt_ext, _extract_errors_for_file, _group_by_path_dict, _make_line_selection, _normalize_entries, _on_build_error, _on_build_finished, _on_build_output, _on_path_changed, _parse_item, _pick_build_cmd, _replace_log, _run_build_qprocess, _update_dict_preview, append_log, apply_log_filter, build_group_tree, clear_ui, create_radio_group, init_dict_panel_creation, init_horizontal_split, init_set_buttons, init_text_editor_creation, init_top_row_create, init_tree_creation, init_vertical_split_creation, init_view_row_create, initializeInit, on_tree_item_clicked, open_in_editor, resolve_alt_ext, set_last_output, setup_issue_tree, show_all_entries, show_error_entries, show_error_for_item, show_warning_entries, start_work, update_issues)

def initFuncs(self):
    try:
        for f in (_editor_clear_highlights, _editor_goto_and_mark, _editor_open_file, _editor_revert_current, _editor_save_current, _editor_show_ranges, _ensure_alt_ext, _extract_errors_for_file, _group_by_path_dict, _make_line_selection, _normalize_entries, _on_build_error, _on_build_finished, _on_build_output, _on_path_changed, _parse_item, _pick_build_cmd, _replace_log, _run_build_qprocess, _update_dict_preview, append_log, apply_log_filter, build_group_tree, clear_ui, create_radio_group, init_dict_panel_creation, init_horizontal_split, init_set_buttons, init_text_editor_creation, init_top_row_create, init_tree_creation, init_vertical_split_creation, init_view_row_create, initializeInit, on_tree_item_clicked, open_in_editor, resolve_alt_ext, set_last_output, setup_issue_tree, show_all_entries, show_error_entries, show_error_for_item, show_warning_entries, start_work, update_issues):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
