

from .functions import *
def initFuncs(self):
    try:
        for f in ():
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
