

from .functions import (display_map,append_log,start_map,_map_context_menu,save_map_to_file,copy_map,wire_map_copy_ui)


def initFuncs(self):
    try:
        for f in (display_map,append_log,start_map,_map_context_menu,save_map_to_file,copy_map,wire_map_copy_ui):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
