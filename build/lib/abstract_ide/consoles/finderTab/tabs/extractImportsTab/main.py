from ..imports import *
from .initFuncs import initFuncs
# ---------------- Worker ----------------

# ------------- The Tab ------------------
class extractImportsTab(QWidget):
    def __init__(self, bus: SharedStateBus):
        super().__init__()
        self.setLayout(QVBoxLayout())

        grid = QGridLayout()
        install_common_inputs(
            self, grid, bus=bus,
            primary_btn=("Extract Imports", self.start_extract),
            secondary_btn=("Copy Imports", self._copy_imports),  # wired below
            default_allowed_exts_in=".py",
            default_unallowed_exts_in=".pyc",
            default_exclude_types_in="compression",
            default_exclude_dirs_in=["__init__", "node_modules"]
        )

        # ---------- FILES (module paths) ----------
        self.layout().addWidget(QLabel("Files"))
        self.module_paths = QListWidget()
        self.module_paths.setUniformItemSizes(True)
        self.module_paths.setSelectionMode(self.module_paths.SelectionMode.ExtendedSelection)
        self.module_paths.itemDoubleClicked.connect(self._open_selected_module_path)
        self.layout().addWidget(self.module_paths, stretch=3)

        # ---------- IMPORTS header + Copy ----------
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Imports"))
        hdr.addStretch(1)
        self.copy_btn = QPushButton("Copy")
        hdr.addWidget(self.copy_btn)
        self.copy_btn.clicked.connect(self._copy_imports)
        self.layout().addLayout(hdr)

        # ---------- IMPORTS as wrapped “chips” ----------
        self.modules_list = QListWidget()
        self.modules_list.setSelectionMode(self.modules_list.SelectionMode.ExtendedSelection)
        self.modules_list.setViewMode(QListView.ViewMode.IconMode)  # horizontal flow
        self.modules_list.setWrapping(True)
        self.modules_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.modules_list.setMovement(QListView.Movement.Static)
        self.modules_list.setSpacing(6)
        # optional: make items compact and readable
        fm = self.fontMetrics()
        self.modules_list.setIconSize(QSize(1, fm.height() + 8))  # tiny “icon” height to get nicer grid rows
        self.layout().addWidget(self.modules_list, stretch=2)

        # selection → filter files that contain the import
        self.modules_list.itemSelectionChanged.connect(self._on_import_selection_changed)

        # last results + index
        self._last_module_paths: list[str] = []
        self._last_imports: list[str] = []
        self._import_to_files: dict[str, list[str]] = {}



extractImportsTab = initFuncs(extractImportsTab)
