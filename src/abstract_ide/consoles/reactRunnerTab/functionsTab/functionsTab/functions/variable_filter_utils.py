from ..imports import *
def _on_variable_clicked(self, var_name: str):
    self.current_var = var_name
    self.variableSelected.emit(var_name)
    self._render_var_lists_for(var_name)
    
# --- shared helpers -----------------------------------------------------------
def _render_var_lists_for(self, var_name: str=None):
   var_name = var_name or self.current_var
   self._render_symbol_lists_for(var_name, self.var_map,
                             self.exporters_list, self.importers_list,
                             getattr(self, "var_filter_mode", "io"))
# --- variables: mirror functions with tiny wrapper(s) -------------------------
def _on_var_filter_mode_changed(self):
    self.var_filter_mode = "source" if self.rb_var_source.isChecked() else ("all" if self.rb_var_all.isChecked() else "io")
    if getattr(self, "current_var", None):
        self._render_var_lists_for(self.current_var)
        
def _add_var_button(self, name: str):
    btn = QPushButton(name)
    btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    btn.clicked.connect(lambda _, n=name: self._on_variable_clicked(n))
    self.var_layout.addWidget(btn)

def _clear_var_buttons(self):
    while self.var_layout.count():
        it = self.var_layout.takeAt(0)
        w = it.widget()
        if w: w.deleteLater()

def _rebuild_var_buttons(self, names_iterable):
    self._clear_var_buttons()
    names = sorted(n for n in names_iterable if n and n != '<reexport>')
    for name in names:
        self._add_var_button(name)

def _filter_var_buttons(self, text: str):
    t = (text or '').strip().lower()
    if not getattr(self, 'var_map', None):
        return
    if not t:
        self._rebuild_var_buttons(self.var_map.keys())
    else:
        match = [n for n in self.var_map.keys() if t in n.lower()]
        self._rebuild_var_buttons(match)
