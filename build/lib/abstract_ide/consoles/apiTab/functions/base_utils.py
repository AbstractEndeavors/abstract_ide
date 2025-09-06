from ..imports import *
try:
    from PyQt6.sip import isdeleted  # PyQt6-safe deleted check
except Exception:
    def isdeleted(obj):  # fallback
        try:
            _ = obj.metaObject()
            return False
        except Exception:
            return True

def _on_base_index_changed(self, *_):
    """Adapter for currentIndexChanged → calls _on_base_changed safely."""
    return _on_base_changed(self, self.base_combo)

def _on_base_changed(self, widget, *args):
    # Guard against deleted widget during shutdown
    if widget is None or isdeleted(widget):
        return
    # Prefer direct text to avoid helper calling into deleted objects
    text = (widget.currentText() or "").strip().rstrip("/")
    pref = _norm_prefix(text or "/api")
    self.api_prefix_in.setText(pref)

def _on_base_text_edited(self, text: str):
    # Only react if the user typed (i.e., not selecting an item).
    # If the current index matches an item, _on_base_changed already ran.
    idx = self.base_combo.currentIndex()
    if idx == -1: # free-typed URL
        # choose behavior: keep user’s current prefix, or reset to default
        if not self.api_prefix_in.text().strip():
            self.api_prefix_in.setText(_norm_prefix("/api"))
        # else: leave as-is
def _collect_kv(self, table: QTableWidget) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for r in range(table.rowCount()):
        k = table.item(r, 0)
        if not k or not k.text().strip():
            continue
        v = table.item(r, 1)
        data[k.text().strip()] = v.text().strip() if v else ""
    return data
def _build_url(self, ep: str) -> str:
    base = (self.base_combo.currentText().strip().rstrip('/'))
    if not base:
        raise ValueError("Base URL is empty.")
    pref = self._normalized_prefix().rstrip('/')
    ep = ep.strip()
    ep = ep if ep.startswith('/') else '/' + ep
    return f"{base}{pref}{ep}"
