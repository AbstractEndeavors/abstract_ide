

from .functions import (_add_file_row, _ask_user_to_pick_file, _clear_files_tree, _collect_checked_files, _fill_files_tree, _first_overwrite_checked, _gather_checked, _get_first_apply_checked_from_tree, _get_selected_path_from_list, _get_selected_path_from_tree, _iter_tree_rows, _on_tree_selection_changed, _open_file_from_row, _pick_preview_target, _preview_for_path, _selected_tree_row_flags, append_log, apply_diff_to_directory, get_all_files, get_all_subs, get_files, get_hunks, get_nufiles, get_test_diff, output_test, preview_patch, save_all_checked, save_patch)

def initFuncs(self):
    try:
        for f in (_add_file_row, _ask_user_to_pick_file, _clear_files_tree, _collect_checked_files, _fill_files_tree, _first_overwrite_checked, _gather_checked, _get_first_apply_checked_from_tree, _get_selected_path_from_list, _get_selected_path_from_tree, _iter_tree_rows, _on_tree_selection_changed, _open_file_from_row, _pick_preview_target, _preview_for_path, _selected_tree_row_flags, append_log, apply_diff_to_directory, get_all_files, get_all_subs, get_files, get_hunks, get_nufiles, get_test_diff, output_test, preview_patch, save_all_checked, save_patch):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
