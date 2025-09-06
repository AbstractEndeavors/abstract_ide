from ..imports import *
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin

def _probe_session():
    s = requests.Session()
    # limit redirects during probing so we detect loops fast
    r = Retry(total=1, redirect=0, backoff_factor=0.1, allowed_methods=frozenset(["GET"]))
    s.mount("http://", HTTPAdapter(max_retries=r))
    s.mount("https://", HTTPAdapter(max_retries=r))
    return s

def canonicalize_slash(base: str, ep: str, timeout: int = 5) -> str:
    """Return a URL that doesn't bounce between /path and /path/."""
    if not ep.startswith("/"):
        ep = "/" + ep
    url = base.rstrip("/") + ep
    candidates = [url.rstrip("/"), url.rstrip("/") + "/"]
    s = _probe_session()

    for cand in candidates:
        try:
            r = s.get(cand, allow_redirects=False, timeout=timeout)
            if r.status_code < 300:
                return cand
            if 300 <= r.status_code < 400:
                loc = r.headers.get("location", "")
                if loc:
                    # make absolute for comparison
                    if loc.startswith("/"):
                        loc = base.rstrip("/") + loc
                    # if it's just the other slash form, try that directly once
                    if loc.rstrip("/") == cand.rstrip("/"):
                        r2 = s.get(loc, allow_redirects=False, timeout=timeout)
                        if r2.status_code < 300:
                            return loc
        except Exception:
            continue
    # fallback (won’t fix a broken server, but at least deterministic)
    return candidates[-1]
