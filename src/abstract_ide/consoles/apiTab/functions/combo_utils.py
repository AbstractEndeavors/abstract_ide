from ..imports import *
def _make_value_combo(self, row_idx: int) -> QComboBox:
    cb = BoundedCombo(self.headers_table, editable=True) # allow free text
    cb.addItems(self._mime_values_for_category(""))
    # keep your completer if you like
    comp = QCompleter(cb.model(), cb)
    comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    cb.setCompleter(comp)
    self._row_value_boxes[row_idx] = cb
    return cb

def _make_type_combo(self, row_idx: int) -> QComboBox:
    cb = BoundedCombo(self.headers_table, editable=False)
    cb.addItem("") # Any
    cb.addItems(sorted(MIME_TYPES.keys()))
    cb.currentTextChanged.connect(partial(self._on_type_changed, row_idx))
    self._row_type_boxes[row_idx] = cb
    return cb

def _mime_values_for_category(self, category: str) -> list[str]:
    if not category: # Any
        return sorted({mime for m in MIME_TYPES.values() for mime in m.values()})
    return sorted(MIME_TYPES.get(category, {}).values())

def _on_type_changed(self, row_idx: int, category: str):
    val_cb = self._row_value_boxes.get(row_idx)
    if not val_cb:
        return
    prior = val_cb.currentText().strip()
    # rebuild options based on selected TYPE
    vals = self._mime_values_for_category(category)
    val_cb.blockSignals(True)
    val_cb.clear()
    val_cb.addItems(vals)
    val_cb.blockSignals(False)
    # keep the previous choice if it still exists
    if prior in vals:
        val_cb.setCurrentText(prior)



