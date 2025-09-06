from .imports import *
# ─── Configuration ──────────────────────────────────────────────────────
PREDEFINED_BASE_URLS = [
    ("https://abstractendeavors.com",'api'),
    ("https://clownworld.biz",'media'),
    ("https://typicallyoutliers.com",'api'),
    ("https://thedailydialectics.com",'api'),
]
def _norm_prefix(p: str) -> str:
    p = (p or "/api").strip()
    if not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/")
PREDEFINED_HEADERS = [
    ("Content-Type", "application/json"),
    ("Accept", "application/json"),
    ("Authorization", "Bearer "),
]
MIME_TYPES_HEADERS = MIME_TYPES
