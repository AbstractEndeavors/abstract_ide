from ..imports import *
import subprocess, traceback, os
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

def build_group_tree(self):
    """
    Create a grouped QTreeWidget. Population is done later by show_error_entries / show_warning_entries.
    """
    tree = QTreeWidget()
    tree.setColumnCount(2)
    tree.setHeaderLabels(["File / Issue", "Details"])
    tree.setUniformRowHeights(True)
    tree.setRootIsDecorated(True)
    # connect to the unified tree-item handler
    tree.itemClicked.connect(self.on_tree_item_clicked)
    return tree
