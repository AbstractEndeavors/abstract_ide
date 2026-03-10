from ..imports import *
def _start_stream(self):
    """Start streaming for current table"""
    if not self.db_config:
        self._log("Not connected - no database config")
        self.watch_btn.setChecked(False)
        return
    
    # Create stream worker if needed
    if not self.stream_worker:
        self.stream_worker = StreamWorker(self.db_config)  # Pass config, not connection
        self.stream_worker.new_rows.connect(self._on_stream_rows)
        self.stream_worker.error.connect(self._on_stream_error)
        self.stream_worker.status_changed.connect(self._on_stream_status)
    
    watermark_col = self.watermark_combo.currentText()
    if not watermark_col:
        self._log("No watermark column selected")
        self.watch_btn.setChecked(False)
        return
    
    config = StreamConfig(
        table_name=self.current_table,
        watermark_column=watermark_col,
        poll_interval_ms=self.poll_interval.value(),
        batch_size=50
    )
    
    self.stream_worker.subscribe(config)
    self.streaming_tables.add(self.current_table)
    self.watch_btn.setText("â¹ Stop")
    self._log(f"Started streaming {self.current_table} (tracking {watermark_col})")
    
    # Switch to stream tab
    self.results_tabs.setCurrentIndex(1)

def _stop_stream(self):
    """Stop streaming for current table"""
    if self.stream_worker and self.current_table:
        self.stream_worker.unsubscribe(self.current_table)
        self.streaming_tables.discard(self.current_table)
    
    self.watch_btn.setText("â–¶ Watch")
    self._log(f"Stopped streaming {self.current_table}")

def _on_stream_rows(self, event: StreamEvent):
    """Handle new rows from stream"""
    # Prepend new rows to stream data (newest first)
    if self._stream_data.empty:
        self._stream_data = event.rows
    else:
        self._stream_data = pd.concat([event.rows, self._stream_data], ignore_index=True)
    
    # Limit stored rows to prevent memory issues
    max_rows = 1000
    if len(self._stream_data) > max_rows:
        self._stream_data = self._stream_data.head(max_rows)
    
    self._stream_row_count += len(event.rows)
    
    # Update view
    self.stream_model.set_dataframe(self._stream_data)
    self.stream_count.setText(f"{len(self._stream_data)} rows ({self._stream_row_count} total)")
    self.results_tabs.setTabText(1, f"Stream ({len(event.rows)} new)")
    
    # Scroll to top to show newest
    self.stream_view.scrollToTop()
    
    self._log(f"âš¡ {len(event.rows)} new rows in {event.table_name}")

def _on_stream_error(self, error: str):
    self._log(f"Stream error: {error}")

def _on_stream_status(self, status: str):
    self.stream_status.setText(f"Status: {status}")

def _on_clear_stream(self):
    """Clear stream data"""
    self._stream_data = pd.DataFrame()
    self._stream_row_count = 0
    self.stream_model.set_dataframe(self._stream_data)
    self.stream_count.setText("0 rows")
    self.results_tabs.setTabText(1, "Stream (0)")
