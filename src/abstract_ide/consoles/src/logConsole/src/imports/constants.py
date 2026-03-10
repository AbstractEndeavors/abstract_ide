from .init_imports import *
LOG_DIR  = os.path.join(os.path.expanduser("~"), ".cache", "abstract_logging")
LOG_FILE = os.path.join(LOG_DIR, "finder.log")
os.makedirs(LOG_DIR, exist_ok=True)
