from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QSpinBox,
    QPushButton, QLabel, QScrollArea, QCheckBox, QSizePolicy,
    QFrame, QGridLayout,
)
from PyQt6.QtCore import Qt, QRunnable, QObject, pyqtSignal, QThreadPool

from ..src.utils import get_user_page, get_page_tags, USER
from ..src.constants import FILTERS


class _TagFetchSignals(QObject):
    done = pyqtSignal(list)
    error = pyqtSignal(str)


class _TagFetcher(QRunnable):
    def __init__(self, page: int, user: str | None):
        super().__init__()
        self.page = page
        self.user = user
        self.signals = _TagFetchSignals()

    def run(self):
        try:
            tags = get_page_tags(self.page, self.user)
            self.signals.done.emit(tags)
        except Exception as e:
            self.signals.error.emit(str(e))




class TagSelector(QWidget):
    COLUMNS = 4

    def __init__(self, active_filters: list[str], parent=None):
        super().__init__(parent)
        self._active: set[str] = set(active_filters)
        self._checkboxes: dict[str, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        # ── single header line ────────────────────────────────
        header = QHBoxLayout()

        self._toggle_btn = QPushButton("▶ Tags")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setFixedWidth(70)
        self._toggle_btn.toggled.connect(self._toggle)

        self._status = QLabel("")
        self._status.setStyleSheet("color: gray; font-size: 10px;")

        self._add_field = QLineEdit()
        self._add_field.setPlaceholderText("Add tag…")
        self._add_field.setFixedWidth(90)
        self._add_field.returnPressed.connect(self._add_manual)

        add_btn = QPushButton("+")
        add_btn.setFixedWidth(22)
        add_btn.clicked.connect(self._add_manual)

        self._fetch_btn = QPushButton("Fetch")
        self._fetch_btn.setFixedWidth(44)
        self._fetch_btn.clicked.connect(self._request_fetch)

        header.addWidget(self._toggle_btn)
        header.addWidget(self._status, stretch=1)
        header.addWidget(self._add_field)
        header.addWidget(add_btn)
        header.addWidget(self._fetch_btn)
        root.addLayout(header)

        # ── collapsible grid ──────────────────────────────────
        self._panel = QWidget()
        self._panel.setVisible(False)

        panel_layout = QVBoxLayout(self._panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMaximumHeight(110)

        self._box_container = QWidget()
        self._box_layout = QGridLayout(self._box_container)
        self._box_layout.setContentsMargins(2, 2, 2, 2)
        self._box_layout.setHorizontalSpacing(8)
        self._box_layout.setVerticalSpacing(1)

        scroll.setWidget(self._box_container)
        panel_layout.addWidget(scroll)
        root.addWidget(self._panel)

        self._get_context = lambda: (1, None)

        for f in sorted(self._active):
            self._add_checkbox(f, checked=True)

        self._refresh_status()

    # ── public ────────────────────────────────────────────────

    def set_context_provider(self, fn):
        self._get_context = fn

    @property
    def active_filters(self) -> list[str]:
        return [tag for tag, cb in self._checkboxes.items() if cb.isChecked()]

    # ── internals ─────────────────────────────────────────────

    def _toggle(self, checked: bool):
        self._toggle_btn.setText(f"{'▼' if checked else '▶'} Tags")
        self._panel.setVisible(checked)

    def _refresh_status(self):
        active = sum(1 for cb in self._checkboxes.values() if cb.isChecked())
        total = len(self._checkboxes)
        self._status.setText(f"{active}/{total}" if total else "")

    def _add_checkbox(self, tag: str, checked: bool = False):
        if tag in self._checkboxes:
            return
        cb = QCheckBox(tag)
        cb.setChecked(checked)
        cb.toggled.connect(lambda _: self._refresh_status())
        idx = len(self._checkboxes)
        row, col = divmod(idx, self.COLUMNS)
        self._box_layout.addWidget(cb, row, col)
        self._checkboxes[tag] = cb
        self._refresh_status()

    def _add_manual(self):
        tag = self._add_field.text().strip()
        if not tag:
            return
        self._add_checkbox(tag, checked=True)
        self._add_field.clear()
        if not self._panel.isVisible():
            self._toggle_btn.setChecked(True)

    def _request_fetch(self):
        page, user = self._get_context()
        self._fetch_btn.setEnabled(False)
        self._status.setText("…")
        fetcher = _TagFetcher(page, user)
        fetcher.signals.done.connect(self._on_tags_fetched)
        fetcher.signals.error.connect(self._on_fetch_error)
        QThreadPool.globalInstance().start(fetcher)

    def _on_tags_fetched(self, tags: list[str]):
        for tag in tags:
            self._add_checkbox(tag, checked=(tag in self._active))
        self._refresh_status()
        self._fetch_btn.setEnabled(True)
        if not self._panel.isVisible():
            self._toggle_btn.setChecked(True)

    def _on_fetch_error(self, msg: str):
        self._status.setText(f"err: {msg}")
        self._fetch_btn.setEnabled(True)
class QueryBar(QWidget):
    def __init__(self, browser):
        super().__init__()
        self.browser = browser

        root = QVBoxLayout(self)
        root.setSpacing(6)

        # ── query row ──────────────────────────────────────────
        query_row = QHBoxLayout()

        self.user = QLineEdit()
        self.user.setPlaceholderText(f"User (default: {USER})")
        self.user.textChanged.connect(self._update_preview)

        self.start_page = QSpinBox()
        self.start_page.setMinimum(1)
        self.start_page.setMaximum(99999)
        self.start_page.setPrefix("From ")
        self.start_page.valueChanged.connect(self._update_preview)

        self.end_page = QSpinBox()
        self.end_page.setMinimum(1)
        self.end_page.setMaximum(99999)
        self.end_page.setPrefix("To ")

        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self.load)

        query_row.addWidget(self.user)
        query_row.addWidget(self.start_page)
        query_row.addWidget(self.end_page)
        query_row.addWidget(load_btn)

        # ── url preview ────────────────────────────────────────
        self._url_label = QLabel()
        self._url_label.setStyleSheet("color: gray; font-size: 10px;")
        self._url_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._url_label.setWordWrap(True)

        # ── tag selector ───────────────────────────────────────
        self._tag_selector = TagSelector(FILTERS)
        self._tag_selector.set_context_provider(self._current_context)

        root.addLayout(query_row)
        root.addWidget(self._url_label)
        root.addWidget(self._tag_selector)
        # in QueryBar.__init__, add to query_row:
        self._skip_downloaded = QCheckBox("Hide downloaded")
        query_row.addWidget(self._skip_downloaded)


        self._update_preview()

    # ── slots ─────────────────────────────────────────────────

    def _current_context(self) -> tuple[int, str | None]:
        user = self.user.text().strip() or None
        return self.start_page.value(), user

    def _update_preview(self):
        user = self.user.text().strip() or USER
        page = self.start_page.value()
        self._url_label.setText(f"URL: {get_user_page(user=user, page=str(page))}")


    # update load():
    def load(self):
        start = self.start_page.value()
        end = max(self.end_page.value(), start)

        FILTERS.clear()
        FILTERS.extend(self._tag_selector.active_filters)

        user = self.user.text().strip() or None
        self.browser.load_pages(
            start, end, user,
            skip_downloaded=self._skip_downloaded.isChecked(),
        )
