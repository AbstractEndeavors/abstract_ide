from __future__ import annotations
from ..imports import *  # keep your project-wide helpers/macros
import logging
from contextlib import suppress
from typing import Optional

import requests
from PySide6.QtCore import QSignalBlocker  # explicit import for safety
from PySide6.QtCore import QObject, QThread, Signal as pyqtSignal

class PrefixDetectWorker(QObject):
    done   = pyqtSignal(str)   # prefix
    error  = pyqtSignal(str)

    def __init__(self, base: str, start_prefix: str = "/api"):
        super().__init__()
        self.base = base.rstrip("/")
        self.start_prefix = _norm_prefix(start_prefix)

    def run(self):
        try:
            roots      = ["", "/api", "/v1", "/api/v1"]
            config_eps = ["/config", "/__config", "/_meta"]
            headers = {"Accept": "application/json"}
            timeout = 3
            found: Optional[str] = None

            for root in roots:
                root_url = self.base + root
                for ep in config_eps:
                    url = root_url + ep
                    try:
                        r = requests.get(url, headers=headers, timeout=timeout)
                        if not r.ok: 
                            continue
                        j = _json_try(r)
                        if isinstance(j, dict):
                            val = j.get("static_url_path") or j.get("api_prefix")
                            if isinstance(val, str) and val.strip():
                                found = _norm_prefix(val)
                                break
                    except Exception:
                        continue
                if found:
                    break

            self.done.emit(found or self.start_prefix)
        except Exception as e:
            self.error.emit(str(e))

def start_detect_api_prefix_async(self):
    base = self.base_combo.currentText().rstrip("/")
    w = PrefixDetectWorker(base, self.api_prefix_in.text() or "/api")
    t = QThread(self)
    w.moveToThread(t)
    t.started.connect(w.run)
    # Wire results
    def _set_prefix(pfx: str):
        with QSignalBlocker(self.api_prefix_in):
            self.api_prefix_in.setText(pfx)
        self.api_prefix = pfx
        with suppress(Exception):
            self.fetch_button.setText(_fetch_label(self))
        logging.info("API prefix set to: %s (base=%s)", pfx, base)
        t.quit()
    def _err(msg: str):
        logging.error("Prefix detect error: %s", msg)
        t.quit()
    w.done.connect(_set_prefix)
    w.error.connect(_err)
    t.finished.connect(w.deleteLater)
    t.finished.connect(t.deleteLater)
    # Prevent GC
    if not hasattr(self, "_threads"): self._threads = []
    self._threads.append(t)
    t.start()

# ── small helpers ─────────────────────────────────────────────────────────────
def _norm_prefix(p: Optional[str]) -> str:
    p = (p or "/api").strip()
    if not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/")

def _json_try(r: requests.Response) -> dict | None:
    with suppress(Exception):
        return r.json()
    return None

# ── UI helpers (unchanged API; deduped normalization) ─────────────────────────
def _fetch_label(self) -> str:
    self.api_prefix = _norm_prefix(getattr(self, "api_prefix", "/api"))
    return f"Fetch {self.api_prefix}/endpoints"

def _normalized_prefix(self) -> str:
    return _norm_prefix(self.api_prefix_in.text())

def _on_api_prefix_changed(self, _txt: str):
    self.api_prefix = _normalized_prefix(self)
    self.fetch_button.setText(_fetch_label(self))

# ── detection (sync, small + robust) ─────────────────────────────────────────
def detect_api_prefix(self) -> str:
    """
    Attempts to detect the API prefix by probing a set of small config endpoints.
    Accepts either {"static_url_path": "/api"} or {"api_prefix": "/api"}.
    Falls back to current entry or '/api'.
    """
    base = self.base_combo.currentText().rstrip("/")
    # endpoints we try at the root and under some likely prefixes
    roots      = ["", "/api", "/v1", "/api/v1"]
    config_eps = ["/config", "/__config", "/_meta"]

    headers = {"Accept": "application/json"}
    timeout = 3
    found: Optional[str] = None

    for root in roots:
        root_url = base + root
        for ep in config_eps:
            url = root_url + ep
            try:
                r = requests.get(url, headers=headers, timeout=timeout)
                if not r.ok:
                    continue
                j = _json_try(r)
                if not isinstance(j, dict):
                    continue
                val = j.get("static_url_path") or j.get("api_prefix")
                if isinstance(val, str) and val.strip():
                    found = _norm_prefix(val)
                    logging.info("Detected API prefix %s from %s", found, url)
                    break
            except Exception:
                continue
        if found:
            break

    # fallback chain: detected → user text → '/api'
    new_prefix = found or _norm_prefix(self.api_prefix_in.text() or "/api")
    # avoid triggering _on_api_prefix_changed while updating the widget
    with QSignalBlocker(self.api_prefix_in):
        self.api_prefix_in.setText(new_prefix)
    self.api_prefix = new_prefix

    # update button label safely
    with suppress(Exception):
        self.fetch_button.setText(_fetch_label(self))

    logging.info("API prefix set to: %s (base=%s)", self.api_prefix, base)
    return self.api_prefix
