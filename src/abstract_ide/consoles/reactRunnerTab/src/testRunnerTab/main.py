import os, json, subprocess,glob
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QListWidget,
    QTabWidget, QLineEdit, QLabel, QFormLayout, QScrollArea, QListWidgetItem
    
)
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from ..imports import *
import re, os, glob, json, subprocess
from .initFuncs import initFuncs
ROOT = "/var/www/presites/thedailydialectics/react/main"
INSPECT_MJS = "/var/www/modules/packages/inspect-dts.mjs"  # expects to print JSON: [{name, params:[{name,type},...]}, ...]

def _node_ok():
    try:
        r = subprocess.run(["node", "-v"], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False

def _json_or_str(s: str):
    s = s.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return s
# optional regex fallback (works for simple cases of `export function foo(...)` or `export const foo = (...) =>`)
_export_fn_re = re.compile(
    r"""
    ^\s*export\s+
    (?:
      (?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\) |
      const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=> 
    )
    """,
    re.M | re.X,
)

class testRunnerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Abstract Packages Explorer")

        # ---- state ----
        self.init_path = ROOT
        self.current_pkg: str | None = None
        self.current_fn: str | None = None
        self.arg_edits: list[QLineEdit] = []

        # ========== FRAME ==========
        frame = QVBoxLayout(self)  # <<< vertical: top bar, then content

        # ---------- TOP BAR ----------
        top_bar = QHBoxLayout()

        self.mode_cb = QComboBox()
        self.mode_cb.addItems(["Packages", "Functions folder", "React project"])
        self.mode_cb.currentIndexChanged.connect(self.reload_all)
        self.mode_cb.currentIndexChanged.connect(self._update_topbar_visibility)

        self.func_subdir_in = QLineEdit("src/lib")  # or "src/functions" if that's your common case
        self.func_subdir_in.setPlaceholderText("React functions subdir (e.g. src/functions)")
        self.func_subdir_in.editingFinished.connect(self.reload_all)

        self.path_in = make_path_input(
            init_value=getattr(self, "init_path", ""),
            parent=self,
            validate=require_package_json,  # or None if your ROOT doesn't always contain package.json
            user_only=True,
        )
        add_fs_completer(self.path_in)

        self.btn_rescan = QPushButton("Rescan")
        self.btn_rescan.clicked.connect(self.reload_all)

        self.btn_tools = QPushButton("Install analyzers (babel/tsx)")
        self.btn_tools.clicked.connect(self._install_analyzers)

        # compose the row: [Mode][Subdir][Path][Rescan][Install]  ...stretch...
        top_bar.addWidget(QLabel("Mode:"))
        top_bar.addWidget(self.mode_cb, 0)
        top_bar.addWidget(self.func_subdir_in, 0)
        top_bar.addSpacing(8)
        top_bar.addWidget(QLabel("Base path:"))
        top_bar.addWidget(self.path_in, 1)
        top_bar.addWidget(self.btn_rescan, 0)
        top_bar.addWidget(self.btn_tools, 0)
        top_bar.addStretch(1)

        frame.addLayout(top_bar)  # <<< top row across full width

        # ---------- CONTENT (split) ----------
        split = QSplitter(Qt.Orientation.Horizontal)

        # left panel: tabs
        left_panel = QWidget()
        left_v = QVBoxLayout(left_panel)
        self.tabs = QTabWidget()
        left_v.addWidget(self.tabs, 1)

        # right panel: inputs + log
        right_panel = QWidget()
        right_v = QVBoxLayout(right_panel)

        self.input_form = QFormLayout()
        self.input_widget = QWidget()
        self.input_widget.setLayout(self.input_form)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.input_widget)
        right_v.addWidget(scroll, 2)

        self.raw_args = QLineEdit()
        self.raw_args.setPlaceholderText('Optional raw JSON args array, e.g. ["foo", 123, {"a":1}]')
        right_v.addWidget(self.raw_args)

        self.btn_run = QPushButton("Run Selected Function")
        self.btn_run.clicked.connect(self.run_function)
        right_v.addWidget(self.btn_run)

        self.open_dir = QPushButton("Open Packages Dir")
        self.open_dir.clicked.connect(self.open_item)
        right_v.addWidget(self.open_dir)

        self.open_fn_btn = QPushButton("Open Function File")
        self.open_fn_btn.clicked.connect(self.open_function_file)
        right_v.addWidget(self.open_fn_btn)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        right_v.addWidget(self.log, 3)

        # add both panels to splitter
        split.addWidget(left_panel)
        split.addWidget(right_panel)
        split.setStretchFactor(0, 1)  # left
        split.setStretchFactor(1, 2)  # right

        frame.addWidget(split, 1)  # <<< main area under the top bar

        if not _node_ok():
            self.log.append("❌ Node.js not found on PATH. Introspection and execution will fail.")

        # show/hide React subdir field depending on mode
        self._update_topbar_visibility()
        self.reload_all()

testRunnerTab = initFuncs(testRunnerTab)
