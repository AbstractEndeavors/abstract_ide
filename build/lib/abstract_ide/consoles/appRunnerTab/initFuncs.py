

from .functions import (_on_run_selection,_on_run_code,_on_save_file_as,_on_open_file,_on_new_buffer,_guess_cwd,_write_temp_script)


def initFuncs(self):
    try:
        for f in (_on_run_selection,_on_run_code,_on_save_file_as,_on_open_file,_on_new_buffer,_guess_cwd,_write_temp_script):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
