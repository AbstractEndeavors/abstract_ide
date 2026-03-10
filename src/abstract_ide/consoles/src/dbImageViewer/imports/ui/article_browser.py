from PyQt6.QtWidgets import QWidget, QScrollArea, QVBoxLayout
from PyQt6.QtCore import QThreadPool

from .flow_layout import FlowLayout
from .article_card import ArticleCard
from ..workers.page_loader import PageLoader


class ArticleBrowser(QWidget):
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool.globalInstance()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.layout = FlowLayout(self.container)
        self.scroll.setWidget(self.container)

        root = QVBoxLayout(self)
        root.addWidget(self.scroll)

        self._pending_clear = False

    def clear(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item:
                item.widget().deleteLater()

    def load_pages(self, start: int, end: int, user: str | None = None, skip_downloaded: bool = False):
        self._pending_clear = True

        for page in range(start, end + 1):
            worker = PageLoader(page, user, skip_downloaded=skip_downloaded)
            worker.signals.page_loaded.connect(self._add_articles)
            worker.signals.error.connect(self._on_error)
            self.thread_pool.start(worker)

    def _add_articles(self, articles):
        if self._pending_clear:
            self.clear()
            self._pending_clear = False
        for article in articles:
            self.layout.addWidget(ArticleCard(article))

    def _on_error(self, msg: str):
        print(f"[page load error] {msg}")
