from ..imports import *

def _normalize_map_entry(data) -> tuple[list[str], list[str]]:
    """
    Accepts either:
      - {'exported_in': [...], 'imported_in': [...]}
      - [ {exported_in: [...], imported_in: [...]}, 'path', ... ]
    Returns (exported_in, imported_in) with duplicates removed (order-stable).
    """
    exported_in, imported_in = [], []
    if isinstance(data, dict):
        exported_in = list(dict.fromkeys(data.get('exported_in', [])))
        imported_in = list(dict.fromkeys(data.get('imported_in', [])))
    elif isinstance(data, list):
        for d in data:
            if isinstance(d, dict):
                exported_in += d.get('exported_in', [])
                imported_in += d.get('imported_in', [])
            elif isinstance(d, str):
                exported_in.append(d); imported_in.append(d)
        exported_in = list(dict.fromkeys(exported_in))
        imported_in = list(dict.fromkeys(imported_in))
    return exported_in, imported_in

def _render_symbol_lists_for(self, name: str, mapping: dict,
                             exporters_widget, importers_widget,
                             mode: str = "io"):
    """
    Generic renderer for functions/variables.
    mode: "source" -> only exporters
          "io"     -> exporters + importers
          "all"    -> union shown in exporters_widget
    """
    exporters_widget.clear()
    if importers_widget is not None:
        importers_widget.clear()

    data = mapping.get(name, {'exported_in': [], 'imported_in': []})
    exported_in, imported_in = _normalize_map_entry(data)

    if mode == "source":
        for f in sorted(exported_in):
            exporters_widget.addItem(f)
    elif mode == "io":
        for f in sorted(exported_in):
            exporters_widget.addItem(f)
        if importers_widget is not None:
            for f in sorted(imported_in):
                importers_widget.addItem(f)
    else:  # "all"
        union = sorted(set(exported_in) | set(imported_in))
        for f in union:
            exporters_widget.addItem(f)

def _on_symbol_clicked(self, name: str, kind: str):
    if kind in {'const','let','var'}:
        return self._on_variable_clicked(name)
    else:
        return self._on_function_clicked(name)
    
def _on_filter_mode_changed(self):
    self.fn_filter_mode = "source" if self.rb_fn_source.isChecked() else ("all" if self.rb_fn_all.isChecked() else "io")
    if self.current_fn:
        self._render_fn_lists_for(self.current_fn)

    self.var_filter_mode = "source" if self.rb_var_source.isChecked() else ("all" if self.rb_var_all.isChecked() else "io")
    if self.current_var:
        self._render_var_lists_for(self.current_var)


def _start_func_scan(self, scope: str):
    try:
        path = self.path_in.text().strip()
        if not path or not os.path.isdir(path):
            QMessageBox.critical(self, "Error", "Invalid project path.")
            return
        self.appendLog(f"[map] starting scan ({scope})\n")

        # Fire the worker (now emits graph, func_map, var_map)
        worker = ImportGraphWorker(path, scope=scope, entries=["index","main"])
        self.map_worker = worker
        worker.log.connect(self.appendLog)
        worker.ready.connect(self._on_map_ready)
        worker.finished.connect(lambda: self.appendLog("[map] done.\n"))
        worker.start()
    except Exception:
        self.appendLog("start_func_scan error:\n" + traceback.format_exc() + "\n")

# functionsTab/functionsTab/functions/filter_utils.py
def _on_map_ready(self, graph: dict, func_map: dict, var_map: dict | None = None):
    self.graph   = graph or {}
    self.func_map = func_map or {}
    self.var_map  = var_map  or {}   # <-- new

    # functions
    self._rebuild_fn_buttons(sorted(self.func_map.keys()))
    if self.current_fn and self.current_fn in self.func_map:
        self._render_fn_lists_for(self.current_fn)
    elif self.func_map:
        self._on_function_clicked(sorted(self.func_map.keys())[0])

    self._rebuild_var_buttons(sorted(self.var_map.keys()))
    if self.current_var and self.current_var in self.var_map:
        self._render_var_lists_for(self.current_var)
    elif self.var_map:
        self._on_variable_clicked(sorted(self.var_map.keys())[0])

    self.appendLog(f"[map] UI updated: {len(self.func_map)} functions, {len(self.var_map)} variables\n")
    
def create_radio_group(self, labels, default_index=0, slot=None):
        """
        Create a QButtonGroup with QRadioButtons for the given labels.

        Args:
            self: parent widget (e.g. 'self' inside a class)
            labels (list[str]): button labels
            default_index (int): which button to check by default
            slot (callable): function to connect all toggled signals to
        Returns:
            (QButtonGroup, list[QRadioButton])
        """
        group = QButtonGroup(self)
        buttons = []

        for i, label in enumerate(labels):
            rb = QRadioButton(label)
            if i == default_index:
                rb.setChecked(True)
            group.addButton(rb)
            buttons.append(rb)
            if slot:
                rb.toggled.connect(slot)

        return group, buttons
