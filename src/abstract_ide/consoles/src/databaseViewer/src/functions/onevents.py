from ..imports import *


def _on_connect(self):
    dialog = ConnectionDialog(self)
    if dialog.exec():
        config = dialog.get_config()
        if config:
            self.db_config = config
            self._log("Connecting to database...")
            self.status_label.setText("Connecting...")
            self.worker.submit(Task(TaskType.CONNECT, {"config": config}))
        else:
            QMessageBox.warning(self, "Error", "Invalid connection settings")


def _on_refresh(self):
    self._log("Refreshing tables...")
    self.worker.submit(Task(TaskType.LIST_TABLES))


def _on_table_selected(self, item):
    table = item.text()
    self.current_table = table
    self._log("Loading table: " + table)
    self.worker.submit(Task(TaskType.LIST_COLUMNS, {"table": table}))
    self.worker.submit(Task(TaskType.PREVIEW, {"table": table, "limit": self.limit_spin.value()}))


def _on_search(self):
    if not self.current_table:
        self._log("No table selected")
        return
    column = self.search_column.currentText()
    if not column:
        self._log("No column selected")
        return
    value = self.search_value.text().strip()
    self._log("Searching " + self.current_table + "." + column + " for '" + value + "'...")
    self.worker.submit(Task(TaskType.QUERY, {
        "table": self.current_table,
        "column": column,
        "value": value,
        "limit": self.limit_spin.value(),
    }))


def _on_result(self, result):
    if not result.success:
        self._log("❌ Error: " + str(result.error))
        self.status_label.setText("Error")
        return

    task_type = result.task_type

    if task_type == TaskType.CONNECT:
        self._log("✅ Connected!")
        self.status_label.setText("Connected")
        self.refresh_btn.setEnabled(True)
        self._on_refresh()

    elif task_type == TaskType.LIST_TABLES:
        self.tables_list.clear()
        self.tables_list.addItems(result.data)
        self._log("Found " + str(len(result.data)) + " tables")

    elif task_type == TaskType.LIST_COLUMNS:
        self.column_types = result.data["types"]
        self.columns_list_data = result.data["columns"]
        self.columns_list.clear()
        for col in self.columns_list_data:
            self.columns_list.addItem(col + " (" + self.column_types.get(col, "?") + ")")
        self.search_column.clear()
        self.search_column.addItems(self.columns_list_data)
        self.watermark_combo.clear()
        self.watermark_combo.addItems(self.columns_list_data)
        # sensible default watermark column
        for candidate in ("id", "created_at", "updated_at"):
            if candidate in self.columns_list_data:
                self.watermark_combo.setCurrentIndex(self.columns_list_data.index(candidate))
                break
        self.watch_btn.setEnabled(True)

    elif task_type in (TaskType.PREVIEW, TaskType.QUERY):
        self.table_model.set_dataframe(result.data)
        self._log("Loaded " + str(len(result.data)) + " rows, "
                  + str(len(result.data.columns)) + " columns")


def _on_watch_toggle(self, checked):
    """Toggle streaming for the current table"""
    if not self.current_table:
        self._log("No table selected")
        self.watch_btn.setChecked(False)
        return
    if checked:
        self._start_stream()
    else:
        self._stop_stream()
