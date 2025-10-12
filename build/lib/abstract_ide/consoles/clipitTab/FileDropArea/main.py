from .imports import *
from abstract_utilities import get_media_exts, eatOuter
from .initFuncs import initFuncs
logger = get_logFile('clipit_logs')

class FileDropArea(QtWidgets.QWidget):
    function_selected = QtCore.pyqtSignal(dict)
    file_selected = QtCore.pyqtSignal(dict)

    def __init__(self, log_widget=None, view_widget=None, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.log_widget = log_widget
        self.view_widget = view_widget
        self.dir_pieces = []
        self.ext_checks: dict[str, QtWidgets.QCheckBox] = {}
        self.dir_checks: dict[str, QtWidgets.QCheckBox] = {}
        self._last_raw_paths: list[str] = []
        self.functions: list[dict] = []
        self.python_files: list[dict] = []
        
        self.allowed_exts = DEFAULT_ALLOWED_EXTS
        self.unallowed_exts = DEFAULT_UNALLOWED_EXTS
        self.exclude_types = DEFAULT_EXCLUDE_TYPES
        self.exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | {"backup", "backups"}
        self.exclude_patterns = set(DEFAULT_EXCLUDE_PATTERNS)
        self.user_exclude_dirs = set()  # ← if you need user additions, keep them separate

        # Main vertical layout
        lay = QtWidgets.QVBoxLayout(self)
        # 1) “Browse Files…” button
        browse_btn = get_push_button(text="Browse Files…", action=self.browse_files)
        self.view_toggle = 'array'
        self.view_widget = 'print'   # lossless by default
        # 2) Extension-filter row
        self.ext_row = QtWidgets.QScrollArea(widgetResizable=True)
        self.ext_row.setFixedHeight(45)
        self.ext_row.setVisible(False)
        self.ext_row_w = QtWidgets.QWidget()
        self.ext_row.setWidget(self.ext_row_w)
        self.ext_row_lay = QtWidgets.QHBoxLayout(self.ext_row_w)
        self.ext_row_lay.setContentsMargins(4, 4, 4, 4)
        self.ext_row_lay.setSpacing(10)
        self._selected_text: dict[str, str] = {}

        # 3) Directory-filter row (new)
        # 3) Directory-filter row (checkboxes)
        self.dir_row = QtWidgets.QScrollArea(widgetResizable=True)
        self.dir_row.setFixedHeight(45)
        self.dir_row.setVisible(False)
        self.dir_row_w = QtWidgets.QWidget()
        self.dir_row.setWidget(self.dir_row_w)
        self.dir_row_lay = QtWidgets.QHBoxLayout(self.dir_row_w)
        self.dir_row_lay.setContentsMargins(4, 4, 4, 4)
        self.dir_row_lay.setSpacing(10)



        # 4) Tab widget to switch between “List View” and “Text View”
        self.view_tabs = QtWidgets.QTabWidget()

        # List View Tab
        list_tab = QtWidgets.QWidget()
        list_layout = get_layout(parent=list_tab)
        self.function_list = QtWidgets.QListWidget()
        self.function_list.setVisible(False)
        self.function_list.setAcceptDrops(False)
        self.function_list.itemClicked.connect(self.on_function_clicked)
        self.python_file_list = QtWidgets.QListWidget()
        self.python_file_list.setVisible(False)
        self.python_file_list.setAcceptDrops(False)
        self.python_file_list.itemClicked.connect(self.on_python_file_clicked)
        add_widgets(list_layout, {"widget": self.python_file_list}, {"widget": self.function_list})
        self.view_tabs.addTab(list_tab, "List View")

        # Text View Tab
        text_tab = QtWidgets.QWidget()
        text_layout = QtWidgets.QVBoxLayout(text_tab)
        self.text_view = QtWidgets.QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setVisible(False)
        self.text_view.setAcceptDrops(False)
        add_widgets(text_layout, {"widget": self.text_view})
        self.view_tabs.addTab(text_tab, "Text View")

        # 5) Status label
        self.status = QtWidgets.QLabel("No files selected.")
        self.status.setStyleSheet("color: #333; font-size: 12px;")
        self.status.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        add_widgets(
            lay,
            {"widget": browse_btn, "kwargs": {"alignment": QtCore.Qt.AlignmentFlag.AlignHCenter}},
            {"widget": self.dir_row},
            {"widget": self.ext_row},
            {"widget": self.view_tabs},
            {"widget": self.status},
        )
        # Initialize dir patterns from input
        self._update_dir_patterns()

FileDropArea = initFuncs(FileDropArea)
