from ..imports import *
# Call this whenever you refresh issues:
def update_issues(self, errors_rows, warnings_rows,all_rows):
    """
    errors_rows / warnings_rows formats accepted:
      - ["file or issue", "line", "msg"]
      - or grouped: [[topCols...], [child1...], [child2...], ...]
    """
    self._fill_tree(self.errors_tree, errors_rows)
    self._fill_tree(self.warnings_tree, warnings_rows)
    self._fill_tree(self.all_tree, all_rows)
    # keep “All” page in sync
    self._fill_tree(self.errors_tree_all, errors_rows)
    self._fill_tree(self.warnings_tree_all, warnings_rows)
    self._fill_tree(self.all_tree_all, all_rows)
def init_set_buttons(self,tree_stack):
    self.rb_err.toggled.connect(lambda on: on and tree_stack.setCurrentIndex(0))
    self.rb_wrn.toggled.connect(lambda on: on and tree_stack.setCurrentIndex(1))
    self.rb_all.toggled.connect(lambda on: on and tree_stack.setCurrentIndex(2))

    # Initial page
    if getattr(self.rb_err, "isChecked", lambda: False)():
        tree_stack.setCurrentIndex(0)
    elif getattr(self.rb_wrn, "isChecked", lambda: False)():
        tree_stack.setCurrentIndex(1)
    else:
        tree_stack.setCurrentIndex(2)
def init_tree_creation(self,layout=None):
    if layout is None:
        layout = QStackedWidget(self)
    # Primary trees (used by Errors page and Warnings page)
    # If initializeInit already created them, keep yours. Otherwise create here:
    if not hasattr(self, "errors_tree"):
        self.errors_tree = QTreeWidget()
        self.errors_tree.setHeaderLabels(["File / Issue", "Line", "Msg"])
    if not hasattr(self, "warnings_tree"):
        self.warnings_tree = QTreeWidget()
        self.warnings_tree.setHeaderLabels(["File / Issue", "Line", "Msg"])
    if not hasattr(self, "all_tree"):
        self.all_tree = QTreeWidget()
        self.all_tree.setHeaderLabels(["File / Issue", "Line", "Msg"])
    self.setup_issue_tree(self.errors_tree)
    self.setup_issue_tree(self.warnings_tree)
    self.setup_issue_tree(self.all_tree)
    
    # Page 0: Errors
    p_err = QWidget(); l_err = QVBoxLayout(p_err)
    l_err.addWidget(QLabel("Errors (grouped by file):"))
    l_err.addWidget(self.errors_tree)
    layout.addWidget(p_err)

    # Page 1: Warnings
    p_wrn = QWidget(); l_wrn = QVBoxLayout(p_wrn)
    l_wrn.addWidget(QLabel("Warnings (grouped by file):"))
    l_wrn.addWidget(self.warnings_tree)
    layout.addWidget(p_wrn)

            # Page 1: Warnings
    p_all = QWidget(); l_all = QVBoxLayout(p_all)
    l_all.addWidget(QLabel("all Entries (grouped by file):"))
    l_all.addWidget(self.all_tree)
    layout.addWidget(p_all)

    # Page 2: All (use separate trees to avoid reparenting)
    self.errors_tree_all = QTreeWidget();  self.errors_tree_all.setHeaderLabels(["File / Issue", "Line", "Msg"])
    self.warnings_tree_all = QTreeWidget(); self.warnings_tree_all.setHeaderLabels(["File / Issue", "Line", "Msg"])
    self.all_tree_all = QTreeWidget(); self.warnings_tree_all.setHeaderLabels(["File / Issue", "Line", "Msg"])
    self.setup_issue_tree(self.errors_tree_all)
    self.setup_issue_tree(self.warnings_tree_all)
    self.setup_issue_tree(self.all_tree_all)

    # Expose a simple API you can call after parsing output:

    self._setup_issue_tree = self.setup_issue_tree
    return layout
