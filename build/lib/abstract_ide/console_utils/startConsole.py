from .worker_scans import *
from .collapsable_log_panel import *
from .log_manager import *
from .ensure_resizable import *
from PyQt6.QtWidgets import QApplication


# ─────────────────────────── runner ───────────────────────────────────────────────

def startConsole(console_class, *args, **kwargs):
    """
    Creates the app/window, wires scanning + log view,
    wraps logs in a toolbar-style collapsible panel that expands the window
    (so the main content isn't squeezed).
    """
    app = QApplication.instance() or QApplication(sys.argv)

    win = console_class(*args, **kwargs)
    get_WorkerScans(win)  # ensures win.log (QTextEdit) and shutdown plumbing exist

    # Ensure main layout
    lay = win.layout() or QtWidgets.QVBoxLayout(win)
    if win.layout() is None:
        win.setLayout(lay)

    # Optional: small header row above the panel (remove if redundant with toolbar)
    header_row = QHBoxLayout()
    header_row.addWidget(QLabel("Log Output (global):"))
    header_row.addStretch(1)
    lay.addLayout(header_row)

    # Use a horizontal splitter to allow future extra panes next to the main log
    splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal, win)
    splitter.addWidget(win.log)  # win.log is the QTextEdit created by get_WorkerScans

    # Collapsible panel that grows/shrinks the window instead of squishing content
    log_panel = CollapsibleLogPanel("Logs", splitter, start_visible=False, parent=win)
    lay.addWidget(log_panel)

    # Reuse the same toggle action in a top toolbar if this is a QMainWindow
    if isinstance(win, QtWidgets.QMainWindow):
        tb = win.addToolBar("View")
        tb.setMovable(False); tb.setFloatable(False)
        tb.addAction(log_panel.toggle_action)

    # Stream live logs + tail existing file (if any). NOTE: only 2 args supported.
    attach_textedit_to_logs(win.log, tail_file=get_log_file_path())

    ensure_user_resizable(win, initial_size=(1100, 800), min_size=(600, 400))
    keep_capped_across_screen_changes(win, margin=8, fraction=0.95)

    # Clean shutdown for threads/workers
    if hasattr(win, "_graceful_shutdown"):
        app.aboutToQuit.connect(win._graceful_shutdown)

    win.show()
    return app.exec()
