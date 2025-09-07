from .imports import *
from .media_autofill import *

# ---------- Optional Abstract integrations (kept, not removed) ----------
try:
    from abstract_webtools.managers.networkManager import NetworkManager
    from abstract_webtools.managers.videoDownloader import downloadvideo
    from abstract_webtools.managers.crawlManager import SitemapGenerator
    from abstract_webtools.managers.dynamicRateLimiter import DynamicRateLimiterManager
except ImportError:
    NetworkManager = None
    downloadvideo = None
    SitemapGenerator = None
    DynamicRateLimiterManager = None



from .emulatorConfig import *
from .politeFetcher import *
from .baseEngine import *
from .seleneumEngine import *
from .playwriteEngine import *
from .scrapeWorker import *
from .crawlWorker import *
