

from .functions import (append_log, populate_results, start_collect)

def initFuncs(self):
    try:
        for f in (append_log, populate_results, start_collect):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
