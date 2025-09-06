

from .functions import (_toggle_pause,)

def initFuncs(self):
    try:
        for f in (_toggle_pause,):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
