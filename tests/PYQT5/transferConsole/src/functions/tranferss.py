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
