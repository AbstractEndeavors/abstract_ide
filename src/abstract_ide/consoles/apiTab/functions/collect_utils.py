from ..imports import *
def _collect_table_data(self, table):
    data = {}
    for r in range(table.rowCount()):
        key_item = table.item(r, 0)
        if not key_item or not key_item.text().strip():
            continue
        val_item = table.item(r, 1)
        data[key_item.text().strip()] = val_item.text().strip() if val_item else ""
    return data

def _collect_headers(self):
    headers = {}
    for r in range(self.headers_table.rowCount()):
        # only include checked rows
        chk = self.headers_table.item(r, 0)
        if not chk or chk.checkState() != Qt.CheckState.Checked:
            continue
        key_item = self.headers_table.item(r, 1)
        key = key_item.text().strip() if key_item else ""
        value_cb = self.headers_table.cellWidget(r, 2)
        if value_cb:
            val = value_cb.currentText().strip()
        else:
            val_item = self.headers_table.item(r, 2)
            val = val_item.text().strip() if val_item else ""
        # if user picked/typed a MIME but left key blank, assume Content-Type
        if val and not key:
            key = "Content-Type"
            if key_item is None:
                key_item = QTableWidgetItem(key)
                self.headers_table.setItem(r, 1, key_item)
            else:
                key_item.setText(key)
        if key:
            headers[key] = val
    return headers
