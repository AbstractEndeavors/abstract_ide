from .imports import *
from .initFuncs import *
class FileSystemTree(QtWidgets.QWidget):
    """
    Left‐hand pane: file browser + “Copy Selected” button.
    """
    def __init__(self, log_widget=None, parent=None):
        super().__init__(parent)
        self.log_widget = get_log_widget()  # keep your shared log
        layout = get_layout(parent=self)

        # QFileSystemModel + QTreeView
        self.model = get_fs_model()

        self.tree = get_tree(model=self.model, hideColumns=True)

        # “Copy Selected” button
        text = "Copy Selected to Clipboard"
        copy_btn = get_push_button(text=text, action=self.copy_selected)

        add_widgets(
            layout,
            {"widget": self.tree},
            {"widget": copy_btn},
        )

        self.setLayout(layout)

FileSystemTree = initFuncs(FileSystemTree)

