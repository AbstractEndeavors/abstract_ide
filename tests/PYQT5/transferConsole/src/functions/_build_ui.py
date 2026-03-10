from __future__ import annotations
import enum
from ..imports import *
import inspect
import PyQt6
from PyQt6 import QtWidgets,QtCore
import inspect



def _build_ui(self):
        self.setWindowTitle("24T Transfer Tool")
        self.resize(800, 500)

        self.sources = []

        layout = QVBoxLayout(self)

        # Source selection
        src_layout = QHBoxLayout()
        self.src_label = QLabel("No files selected")
        btn_files = QPushButton("Add Files")
        btn_dirs = QPushButton("Add Folder")

        btn_files.clicked.connect(self.add_files)
        btn_dirs.clicked.connect(self.add_dir)

        src_layout.addWidget(btn_files)
        src_layout.addWidget(btn_dirs)
        src_layout.addWidget(self.src_label)

        # Destination
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel("Remote subdir:"))
        self.dest_input = QLineEdit("backups")
        dest_layout.addWidget(self.dest_input)

        # Output
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        # Transfer
        self.btn_start = QPushButton("Start Transfer")
        self.btn_start.clicked.connect(self.start_transfer)

        layout.addLayout(src_layout)
        layout.addLayout(dest_layout)
        layout.addWidget(self.output)
        layout.addWidget(self.btn_start)
