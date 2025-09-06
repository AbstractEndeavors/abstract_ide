from ..imports import *
def get_fs_model(index=None, root_path=None, hideColumns=True):
    fs_model = QtGui.QFileSystemModel()   # ⬅ moved from QtWidgets
    fs_model.setRootPath(root_path or QtCore.QDir.rootPath())

    if hideColumns:
        # Hide size/type/date columns later when attaching to view
        pass

    if index is not None:
        fs_model.index(index)

    return fs_model


def get_tree(model=None, index=None, root_path=None, hideColumns=True, dragEnabled=True):
    tree = QtWidgets.QTreeView()
    model = model or get_fs_model(index=index, root_path=root_path, hideColumns=hideColumns)
    tree.setModel(model)

    # Multi-selection & drag from tree (Qt6 enum namespaces)
    tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
    tree.setDragEnabled(dragEnabled)
    tree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
    return tree
