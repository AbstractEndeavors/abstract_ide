from .imports import *
# ---------------- table helpers ----------------
def update_table(self) -> None:
    search = self.search_edit.text().lower()
    t_req = self.type_combo.currentText()

    # rows = filtered windows
    rows = [
        w for w in self.windows
        if (not search or search in w[2].lower())
        and (t_req == "All" or w[4] == t_req)
    ]

    self.table.setRowCount(len(rows))

    for r, data in enumerate(rows):
        win_id, pid, title, monitor, win_type, has_selection = data

        # convert values to strings for table
        col_values = [
            win_id,
            pid,
            title,
            monitor,
            win_type,
            "✔" if has_selection else ""
        ]

        for c, val in enumerate(col_values):
            item = QTableWidgetItem(val)
            item.setData(Qt.ItemDataRole.UserRole, data)

            # mark unsaved items red (your existing rule)
            if c == 1 and looks_unsaved(pid):
                item.setForeground(QBrush(QColor("red")))

            self.table.setItem(r, c, item)

        # --- NEW: color entire row if window currently has highlighted text ---
        if has_selection:
            for c in range(len(col_values)):
                it = self.table.item(r, c)
                if it:
                    it.setBackground(QBrush(QColor("#c8ffc8")))  # pale green

    self.table.resizeColumnsToContents()


def update_monitor_dropdown(self) -> None:
    self.monitor_combo.clear()
    self.monitor_combo.addItems([m[0] for m in self.monitors])
