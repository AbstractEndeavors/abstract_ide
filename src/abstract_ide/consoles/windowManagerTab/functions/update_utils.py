from ..imports import *
# ---------------- table helpers ----------------
def update_table(self) -> None:
    search = self.search_edit.text().lower()
    t_req = self.type_combo.currentText()
    rows = [w for w in self.windows if (not search or search in w[2].lower()) and (t_req == "All" or w[4] == t_req)]
    self.table.setRowCount(len(rows))
    for r, data in enumerate(rows):
        for c, val in enumerate(data):
            item = QTableWidgetItem(val)
            item.setData(Qt.ItemDataRole.UserRole, data)
            if c == 1 and looks_unsaved(val):
                item.setForeground(QBrush(QColor("red")))
            self.table.setItem(r, c, item)
    self.table.resizeColumnsToContents()


def update_monitor_dropdown(self) -> None:
    self.monitor_combo.clear()
    self.monitor_combo.addItems([m[0] for m in self.monitors])
