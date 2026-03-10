from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from ..parser.article_parser import parse_articles
from ..src.utils import get_user_page, USER


class PageLoaderSignals(QObject):
    page_loaded = pyqtSignal(list)
    error = pyqtSignal(str)


class PageLoader(QRunnable):
    def __init__(self, page: int, user: str | None = None, skip_downloaded: bool = False):
        super().__init__()
        self.page = page
        self.user = user or USER
        self.skip_downloaded = skip_downloaded
        self.signals = PageLoaderSignals()

    def run(self):
        try:
            url = get_user_page(user=self.user, page=str(self.page))
            articles = parse_articles(url, skip_downloaded=self.skip_downloaded)
            self.signals.page_loaded.emit(articles)
        except Exception as e:
            self.signals.error.emit(str(e))
