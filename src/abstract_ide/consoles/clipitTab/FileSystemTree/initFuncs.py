from .imports import *
from .functions import (_log, copy_selected)
def initFuncs(self):
    try:
        for f in (_log, copy_selected):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
