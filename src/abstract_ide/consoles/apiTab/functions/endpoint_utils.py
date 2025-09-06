from ..imports import *
def fetch_remote_endpoints(self):
    base = self.base_combo.currentText().rstrip('/')
    prefix = self._normalized_prefix()
    url = f"{base}{prefix}/endpoints"
    self.log_output.clear()
    logging.info(f"Fetching remote endpoints from {url}")
    try:
        data = getRequest(url=url)
        if isinstance(data, list):
            self._populate_endpoints(data)
            logging.info("✔ Remote endpoints loaded")
        else:
            logging.warning(f"{prefix}/endpoints returned non-list, ignoring")
    except Exception as e:
        logging.error(f"Failed to fetch endpoints: {e}")
        QMessageBox.warning(self, "Fetch Error", str(e))

def _populate_endpoints(self, lst):
    self.endpoints_table.clearContents()
    self.endpoints_table.setRowCount(len(lst))
    for i, (path, methods) in enumerate(lst):
        self.endpoints_table.setItem(i, 0, QTableWidgetItem(path))
        self.endpoints_table.setItem(i, 1, QTableWidgetItem(methods))

def on_endpoint_selected(self, row, col):
    ep = self.endpoints_table.item(row, 0).text()
    cfg = self.config_cache.get(ep, {})
    # restore override method
    if 'method' in cfg:
        self.method_box.setCurrentText(cfg['method'])
    # restore headers, but only for UNCHECKED rows
    saved_headers = cfg.get('headers', {})
    for r in range(self.headers_table.rowCount()):
        chk_item = self.headers_table.item(r, 0)
        if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
            continue
        key_item = self.headers_table.item(r, 1)
        key = key_item.text().strip() if key_item else ""
        val_item = self.headers_table.item(r, 2)
        if key and key in saved_headers:
            chk_item.setCheckState(Qt.CheckState.Checked)
            val = saved_headers[key]
            if self.headers_table.cellWidget(r, 2):
                self.headers_table.cellWidget(r, 2).setCurrentText(val)
            elif val_item:
                val_item.setText(val)
        else:
            chk_item.setCheckState(Qt.CheckState.Unchecked)
            if self.headers_table.cellWidget(r, 2):
                self.headers_table.cellWidget(r, 2).setCurrentText("")
            elif val_item:
                val_item.setText("")

def methodComboInit(self,layout):
    # Only create if not already made by _build_ui
    if not hasattr(self, "method_box") or self.method_box is None:
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Override Method:"))
        self.method_box = QComboBox()
        self.method_box.addItems(["GET", "POST"])
        method_row.addWidget(self.method_box)
        layout.addLayout(method_row)
    else:
        # If it exists, ensure at least GET/POST are available
        have = {self.method_box.itemText(i) for i in range(self.method_box.count())}
        for m in ("GET", "POST"):
            if m not in have:
                self.method_box.addItem(m)
