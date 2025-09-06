from ..imports import *
def _maybe_add_header_row(self, row, col):
    last = self.headers_table.rowCount() - 1
    if row != last:
        return
    key_item = self.headers_table.item(row, 1)
    val_item = self.headers_table.item(row, 2)
    if (key_item and key_item.text().strip()) or (val_item and val_item.text().strip()):
        self.headers_table.blockSignals(True)
        self.headers_table.insertRow(last+1)
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        chk.setCheckState(Qt.CheckState.Unchecked)
        self.headers_table.setItem(last+1, 0, chk)
        self.headers_table.setItem(last+1, 1, QTableWidgetItem(""))
        self.headers_table.setItem(last+1, 2, QTableWidgetItem(""))
        self.headers_table.blockSignals(False)

def _maybe_add_body_row(self, row, col):
    last = self.body_table.rowCount() - 1
    key_item = self.body_table.item(row, 0)
    val_item = self.body_table.item(row, 1)
    if row == last and ((key_item and key_item.text().strip()) or (val_item and val_item.text().strip())):
        self.body_table.blockSignals(True)
        self.body_table.insertRow(last+1)
        self.body_table.setItem(last+1, 0, QTableWidgetItem(""))
        self.body_table.setItem(last+1, 1, QTableWidgetItem(""))
        self.body_table.blockSignals(False)
