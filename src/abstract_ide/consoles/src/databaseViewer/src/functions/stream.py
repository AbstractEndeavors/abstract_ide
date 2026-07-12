from ..imports import *


def _start_stream(self):
    """Start streaming for current table"""
    if not self.db_config:
        self._log("Not connected - no database config")
        self.watch_btn.setChecked(False)
        return
    watermark = self.watermark_combo.currentText()
    if not watermark:
        self._log("No watermark column selected")
        self.watch_btn.setChecked(False)
        return

    self.stream_worker = StreamWorker(self.db_config)
    self.stream_worker.new_rows.connect(self._on_stream_rows)
    self.stream_worker.error.connect(self._on_stream_error)
    self.stream_worker.status_changed.connect(self._on_stream_status)

    config = StreamConfig(
        table_name=self.current_table,
        watermark_column=watermark,
        poll_interval_ms=self.poll_interval.value(),
    )
    self.stream_worker.subscribe(config)
    self.streaming_tables.add(self.current_table)
    self.watch_btn.setText("⏹ Stop")
    self._log("Started streaming " + self.current_table + " (tracking " + watermark + ")")
    self.results_tabs.setCurrentIndex(1)


def _stop_stream(self):
    """Stop streaming for current table"""
    if self.stream_worker:
        self.stream_worker.unsubscribe(self.current_table)
    self.streaming_tables.discard(self.current_table)
    self.watch_btn.setText("▶ Watch")
    self._log("Stopped streaming " + self.current_table)


def _on_stream_rows(self, event):
    """Handle new rows from stream"""
    if self._stream_data.empty:
        self._stream_data = event.rows
    else:
        self._stream_data = pd.concat([event.rows, self._stream_data])
    self._stream_row_count = len(self._stream_data)
    self._stream_data = self._stream_data.head(10000)

    self.stream_model.set_dataframe(self._stream_data)
    self.stream_count.setText(str(len(event.rows)) + " rows (" + str(self._stream_row_count) + " total)")
    self.results_tabs.setTabText(1, "Stream (" + str(len(event.rows)) + " new)")
    self.stream_view.scrollToTop()
    self._log("⚡ " + str(len(event.rows)) + " new rows in " + event.table_name)


def _on_stream_error(self, error):
    self._log("Stream error: " + str(error))


def _on_stream_status(self, status):
    self.stream_status.setText("Status: " + str(status))


def _on_clear_stream(self):
    """Clear stream data"""
    self._stream_data = pd.DataFrame()
    self._stream_row_count = 0
    self.stream_model.set_dataframe(self._stream_data)
    self.stream_count.setText("0 rows")
    self.results_tabs.setTabText(1, "Stream (0)")
