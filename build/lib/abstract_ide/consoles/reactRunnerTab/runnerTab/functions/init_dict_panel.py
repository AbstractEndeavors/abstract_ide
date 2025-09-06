from ..imports import *
def _update_dict_preview(self, item):
        # show the dict of the highlighted row
        ['msg','vars']
        if not item:
            self.dict_view.clear()
            return
        data = item.data(0, QtCore.Qt.ItemDataRole.UserRole) or {}
            # children store {'role':'child','entry': <dict>}; parents store {'role':'parent','path':..., 'entries':[dict,...]}
        payload = data.get('entry', data)
        entries = make_list(payload.get('entries',payload))
        string = ""
        for i,entry in enumerate(entries):
            path = entry.get('path')
            if string == "":
                string+=f"path == {path}\n"
            string+=f"entry {i}:\n"
            variables = entry.get('vars')
            message = entry.get('msg')
            string+=f"vars == {variables}\n"
            string+=f"msg == {message}\n"


        self.dict_view.setPlainText(string)

def init_dict_panel_creation(self):
    dict_panel = QtWidgets.QWidget(self)
    dict_row   = QtWidgets.QHBoxLayout(dict_panel)
    self.dict_view = QtWidgets.QPlainTextEdit()
    self.dict_view.setReadOnly(True)
    self.dict_view.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
    self.dict_view.setMinimumHeight(120)
    # keep it short by default (grows only if you drag the splitter)
    self.dict_view.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                 QtWidgets.QSizePolicy.Policy.Preferred)
    mono = self.dict_view.font(); mono.setFamily("monospace"); self.dict_view.setFont(mono)
    dict_row.addWidget(self.dict_view)   # <- addWidget, not addLayout
    # connect once after trees are created:
    for t in (self.errors_tree, self.warnings_tree, self.all_tree):
        t.currentItemChanged.connect(lambda cur, prev: self._update_dict_preview(cur))
        t.itemClicked.connect(lambda it, col: self._update_dict_preview(it))
    
    return dict_panel
