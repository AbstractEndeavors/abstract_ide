from .init_imports import *
LOG_DIR = os.path.join(os.path.expanduser("~"), ".cache", "abstract_finder")
LOG_FILE = os.path.join(LOG_DIR, "finder.log")
os.makedirs(LOG_DIR, exist_ok=True)

root_logger = logging.getLogger("launcher")
if not root_logger.handlers:
    root_logger.setLevel(logging.DEBUG)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"))
    root_logger.addHandler(fh)

abs_dir = get_caller_dir()
env_loc = os.path.join(abs_dir,'.env')
API_BASE = get_env_value('API_BASE',env_loc)
imports_dir = os.path.dirname(abs_dir)
main_dir = os.path.dirname(imports_dir)
OUT_DIR = os.path.join(main_dir,'downloads')
REGISTRY = os.path.join(OUT_DIR,'registry.json')
OUT_DIR = Path(OUT_DIR)
userName = get_env_value('userName',env_loc)
passWord = get_env_value('passWord',env_loc)
URL_KEY = "DB_DSN_POSTGRESQL_URL"
if os.path.isdir('/home/flerb'):
    URL_KEY = "DB_DSN_POSTGRESQL_URL_REMOTE"
DB_DSN = get_env_value(URL_KEY,env_loc)
FILTERS = get_env_value('FILTERS',env_loc)
if FILTERS:
    FILTERS = FILTERS.replace('>',' ').split(',')
MEDIA_TYPE = get_env_value('MEDIA_TYPE',env_loc)
if MEDIA_TYPE:
    MEDIA_TYPE = MEDIA_TYPE.replace('>',' ')
USER = get_env_value('USER',env_loc)
if USER:
    USER = USER.replace('>',' ')
ENV_PATH = get_env_value("ABSTRACT_IDE_ENV_PATH")
BASE_URL = get_env_value("ABSTRACT_IDE_DB_BASE_URL",path=ENV_PATH) or 'https://k2s.cc/file/'
TARGET_DOMAIN = get_env_value("ABSTRACT_IDE_DB_TARGET_DOMAIN",path=ENV_PATH) or 'https://k2s.cc'
