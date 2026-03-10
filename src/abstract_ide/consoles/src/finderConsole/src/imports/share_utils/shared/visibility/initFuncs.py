

from abstract_utilities import get_logFile
from .functions import (button, container, is_visible, register, set_visible)
logger=get_logFile(__name__)
def initFuncs(self):
    try:
        for f in (button, container, is_visible, register, set_visible):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
