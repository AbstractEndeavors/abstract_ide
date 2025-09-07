from .imports import *
# ---------- Config ----------
DEFAULT_TIMEOUT = 10
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
DOC_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".md", ".rtf"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}

mimetypes.init()

def _ext_from_url(u: str) -> str:
    path = urlparse(u).path
    name = Path(unquote(path)).name
    ext = (Path(name).suffix or "").lower()
    return ext

def _type_from_ext(ext: str) -> Optional[str]:
    if ext in IMG_EXTS: return "image"
    if ext in DOC_EXTS: return "document"
    if ext in VIDEO_EXTS: return "video"
    if ext in AUDIO_EXTS: return "audio"
    if ext:  # guess by mimetype
        mt, _ = mimetypes.guess_type("x"+ext)
        if mt:
            if mt.startswith("image/"): return "image"
            if mt.startswith("video/"): return "video"
            if mt.startswith("audio/"): return "audio"
            if mt in ("application/pdf",): return "document"
    return None

def _basename_filename(ext: str, url_or_path: str) -> Tuple[str, str]:
    """basename: with ext; filename: without ext (safe)"""
    name = Path(unquote(urlparse(url_or_path).path or url_or_path)).name or "index"
    if not Path(name).suffix and ext:
        name = f"{name}{ext}"
    base = name
    file_no_ext = base[:-len(ext)] if ext and base.lower().endswith(ext) else Path(base).stem
    # normalize
    safe_base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base)
    safe_file = re.sub(r"[^a-zA-Z0-9._-]+", "_", file_no_ext)
    return safe_base, safe_file

def _norm_keywords(keys: Any) -> List[str]:
    if not keys: return []
    if isinstance(keys, str):
        # split on commas and strip markdown "**"
        parts = [p.strip().strip("*") for p in keys.split(",") if p.strip()]
        return parts
    if isinstance(keys, list):
        return [str(k).strip().strip("*") for k in keys if str(k).strip()]
    return []

def _mk_keywords_str(keys: List[str]) -> str:
    # Keep your existing style (leading/trailing ** blocks preserved at ends if present)
    cleaned = [k for k in dict.fromkeys(k.strip() for k in keys) if k]  # de-dupe order-preserving
    return ", ".join(cleaned)

def _guess_alt_from_title_desc(title: Optional[str], desc: Optional[str], fallback: str) -> str:
    if title and title.strip(): return title.strip()
    if desc and desc.strip(): return desc.strip()
    return fallback

def _ensure_abs(base: str, href: Optional[str]) -> Optional[str]:
    if not href: return None
    if href.startswith("data:"): return href  # leave data URIs
    if href.startswith("//"):
        scheme = urlparse(base).scheme or "https"
        return f"{scheme}:{href}"
    if bool(urlparse(href).netloc):  # already absolute
        return href
    return urljoin(base, href)

def _http_fetch(u: str, session: Optional[requests.Session] = None) -> Tuple[int, Optional[str]]:
    s = session or requests.Session()
    try:
        r = s.get(u, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": UA})
        return r.status_code, r.text if "html" in (r.headers.get("Content-Type") or "") else None
    except Exception:
        return 0, None

def _derive_paths(entry: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    """Non-destructive: propose path-related fields if missing."""
    url = entry.get("url")
    if not url: return {}
    ext = entry.get("ext") or _ext_from_url(url)
    base_name, file_no_ext = _basename_filename(ext, url)

    out: Dict[str, Any] = {}
    out.setdefault("ext", ext or "")
    out.setdefault("basename", base_name)
    out.setdefault("filename", file_no_ext)

    # propose resized/OG assets for images (does not create files; just fills targets)
    if _type_from_ext(ext or "") == "image":
        # Keep your convention: "{dir}/og_{filename}.jpg" if you already use it
        # If the record has a 'thumbnail' directory-ish hint, reuse it; else derive from /imgs/...
        # Try to infer dir from url under your site, else leave relative
        parsed = urlparse(url)
        if parsed.netloc and base_url and parsed.netloc == urlparse(base_url).netloc:
            # path like /imgs/segment/foo.webp -> suggest og_foo.jpg alongside
            parent = str(Path(parsed.path).parent).lstrip("/")
            og_name = f"og_{file_no_ext}.jpg"
            out.setdefault("resized", f"{parent}/{og_name}")
        else:
            out.setdefault("resized", f"imgs/og_{file_no_ext}.jpg")
    return out

def _pull_page_metadata(url: str, base_url: str, session: Optional[requests.Session]=None) -> Dict[str, Any]:
    status, html = _http_fetch(url, session=session)
    meta: Dict[str, Any] = {"http_status": status}
    if status and html:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        # meta description & og:title/description
        def _meta(name: str) -> Optional[str]:
            tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
            if tag and tag.get("content"): return tag["content"].strip()
            return None
        description = _meta("description") or _meta("og:description")
        og_title = _meta("og:title")
        if og_title and not title: title = og_title
        meta.update({"page_title": title, "page_description": description})
        # canonical image?
        og_img = _meta("og:image")
        if og_img:
            meta["og_image"] = _ensure_abs(base_url or url, og_img)
    return meta

def enrich_media_item(item: Dict[str, Any], base_url: str, session: Optional[requests.Session]=None) -> Dict[str, Any]:
    """Return a NEW enriched item (non-destructive to original)."""
    item = dict(item)  # copy
    url = item.get("url")
    # 1) absolute url if relative
    if url and base_url:
        item["url"] = _ensure_abs(base_url, url)

    # 2) infer type/ext/basename/filename
    ext = (item.get("ext") or (url and _ext_from_url(item["url"])) or "").lower()
    mtype = item.get("type") or _type_from_ext(ext) or ("document" if (ext == ".html" or ext.endswith(".aspx") or ext.endswith(".php")) else None)
    if mtype is None and not ext and url:
        # guess by path (no ext): likely webpage
        mtype = "webpage"

    item.setdefault("ext", ext)
    item.setdefault("type", mtype)

    # 3) basename/filename
    base, file_no_ext = _basename_filename(ext, item.get("url") or item.get("path") or item.get("basename") or item.get("filename") or "")
    item.setdefault("basename", base)
    item.setdefault("filename", file_no_ext)

    # 4) paths (resized/og suggestions for images)
    item.update({k: v for k, v in _derive_paths(item, base_url).items() if k not in item or not item[k]})

    # 5) keywords normalization
    keys_list = _norm_keywords(item.get("keywords") or item.get("keywords_str"))
    if keys_list:
        item["keywords"] = keys_list
        item.setdefault("keywords_str", _mk_keywords_str(keys_list))

    # 6) Pull remote metadata for webpages/documents (and as fallback for images without alt/title)
    if item.get("url") and (item["type"] in ("webpage", "document") or not item.get("title") or not item.get("description")):
        meta = _pull_page_metadata(item["url"], base_url, session=session)
        # if we got a page title and missing title, fill
        if meta.get("page_title") and not item.get("title"):
            item["title"] = meta["page_title"]
        if meta.get("page_description") and not item.get("description"):
            item["description"] = meta["page_description"]
        # if no thumbnail but og:image exists, suggest it
        if not item.get("thumbnail_link") and meta.get("og_image"):
            item["thumbnail_link"] = meta["og_image"]
        item["http_status"] = meta.get("http_status")

    # 7) alt/caption fallbacks
    item.setdefault("alt", _guess_alt_from_title_desc(item.get("title"), item.get("description"), item.get("filename") or "media"))
    if not item.get("caption"):
        # simple caption heuristic
        cap = item.get("description") or item.get("title")
        if cap:
            item["caption"] = cap

    return item

def enrich_variables_json(variables: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich entire variables.json (non-destructive)."""
    base_url = variables.get("BASE_URL") or ""
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    out = dict(variables)
    media = variables.get("media") or []
    enriched = []
    for it in media:
        try:
            enriched.append(enrich_media_item(it, base_url, session=session))
            time.sleep(0.15)  # be polite
        except Exception as e:
            bad = dict(it)
            bad["enrich_error"] = str(e)
            enriched.append(bad)
    out["media"] = enriched

    # also normalize top-level keywords_str
    if variables.get("keywords_str") and "keywords" not in variables:
        keys = _norm_keywords(variables["keywords_str"])
        if keys:
            out["keywords"] = keys

    return out

def load_and_enrich(path: str) -> Dict[str, Any]:
    variables = json.loads(Path(path).read_text(encoding="utf-8"))
    enriched = enrich_variables_json(variables)
    return enriched

def save_json(obj: Dict[str, Any], path: str):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
