from ..imports import *
def get_tabs_attr(self):
    return get_set_attr(parent=self,
                    attr_name='tabs',
                    valueFunc=QTabWidget
                    )
       
    
def init_functions_button_tab(self):
    get_tabs_attr(self)
    # --- Functions tab
    self.fn_tab = QWidget(); fn_v = QVBoxLayout(self.fn_tab)

    self.search_fn = QLineEdit(); self.search_fn.setPlaceholderText("Filter functions…")
    fn_v.addWidget(self.search_fn)

    self.rb_fn_source = QRadioButton("Function")
    self.rb_fn_io     = QRadioButton("Import/Export"); self.rb_fn_io.setChecked(True)
    self.rb_fn_all    = QRadioButton("All")
    self.fn_filter_group = QButtonGroup(self)
    for rb in (self.rb_fn_source, self.rb_fn_io, self.rb_fn_all):
        self.fn_filter_group.addButton(rb); fn_v.addWidget(rb)

    self.fn_scroll = QScrollArea(); self.fn_scroll.setWidgetResizable(True)
    self.fn_container = QWidget()
    if self.use_flow:
        self.fn_layout = flowLayout(self.fn_container, hspacing=8, vspacing=6)
        self.fn_container.setLayout(self.fn_layout)
    else:
        box = QVBoxLayout(self.fn_container)
        box.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.fn_layout = box
    self.fn_scroll.setWidget(self.fn_container)
    fn_v.addWidget(self.fn_scroll)
    self.tabs.addTab(self.fn_tab,  "Functions")
    return fn_v
def init_variables_button_tab(self):
    # --- Variables tab
    get_tabs_attr(self)
    self.var_tab = QWidget(); var_v = QVBoxLayout(self.var_tab)

    self.search_var = QLineEdit(); self.search_var.setPlaceholderText("Filter variables…")
    var_v.addWidget(self.search_var)

    self.rb_var_source = QRadioButton("Variable")
    self.rb_var_io     = QRadioButton("Import/Export"); self.rb_var_io.setChecked(True)
    self.rb_var_all    = QRadioButton("All")
    self.var_filter_group = QButtonGroup(self)
    for rb in (self.rb_var_source, self.rb_var_io, self.rb_var_all):
        self.var_filter_group.addButton(rb); var_v.addWidget(rb)

    self.var_scroll = QScrollArea(); self.var_scroll.setWidgetResizable(True)
    self.var_container = QWidget()
    if self.use_flow:
        self.var_layout = flowLayout(self.var_container, hspacing=8, vspacing=6)
        self.var_container.setLayout(self.var_layout)
    else:
        vbox = QVBoxLayout(self.var_container)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.var_layout = vbox
    self.var_scroll.setWidget(self.var_container)
    var_v.addWidget(self.var_scroll)
    self.tabs.addTab(self.var_tab, "Variables")
    return var_v




