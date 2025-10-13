
from ..imports import *
from .functions import (on_python_file_clicked,on_function_clicked,copy_raw,_apply_ext_filter, _clear_layout, _extract_imports, _log, _parse_functions, _populate_list_view, _populate_text_view, _rebuild_dir_row, _rebuild_ext_row, _toggle_populate_text_view, _update_dir_patterns, browse_files, dragEnterEvent, dropEvent, filter_paths, get_contents_text, map_function_dependencies, map_import_chain, on_function_clicked, on_file_clicked, populate_file_view, process_files)

def initFuncs(self):
    try:
        for f in (on_python_file_clicked,on_function_clicked,copy_raw,_apply_ext_filter, _clear_layout, _extract_imports, _log, _parse_functions, _populate_list_view, _populate_text_view, _rebuild_dir_row, _rebuild_ext_row, _toggle_populate_text_view, _update_dir_patterns, browse_files, dragEnterEvent, dropEvent, filter_paths, get_contents_text, map_function_dependencies, map_import_chain, on_function_clicked, on_file_clicked, populate_file_view, process_files):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
