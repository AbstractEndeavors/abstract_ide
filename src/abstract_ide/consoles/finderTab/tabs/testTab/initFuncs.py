

from .functions import (start_search,)

def initFuncs(self):
    try:
        for f in (start_search,):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
