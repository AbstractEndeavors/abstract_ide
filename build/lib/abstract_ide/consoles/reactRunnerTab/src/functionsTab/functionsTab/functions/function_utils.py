from ..imports import *
def _on_function_clicked(self, fn_name: str):
    self.current_fn = fn_name
    self.functionSelected.emit(fn_name)
    self._render_fn_lists_for(fn_name)
    
def _render_fn_lists_for(self, fn_name: str=None):
   fn_name = fn_name or self.current_fn
   self._render_symbol_lists_for(fn_name, self.func_map,
                             self.exporters_list, self.importers_list,
                             getattr(self, "fn_filter_mode", "io"))

def _on_fn_filter_mode_changed(self):
    self.fn_filter_mode = "source" if self.rb_fn_source.isChecked() else ("all" if self.rb_fn_all.isChecked() else "io")
    if self.current_fn:
        self._render_fn_lists_for(self.current_fn)
        
def _add_fn_button(self, name: str):
    btn = QPushButton(name)
    btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    btn.clicked.connect(lambda _, n=name: self._on_function_clicked(n))
    self.fn_layout.addWidget(btn)

def _clear_fn_buttons(self):
    while self.fn_layout.count():
        it = self.fn_layout.takeAt(0)
        w = it.widget()
        if w: w.deleteLater()

def _rebuild_fn_buttons(self, names_iterable):
    self._clear_fn_buttons()
    names = sorted(n for n in names_iterable if n and n != '<reexport>')
    for name in names:
        self._add_fn_button(name)

def _filter_fn_buttons(self, text: str):
    t = (text or '').strip().lower()
    if not self.func_map:
        return
    if not t:
        self._rebuild_fn_buttons(self.func_map.keys())
    else:
        match = [n for n in self.func_map.keys() if t in n.lower()]
        self._rebuild_fn_buttons(match)
def expandingDirections(self):
    # allow using extra horizontal space so items can wrap
    return Qt.Orientations(Qt.Orientation.Horizontal)
