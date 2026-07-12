from ..imports import *
def _setup_ui(self) -> None:
    self.setWindowTitle("Scaffolding Tool")
    self.setMinimumSize(1000, 700)

    central = QWidget()
    self.setCentralWidget(central)
    main_layout = QVBoxLayout(central)

    self.tree_input = TreeInputPanel()

    splitter = QSplitter(Qt.Orientation.Horizontal)

    self.file_browser = FileBrowserPanel()
    self.file_browser.setMinimumWidth(250)

    self.editor = EditorPanel()

    splitter.addWidget(self.file_browser)
    splitter.addWidget(self.editor)
    splitter.setSizes([300, 700])

    main_layout.addWidget(self.tree_input)
    main_layout.addWidget(splitter, stretch=1)

    self.status_bar = QStatusBar()
    self.setStatusBar(self.status_bar)

    self._setup_menu()
    self._setup_shortcuts()
