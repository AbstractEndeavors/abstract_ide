from ..imports import *
from .initFuncs import initFuncs
# New Tab: Directory Map

class directoryMapTab(QWidget):
    def __init__(self, bus: SharedStateBus):
        super().__init__()
        self.setLayout(QVBoxLayout())
        grid = QGridLayout()
        self.btn_copy_sel = QPushButton("Copy Selected")
        self.btn_copy_all = QPushButton("Copy All")
        self.btn_save_map  = QPushButton("Save…")
        install_common_inputs(
            self, grid, bus=bus,
            primary_btn=("Generate Map", self.start_map),
            secondary_btn=("Copy Map", (lambda: copy_map(self, only_selected=False))),
            trinary_btn=("Save Map", (lambda: save_map_to_file(self)))
            
            
        )

        # Prefix + flags (unchanged)
        self.prefix_in = QLineEdit("")
        self.prefix_in.setPlaceholderText("Optional prefix")
        self.chk_recursive = QCheckBox("Recursive"); self.chk_recursive.setChecked(True)
        self.chk_include_files = QCheckBox("Include Files"); self.chk_include_files.setChecked(True)
        self.chk_add = QCheckBox("Add to defaults"); self.chk_add.setChecked(False)

        self.btn_run = QPushButton("Get Directory Map")
        self.btn_run.clicked.connect(self.start_map)

        # Results
        self.layout().addWidget(QLabel("Results"))
        self.list = QListWidget()
        # (optional) double-click to copy selected line
        # self.list.itemDoubleClicked.connect(lambda _: copy_map(self, only_selected=True))
        self.list.itemDoubleClicked.connect(self.start_map)  # keep your original behavior
        self.layout().addWidget(self.list, stretch=3)

        # Make the map monospaced
        f = self.list.font()
        f.setStyleHint(QFont.StyleHint.TypeWriter)
        self.list.setFont(f)

        # ↓↓↓ add the copy/save UI + shortcuts + context menu
        self.wire_map_copy_ui()

        self._last_results = []

directoryMapTab = initFuncs(directoryMapTab)
