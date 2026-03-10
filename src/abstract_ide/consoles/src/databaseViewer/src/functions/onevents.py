from ..imports import *
def _on_connect(self):
    dialog = ConnectionDialog(self)
    if dialog.exec():
        config = dialog.get_config()
        if config:
            self.db_config = config  # Store for stream worker
            self._log(f"Connecting to database...")
            self.status_label.setText("Connecting...")
            self.worker.submit(Task(TaskType.CONNECT, {'config': config}))
        else:
            QMessageBox.warning(self, "Error", "Invalid connection settings")

def _on_refresh(self):
    self._log("Refreshing tables...")
    self.worker.submit(Task(TaskType.LIST_TABLES))

def _on_table_selected(self, item):
    table_name = item.text()
    self.current_table = table_name
    self._log(f"Loading table: {table_name}")
    
    # Get columns
    self.worker.submit(Task(TaskType.LIST_COLUMNS, {'table': table_name}))
    
    # Preview data
    self.worker.submit(Task(
        TaskType.PREVIEW, 
        {'table': table_name, 'limit': self.limit_spin.value()}
    ))

def _on_search(self):
    if not self.current_table:
        self._log("No table selected")
        return
    
    column = self.search_column.currentText()
    value = self.search_value.text().strip()
    
    if not column:
        self._log("No column selected")
        return
    
    self._log(f"Searching {self.current_table}.{column} for '{value}'...")
    
    self.worker.submit(Task(TaskType.QUERY, {
        'table': self.current_table,
        'column': column,
        'value': value,
        'limit': self.limit_spin.value()
    }))

def _on_result(self, result: TaskResult):
    if not result.success:
        self._log(f"âŒ Error: {result.error}")
        self.status_label.setText("Error")
        return
    
    if result.task_type == TaskType.CONNECT:
        self._log("âœ… Connected!")
        self.status_label.setText("Connected")
        self.refresh_btn.setEnabled(True)
        self._on_refresh()
    
    elif result.task_type == TaskType.LIST_TABLES:
        tables = result.data
        self.tables_list.clear()
        self.tables_list.addItems(tables)
        self._log(f"Found {len(tables)} tables")
    
    elif result.task_type == TaskType.LIST_COLUMNS:
        columns = result.data['columns']
        types = result.data['types']
        self.column_types = types
        self.columns_list_data = columns
        
        self.columns_list.clear()
        self.search_column.clear()
        self.watermark_combo.clear()
        
        for col in columns:
            col_type = types.get(col, "?")
            self.columns_list.addItem(f"{col} ({col_type})")
            self.search_column.addItem(col)
            self.watermark_combo.addItem(col)
        
        # Try to auto-select a good watermark column
        for preferred in ['id', 'created_at', 'timestamp', 'updated_at']:
            if preferred in columns:
                idx = columns.index(preferred)
                self.watermark_combo.setCurrentIndex(idx)
                break
        
        self.watch_btn.setEnabled(True)
    
    elif result.task_type in (TaskType.PREVIEW, TaskType.QUERY):
        df = result.data
        self.table_model.set_dataframe(df)
        self._log(f"Loaded {len(df)} rows, {len(df.columns)} columns")

def _on_watch_toggle(self, checked: bool):
    """Toggle streaming for the current table"""
    if not self.current_table:
        self._log("No table selected")
        self.watch_btn.setChecked(False)
        return
    
    if checked:
        self._start_stream()
    else:
        self._stop_stream()
