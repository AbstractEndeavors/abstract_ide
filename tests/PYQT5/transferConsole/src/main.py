from .imports import *
class transferConsole(QWidget):
    def __init__(self):
        super().__init__()
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

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        if files:
            self.sources.extend(files)
            self.update_label()

    def add_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select folder")
        if directory:
            self.sources.append(directory + "/")
            self.update_label()

    def update_label(self):
        self.src_label.setText(f"{len(self.sources)} item(s) selected")

    def start_transfer(self):
        if not self.sources:
            self.output.append("No sources selected.\n")
            return

        remote_path = f"{REMOTE_BASE}/{self.dest_input.text().strip()}"
        self.output.append(f"Target: {remote_path}\n")

        self.worker = RsyncWorker(self.sources, remote_path)
        self.worker.output.connect(self.output.append)
        self.worker.finished.connect(self.transfer_done)

        self.btn_start.setEnabled(False)
        self.worker.start()

    def transfer_done(self, code):
        self.output.append(f"\nFinished with exit code {code}\n")
        self.btn_start.setEnabled(True)

    def start():
        startConsole(transferConsole)
