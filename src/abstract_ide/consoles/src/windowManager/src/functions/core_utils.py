from .imports import *
class CoreUtilsMixin:
    @staticmethod
    def isNone(obj):
        return obj is None

    @staticmethod
    def compare_lowers(a, b, none_ok=True):

        if a is None or b is None:
            return none_ok

        return str(a).lower() == str(b).lower()

    def is_self(self, win_id, pid):

        return (
            self.compare_lowers(win_id, self._self_win_hex, False)
            or self.compare_lowers(pid, self._self_pid, False)
        )

    def refresh(self) -> None:

        self.wm_compute_self_ids()
        self.wm_refresh_windows()
        self.wm_refresh_monitors()

        self.update_table()
        self.update_monitor_dropdown()
        self.update_type_dropdown()

        self.statusBar().showMessage("Refreshed", 2500)

    def _selected_rows(self):

        sel = []

        model = self.table.selectionModel()
        if not model:
            return sel

        for idx in model.selectedRows():

            item = self.table.item(idx.row(), 0)
            if not item:
                continue

            data = item.data(Qt.ItemDataRole.UserRole)

            if data:
                sel.append(data)

        return sel

    def select_all_by_type(self):

        req = self.type_combo.currentText()

        if req == "All":
            self.table.selectAll()
            return

        self.table.clearSelection()

        for r in range(self.table.rowCount()):

            if self.table.item(r, 4).text() == req:
                self.table.selectRow(r)
    def is_self(self, win_id, pid):
        self.get_self()
        return (
            self.compare_lowers(win_id, self.self_win_hex, none_ok=False)
            or self.compare_lowers(pid, self.self_pid, none_ok=False)
        )
    def get_self(self):
        self.self_pid = getattr(self, "_self_pid", None)
        self.self_win_hex = getattr(self, "_self_win_hex", None)

    def update_type_dropdown(self) -> None:
        current = self.type_combo.currentText()
        types = sorted({w[4] for w in self.windows})
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItem("All")
        self.type_combo.addItems(types)
        # restore previous selection if still valid
        idx = self.type_combo.findText(current)
        self.type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.type_combo.blockSignals(False)



    def move_window(self) -> None:
        sel = self._selected_rows()
        if not sel:
            return
        tgt = self.monitor_combo.currentText()
        for win_id, *_ in sel:
            for name, x, y, *_ in self.monitors:
                if name == tgt:
                    self.run_command(f"wmctrl -i -r {win_id} -e 0,{x},{y},-1,-1")
        self.refresh()
    def control_window(self, act: str) -> None:
        sel = self._selected_rows()
        if not sel:
            return
        for win_id, *_ in sel:
            if act == "minimize":
                self.run_command(f"xdotool windowminimize {win_id}")
            elif act == "maximize":
                self.run_command(f"wmctrl -i -r {win_id} -b add,maximized_vert,maximized_horz")
        self.refresh()
    def should_close(self,win_id,pid,title,include_unsaved):
        if self.is_self(win_id,pid):
            return False
        if not include_unsaved:
            if looks_unsaved(title):
                return False
        return True
    def close_selected(self, include_unsaved: bool) -> None:

        sel = self._selected_rows()
        if not sel:
            return

        skip = []
        to_close = []

        for data in sel:
            win_id, pid, title, *_ = data

            if self.should_close(win_id, pid, title, include_unsaved):
                to_close.append((win_id, title))
            else:
                skip.append(title)

        if not to_close:
            QMessageBox.information(self, "Nothing to close", "No eligible windows selected.")
            return

        for win_id, _ in to_close:

            # attempt graceful close
            out = self.run_command(f"wmctrl -i -c {win_id}")

            # fallback if wmctrl fails
            if not out:
                self.run_command(f"xdotool windowkill {win_id}")

        skipped_note = f" (skipped {len(skip)})" if skip else ""

        self.statusBar().showMessage(
            f"Closed {len(to_close)} window(s){skipped_note}", 4000
        )

        self.refresh()
    def activate_window(self, item) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)  # Qt6 enum
        if data:
            self.run_command(f"xdotool windowactivate {data[0]}")
