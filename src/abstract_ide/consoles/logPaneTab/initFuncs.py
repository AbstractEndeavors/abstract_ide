

from .functions import (append_line,)

def initFuncs(self):
    try:
        for f in (append_line,):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
