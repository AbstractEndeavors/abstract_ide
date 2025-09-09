from ..imports import *
import logging

def fetch_remote_endpoints(self):
    base = self.base_combo.currentText().rstrip('/')
    prefix = self._normalized_prefix()
    url = f"{base}{prefix}/endpoints"
    try:
        self.log_output.clear()
    except Exception:
        pass

    logging.info(f"Fetching remote endpoints from {url}")
    try:
        data = getRequest(url=url)
        # Accept: list of pairs, list of dicts, dict with "endpoints"
        if isinstance(data, dict) and "endpoints" in data:
            data = data["endpoints"]

        if not isinstance(data, list):
            logging.warning(f"{prefix}/endpoints returned non-list ({type(data).__name__}); ignoring")
            return

        self._populate_endpoints(data)
        logging.info("✔ Remote endpoints loaded")
    except Exception as e:
        logging.error(f"Failed to fetch endpoints: {e}")
        QMessageBox.warning(self, "Fetch Error", str(e))


def on_endpoint_selected(self, row, col):
    ep = self.endpoints_table.item(row, 0).text()
    cfg = getattr(self, "config_cache", {}).get(ep, {})

    # restore override method
    if 'method' in cfg and hasattr(self, "method_box") and self.method_box:
        self.method_box.setCurrentText(str(cfg['method']).upper())

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


def methodComboInit(self, layout):
    # Only create if not already made by _build_ui
    if not hasattr(self, "method_box") or self.method_box is None:
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Override Method:"))
        self.method_box = QComboBox()
        self.method_box.addItems(["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
        method_row.addWidget(self.method_box)
        layout.addLayout(method_row)
    else:
        # Ensure these at minimum
        have = {self.method_box.itemText(i) for i in range(self.method_box.count())}
        for m in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            if m not in have:
                self.method_box.addItem(m)

def _populate_endpoints(self, lst):
    """
    Accept items shaped as:
      - ("/path", "GET,POST") or ("/path", ["GET","POST"])
      - ["/path", "GET"]  (len>=2)
      - {"path": "/path", "methods": ["GET","POST"]}  (keys flexible: method/methods)
      - "/path"           (assume GET)
    Any malformed item is skipped, not fatal.
    """
    def _parse_item(item):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            p, m = item[0], item[1]
        elif isinstance(item, dict):
            p = item.get("path") or item.get("endpoint") or item.get("url") or ""
            m = item.get("methods") or item.get("method") or []
        elif isinstance(item, str):
            p, m = item, ["GET"]
        else:
            return None

        # normalize
        path = str(p).strip()
        if isinstance(m, (list, tuple, set)):
            methods = ", ".join(str(x).upper() for x in m)
        else:
            methods = str(m).upper().replace(" ", "")
        methods = methods or "GET"
        return (path, methods)

    self.endpoints_table.setRowCount(0)
    rows = 0
    for item in lst:
        parsed = _parse_item(item)
        if not parsed:
            continue
        path, methods = parsed
        if not path:
            continue
        r = self.endpoints_table.rowCount()
        self.endpoints_table.insertRow(r)
        self.endpoints_table.setItem(r, 0, QTableWidgetItem(path))
        self.endpoints_table.setItem(r, 1, QTableWidgetItem(methods))
        rows += 1

    # Select first row for convenience
    if rows:
        try:
            self.endpoints_table.setRangeSelected(
                QTableWidgetSelectionRange(0, 0, 0, 1), True
            )
        except Exception:
            pass


def on_endpoint_selected(self, row, col):
    ep = self.endpoints_table.item(row, 0).text()
    cfg = getattr(self, "config_cache", {}).get(ep, {})

    # restore override method
    if 'method' in cfg and hasattr(self, "method_box") and self.method_box:
        self.method_box.setCurrentText(str(cfg['method']).upper())

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

def methodComboInit(self, layout):
    # Only create if not already made by _build_ui
    if not hasattr(self, "method_box") or self.method_box is None:
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Override Method:"))
        self.method_box = QComboBox()
        self.method_box.addItems(["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
        method_row.addWidget(self.method_box)
        layout.addLayout(method_row)
    else:
        # Ensure these at minimum
        have = {self.method_box.itemText(i) for i in range(self.method_box.count())}
        for m in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            if m not in have:
                self.method_box.addItem(m)
