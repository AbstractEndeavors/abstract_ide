

from .functions import (_gather_map_text, _map_context_menu, append_log, copy_map, display_map, save_map_to_file, start_map, wire_map_copy_ui)

def initFuncs(self):
    try:
        for f in (_gather_map_text, _map_context_menu, append_log, copy_map, display_map, save_map_to_file, start_map, wire_map_copy_ui):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
