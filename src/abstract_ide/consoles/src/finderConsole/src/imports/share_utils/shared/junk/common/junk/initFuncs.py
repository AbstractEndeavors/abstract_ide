

from abstract_utilities import get_logFile
from .functions import (_open_result, _refresh_results, init_results_ui)
logger=get_logFile(__name__)
def initFuncs(self):
    try:
        for f in (_open_result, _refresh_results, init_results_ui):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
