from PyQt6 import QtCore
from PyQt6.QtWidgets import QToolButton,QHBoxLayout,QSpinBox,QGridLayout,QWidget,QCheckBox,QLineEdit,QPushButton,QLabel
from PyQt6.QtCore import QSignalBlocker
from ..imports import *

from PyQt6.QtCore import QObject, pyqtSignal
from .results import *
from .states import *
from .open_file_funcs import *
from abstract_utilities.file_utils import (derive_file_defaults)

from .visibility import *
logger = get_logFile(__name__)
_read_state = read_state
_write_state = write_state
def normalize_filter_value(v):
    if v is None or v is False:
        return ""
    if isinstance(v, (set, list, tuple)):
        return ",".join(sorted(str(x) for x in v))
    return str(v)

class SharedStateBus(QObject):
    stateBroadcast = pyqtSignal(object, dict)  # (sender, state)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._snap: dict = {}

    def snapshot(self) -> dict:
        return dict(self._snap)

    def push(self, sender, state: dict):
        self._snap = dict(state)
        self.stateBroadcast.emit(sender, self.snapshot())
def getContentComponentDefaults(
        host,
        *args,
        primary_btn=None,
        secondary_btn=None,
        trinary_btn=None,
        **kwargs
    ):
    DEFAULT_SECONDARY_BUTTON=("blank", None) 
    DEFAULT_PRIMARY_BUTTON = ("Run", None)
    DEFAULT_TRINARY_BUTTON = ("open all hits", host.open_all_hits)
    host.primary_btn=primary_btn or DEFAULT_PRIMARY_BUTTON
    host.secondary_btn=secondary_btn or  DEFAULT_SECONDARY_BUTTON
    host.trinary_btn = trinary_btn or  DEFAULT_TRINARY_BUTTON
    file_defaults = derive_file_defaults(**kwargs)
    logger.info(file_defaults)
    host.allowed_exts_in   = QLineEdit(normalize_filter_value(file_defaults.get('allowed_exts')))
    host.exclude_exts_in = host.unallowed_exts_in =QLineEdit(normalize_filter_value(file_defaults.get('exclude_exts')))
    host.allowed_types_in  = QLineEdit(normalize_filter_value(file_defaults.get('allowed_types')))
    host.exclude_types_in  = QLineEdit(normalize_filter_value(file_defaults.get('exclude_types')))
    host.allowed_dirs_in   = QLineEdit(normalize_filter_value(file_defaults.get('allowed_dirs')))
    host.exclude_dirs_in   = QLineEdit(normalize_filter_value(file_defaults.get('exclude_dirs')))
    host.allowed_patterns_in = QLineEdit(normalize_filter_value(file_defaults.get('allowed_patterns')))
    host.exclude_patterns_in = QLineEdit(normalize_filter_value(file_defaults.get('exclude_patterns')))

    host.chk_add        = QCheckBox("Add");          host.chk_add.setChecked(False)
    host.chk_recursive  = QCheckBox("Recursive");    host.chk_recursive.setChecked(True)
    host.chk_total      = QCheckBox("Require ALL strings (total_strings)")
    host.chk_total.setChecked(False)
    host.chk_parse      = QCheckBox("parse_lines");  host.chk_parse.setChecked(False)
    host.chk_getlines   = QCheckBox("get_lines");    host.chk_getlines.setChecked(True)

    host.spec_spin = QSpinBox(); host.spec_spin.setRange(0, 999999); host.spec_spin.setValue(0)
    global_default_filters = dict(
                **file_defaults,
                add=host.chk_add 
            )
    return global_default_filters
def createLayoutForm(host):
    r = 0
    host._input_grid.addWidget(QLabel("Directory"), r, 0); host._input_grid.addWidget(host.dir_in, r, 1); host._input_grid.addWidget(host.btn_browse, r, 2); r+=1
    host._input_grid.addWidget(QLabel("Strings"), r, 0); host._input_grid.addWidget(host.strings_in, r, 1, 1, 2); r+=1
    host._input_grid.addWidget(QLabel("Allowed Exts"), r, 0); host._input_grid.addWidget(host.allowed_exts_in, r, 1, 1, 2); r+=1
    host._input_grid.addWidget(QLabel("Exclude Exts"), r, 0); host._input_grid.addWidget(host.exclude_exts_in, r, 1, 1, 2); r+=1
    host._input_grid.addWidget(QLabel("Allowed Types"), r, 0); host._input_grid.addWidget(host.allowed_types_in, r, 1, 1, 2); r+=1
    host._input_grid.addWidget(QLabel("Exclude Types"), r, 0); host._input_grid.addWidget(host.exclude_types_in, r, 1, 1, 2); r+=1
    host._input_grid.addWidget(QLabel("Allowed Dirs"), r, 0); host._input_grid.addWidget(host.allowed_dirs_in, r, 1, 1, 2); r+=1
    host._input_grid.addWidget(QLabel("Exclude Dirs"), r, 0); host._input_grid.addWidget(host.exclude_dirs_in, r, 1, 1, 2); r+=1
    host._input_grid.addWidget(QLabel("Allowed Patterns"), r, 0); host._input_grid.addWidget(host.allowed_patterns_in, r, 1, 1, 2); r+=1
    host._input_grid.addWidget(QLabel("Exclude Patterns"), r, 0); host._input_grid.addWidget(host.exclude_patterns_in, r, 1, 1, 2); r+=1

    flags = QHBoxLayout()
    for w in (host.chk_recursive, host.chk_total, host.chk_parse, host.chk_getlines, host.chk_add):
        flags.addWidget(w)
    host._input_grid.addLayout(flags, r, 0, 1, 3); r+=1

    sp = QHBoxLayout()
    sp.addWidget(QLabel("spec_line (0=off):")); sp.addWidget(host.spec_spin); sp.addStretch(1)
    host._input_grid.addLayout(sp, r, 0, 1, 3); r+=1

    host.layout().addWidget(host._input_container)
    # CTA row
    cta = QHBoxLayout()
    if host.primary_btn[1]:
        host.btn_run = QPushButton(host.primary_btn[0]); host.btn_run.clicked.connect(host.primary_btn[1])
        cta.addWidget(host.btn_run)
    cta.addStretch(1)
    if host.secondary_btn[1]:
        host.btn_secondary = QPushButton(host.secondary_btn[0]); host.btn_secondary.clicked.connect(host.secondary_btn[1])
        cta.addWidget(host.btn_secondary)
    if host.trinary_btn[1]:
        host.btn_third = QPushButton(host.trinary_btn[0]); host.btn_third.clicked.connect(host.trinary_btn[1])
        cta.addWidget(host.btn_third)
    host.layout().addLayout(cta)
def getSharedBus(
        host,
        bus: SharedStateBus,
        auto_unlink_on_init_if_diff=True,
        global_default_filters=None
    ):

    host._bus = bus
    host._applying_remote = False

    # --- propagate local → bus when linked
    def maybe_broadcast(*_):
        if not host.link_btn.isChecked() or host._applying_remote:
            return
        bus.push(host, _read_state(host))

    # connect all widgets to broadcast
    for w in (host.dir_in, host.strings_in,
              host.allowed_exts_in, host.exclude_exts_in,
              host.allowed_types_in, host.exclude_types_in,
              host.allowed_dirs_in, host.exclude_dirs_in,
              host.allowed_patterns_in, host.exclude_patterns_in):
        w.textEdited.connect(maybe_broadcast)

    for cb in (host.chk_add, host.chk_recursive, host.chk_total,
               host.chk_parse, host.chk_getlines):
        cb.toggled.connect(maybe_broadcast)

    host.spec_spin.valueChanged.connect(maybe_broadcast)

    # --- bus → host
    def apply_shared(sender, state):
        if sender is host or not host.link_btn.isChecked():
            return
        host._applying_remote = True
        _write_state(host, state)
        host._applying_remote = False

    bus.stateBroadcast.connect(apply_shared)

    # --- INITIAL SYNC
    current = _read_state(host)
    snap = bus.snapshot()

    if snap:
        # Already have shared state → sync with that
        host._applying_remote = True
        _write_state(host, snap)
        host._applying_remote = False
        return

    # First tab to attach → seed the bus
    bus.push(host, current)


def add_result_item(list_widget, file_path: str, line: int | None):
    text = f"{file_path}:{line}" if line is not None else file_path
    it = QListWidgetItem(text)
    it.setData(Qt.ItemDataRole.UserRole, {"file_path": file_path, "line": line})
    list_widget.addItem(it)
def setupLayout(host, grid=None):
    grid = grid or QGridLayout()
    host._input_grid = grid
    form_container = QWidget()
    form_container.setLayout(host._input_grid)
    host._input_container = form_container
    host.browse_dir = browse_dir
    host.make_params = make_params

    # bind editor openers so `self` is host
    host.open_one = MethodType(open_one, host)
    host.open_all_hits = MethodType(open_all_hits, host)

    # do not create or insert a list here; tabs manage their own `self.list`
    if hasattr(host, "list"):
        try:
            host.list.itemDoubleClicked.disconnect()
        except Exception:
            pass
        host.list.itemDoubleClicked.connect(host.open_one)
def install_common_inputs(host, grid: QGridLayout, *,
                          bus: SharedStateBus,
                          primary_btn=None,
                          secondary_btn=None,
                          trinary_btn=None,
                          default_dir_in=None,
                          default_allowed_exts_in=None,
                          default_exclude_exts_in=None,
                          default_allowed_types_in=None,
                          default_exclude_types_in=None,
                          default_allowed_dirs_in=None,
                          default_exclude_dirs_in=None,
                          default_allowed_patterns_in=None,
                          default_exclude_patterns_in=None,
                          # NEW:
                          auto_unlink_on_init_if_diff=True,
                          global_default_filters: dict | None = None):

    """
    Adds the shared controls to `host` and wires them to `bus`.
    Expects `host` to already have a QVBoxLayout() as its layout().
    """

    setupLayout(host,grid=grid)
    # --- widgets (your exact fields) -------------------------------------
    host.dir_in = QLineEdit(default_dir_in or os.getcwd())
    host.btn_browse = QPushButton("Browse…")
    host.btn_browse.clicked.connect(lambda: browse_dir(host))
    host._vis = visibilityMgr(host, settings_app="common_inputs", animate_default=True)
    host.strings_in = QLineEdit("")
    host.strings_in.setPlaceholderText("comma,separated,strings")
    
    global_default_filters = getContentComponentDefaults(
        host,
        primary_btn=primary_btn,
        secondary_btn=secondary_btn,
        trinary_btn=trinary_btn,
        allowed_exts=default_allowed_exts_in,
        exclude_exts=default_exclude_exts_in,
        allowed_types=default_allowed_types_in,
        exclude_types=default_exclude_types_in,
        allowed_dirs=default_allowed_dirs_in,
        exclude_dirs=default_exclude_dirs_in,
        allowed_patterns=default_allowed_patterns_in,
        exclude_patterns=default_exclude_patterns_in
    )
    logger.info(global_default_filters)
    # toolbar row you already have
    link_row = QHBoxLayout()
    host.link_btn = QToolButton(); host.link_btn.setCheckable(True); host.link_btn.setChecked(True)
    host.link_btn.setText("🔗 Linked"); link_row.addWidget(host.link_btn)
    link_row.addStretch(1)
    host.layout().addLayout(link_row)

    # NEW: visibility manager
    if not hasattr(host, "_vis"):
        host._vis = VisibilityMgr(host, settings_app="FinderConsole", animate_default=True)

    # Register the form as a collapsible section, auto-create a toggle button and place it in link_row
    host._vis.collapse_btn = host._vis.register(
        name="filters",
        container=host._input_container,
        button_host_layout=link_row,          # puts the button next to "Linked" control
        start_visible=True,
        animate=True,                         # slide animation
        shortcut="Ctrl+`",                    # toggle with a hotkey
        button_text_open="−",
        button_text_closed="+",
        persist=True
    )
    # --- lay out form -----------------------------------------------------
    createLayoutForm(host)
    getSharedBus(host,bus=bus,global_default_filters=global_default_filters,auto_unlink_on_init_if_diff=auto_unlink_on_init_if_diff,)
    
