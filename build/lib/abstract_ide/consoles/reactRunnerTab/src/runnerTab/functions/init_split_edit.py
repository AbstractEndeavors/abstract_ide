from ..imports import *
def init_vertical_split_creation(self,*widgets):
    stack_split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self)
    for widget in widgets:
        stack_split.addWidget(widget)     # your left panel QWidget
    # optional: make the bottom get most of the space
    stack_split.setStretchFactor(0, 0)
    stack_split.setStretchFactor(1, 1)
    # optional: allow collapsing the preview if the user drags it shut
    stack_split.setChildrenCollapsible(True)
    return stack_split
def init_horizontal_split(self,*widgets):
    content_split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self)
    for widget in widgets:
        content_split.addWidget(widget)     # your left panel QWidget
    content_split.setStretchFactor(0, 1)
    content_split.setStretchFactor(1, 2)
    return content_split
def init_text_editor_creation(self):
    right_panel = QWidget(); right_lay = QVBoxLayout(right_panel)
    editor_hdr = QHBoxLayout()
    editor_hdr.addWidget(QLabel("Editor:")); editor_hdr.addStretch(1)
    editor_hdr.addWidget(self.btn_revert); editor_hdr.addWidget(self.btn_save)
    right_lay.addLayout(editor_hdr)
    right_lay.addWidget(self.editor, 1)   # editor fills remaining space
    return right_panel
def init_view_row_create(self):
    view_row = QHBoxLayout()
    view_row.addWidget(QLabel("View:")); view_row.addStretch(1)
    view_row.addWidget(self.rb_all); view_row.addWidget(self.rb_err); view_row.addWidget(self.rb_wrn)
    view_row.addWidget(self.cb_try_alt_ext)
    return view_row
def init_top_row_create(self):
    top = QHBoxLayout()
    top.addWidget(QLabel("User:")); top.addWidget(self.user_in, 2)
    top.addWidget(QLabel("Path:")); top.addWidget(self.path_in, 3)
    top.addWidget(self.run_btn); top.addWidget(self.rerun_btn); top.addWidget(self.clear_btn)
    return top

