

from .functions import (_log, _toggle_logs, _toggle_view, copy_raw, on_file_selected, on_function_selected, on_tree_copy, on_tree_double_click)

def initFuncs(self):
    try:
        for f in (_log, _toggle_logs, _toggle_view, copy_raw, on_file_selected, on_function_selected, on_tree_copy, on_tree_double_click):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
