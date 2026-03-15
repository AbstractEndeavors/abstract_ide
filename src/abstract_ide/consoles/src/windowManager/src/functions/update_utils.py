from .imports import *

class UpdateUtilsMixin:

    def update_table(self):

        search = self.search_edit.text().lower()
        t_req = self.type_combo.currentText()

        rows = [
            w for w in self.windows
            if (not search or search in w[2].lower())
            and (t_req == "All" or w[4] == t_req)
        ]

        self.table.setRowCount(len(rows))

        for r, data in enumerate(rows):

            win_id, pid, title, monitor, win_type, has_selection = data

            vals = [
                win_id,
                pid,
                title,
                monitor,
                win_type,
                "✔" if has_selection else ""
            ]

            for c, val in enumerate(vals):

                item = QTableWidgetItem(val)

                if c == 0:
                    item.setData(Qt.ItemDataRole.UserRole, data)

                if c == 2 and looks_unsaved(title):
                    item.setForeground(QBrush(QColor("red")))

                self.table.setItem(r, c, item)

            if has_selection:

                for c in range(len(vals)):

                    it = self.table.item(r, c)

                    if it:
                        it.setBackground(QBrush(QColor("#c8ffc8")))

    def update_monitor_dropdown(self):

        self.monitor_combo.clear()

        if self.monitors:
            self.monitor_combo.addItems([m[0] for m in self.monitors])

    def update_type_dropdown(self):

        current = self.type_combo.currentText()

        types = sorted({w[4] for w in self.windows})

        self.type_combo.blockSignals(True)

        self.type_combo.clear()
        self.type_combo.addItem("All")
        self.type_combo.addItems(types)

        idx = self.type_combo.findText(current)

        self.type_combo.setCurrentIndex(idx if idx >= 0 else 0)

        self.type_combo.blockSignals(False)
