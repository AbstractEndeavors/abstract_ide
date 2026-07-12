from ..imports import *
def _setup_menu(self) -> None:
    menu_bar = self.menuBar()

    file_menu = menu_bar.addMenu("&File")

    select_dir_action = QAction("Select Root Directory...", self)
    select_dir_action.triggered.connect(self._select_root_directory)
    file_menu.addAction(select_dir_action)

    file_menu.addSeparator()

    quit_action = QAction("Quit", self)
    quit_action.triggered.connect(self.close)
    file_menu.addAction(quit_action)

def _setup_shortcuts(self) -> None:
    save_action = QAction(self)
    save_action.setShortcut("Ctrl+S")
    save_action.triggered.connect(self._save_current_file)
    self.addAction(save_action)

def _connect_signals(self) -> None:
    self.tree_input.structure_submitted.connect(self._on_structure_submitted)
    self.file_browser.file_selected.connect(self._on_file_selected)
    self.editor.content_changed.connect(self._on_content_changed)
    self.editor.save_requested.connect(self._save_current_file)

def _select_root_directory(self) -> None:
    path = QFileDialog.getExistingDirectory(
        self,
        "Select Root Directory",
        str(self.config.root_path or Path.home()),
    )
    if path:
        self.config.root_path = Path(path)
        self.status_bar.showMessage(f"Root: {path}", 3000)

def _on_structure_submitted(self, text: str) -> None:
    if not self.config.root_path:
        self._select_root_directory()
        if not self.config.root_path:
            return

    nodes = self.parser.parse(text)
    if not nodes:
        QMessageBox.warning(self, "Parse Error", "Could not parse the structure.")
        return

    try:
        files = self.builder.build(self.config.root_path, nodes)
        self.file_browser.populate(self.config.root_path.name, files)
        self.editor.clear()
        self._current_file = None
        self.status_bar.showMessage(f"Created {len(files)} files", 3000)
    except Exception as e:
        QMessageBox.critical(self, "Build Error", str(e))

def _on_file_selected(self, relative_path: Path) -> None:
    entry = self.registry.get(relative_path)
    if entry:
        self._current_file = relative_path
        self.editor.set_file(relative_path, entry.content)

def _on_content_changed(self, content: str) -> None:
    if self._current_file:
        self.registry.update_content(self._current_file, content)

def _save_current_file(self) -> None:
    if not self._current_file:
        return

    entry = self.registry.get(self._current_file)
    if not entry:
        return

    try:
        content = self.editor.get_content()
        entry.absolute_path.write_text(content, encoding="utf-8")
        self.registry.mark_saved(self._current_file)
        self.status_bar.showMessage(f"Saved: {self._current_file}", 3000)
    except Exception as e:
        QMessageBox.critical(self, "Save Error", str(e))
