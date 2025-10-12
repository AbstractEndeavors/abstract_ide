

from .functions import (_guess_cwd, _on_new_buffer, _on_open_file, _on_run_code, _on_run_selection, _on_save_file_as)

def initFuncs(self):
    try:
        for f in (_guess_cwd, _on_new_buffer, _on_open_file, _on_run_code, _on_run_selection, _on_save_file_as):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
