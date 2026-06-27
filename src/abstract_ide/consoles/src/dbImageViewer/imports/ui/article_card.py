from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QPixmap, QCursor
from PyQt6.QtCore import Qt, QRunnable, QObject, pyqtSignal, QThreadPool
import requests
import webbrowser

from ..parser.article_parser import ArticleData


class _ImageFetchSignals(QObject):
    done = pyqtSignal(bytes)
    failed = pyqtSignal()


class _ImageFetcher(QRunnable):
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.signals = _ImageFetchSignals()

    def run(self):
        try:
            r = requests.get(self.url, timeout=5)
            r.raise_for_status()
            self.signals.done.emit(r.content)
        except Exception:
            self.signals.failed.emit()


class _DownloadSignals(QObject):
    started  = pyqtSignal()
    done     = pyqtSignal(str)   # path
    error    = pyqtSignal(str)
    skipped  = pyqtSignal()      # already in registry


class _DownloadWorker(QRunnable):
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.signals = _DownloadSignals()

    def run(self):
        # import here — LISTMANAGER is a singleton, safe to call from any thread
        from ..managers.listManager import LISTMANAGER
        try:
            mgr = LISTMANAGER()
            token_url, url_js = mgr.get_token_url(self.url)
            if not token_url:
                self.signals.skipped.emit()
                return
            from ..workers.worker import download
            path = download(token_url, url_js['file_name'])
            from ..managers.db import DownloadRecord
            mgr.registry.save(DownloadRecord(
                file_id=url_js['file_id'],
                file_name=url_js['file_name'],
                original_url=url_js['original_url'],
                token_url=token_url,
                path=str(path),
            ))
            self.signals.done.emit(str(path))
        except Exception as e:
            self.signals.error.emit(str(e))


class ArticleCard(QWidget):
    def __init__(self, article: ArticleData):
        super().__init__()
        self.article = article
        self.setFixedWidth(260)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._downloading = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self._img_label = QLabel("Loading…")
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setFixedHeight(180)
        layout.addWidget(self._img_label)

        if self.article.image_url:
            fetcher = _ImageFetcher(self.article.image_url)
            fetcher.signals.done.connect(self._set_image)
            fetcher.signals.failed.connect(lambda: self._img_label.setText("Image unavailable"))
            QThreadPool.globalInstance().start(fetcher)
        else:
            self._img_label.setText("No image")

        title = QLabel(self.article.title)
        title.setWordWrap(True)
        title.setStyleSheet("font-weight: bold;")

        meta = QLabel(f"{self.article.pages} • {self.article.size}\n{self.article.views}")
        meta.setStyleSheet("color: gray; font-size: 10px")

        author = QLabel()
        if self.article.author_url:
            author.setText(f"<a href='{self.article.author_url}'>{self.article.author}</a>")
            author.setOpenExternalLinks(True)

        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 10px;")
        self._status.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(meta)
        layout.addWidget(author)
        layout.addWidget(self._status)

    def _set_image(self, data: bytes):
        pix = QPixmap()
        if pix.loadFromData(data):
            self._img_label.setPixmap(
                pix.scaledToWidth(240, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self._img_label.setText("Invalid image")

    def mousePressEvent(self, event):
        if not self.article.download_url or self._downloading:
            return
        self._start_download()

    def _start_download(self):
        self._downloading = True
        self._status.setStyleSheet("color: gray; font-size: 10px;")
        self._status.setText("Queued…")

        worker = _DownloadWorker(self.article.download_url)
        worker.signals.started.connect(lambda: self._status.setText("Downloading…"))
        worker.signals.done.connect(self._on_done)
        worker.signals.error.connect(self._on_error)
        worker.signals.skipped.connect(self._on_skipped)
        QThreadPool.globalInstance().start(worker)

    def _on_done(self, path: str):
        self._downloading = False
        self._status.setStyleSheet("color: green; font-size: 10px;")
        self._status.setText(f"✓ {path.split('/')[-1]}")

    def _on_error(self, msg: str):
        self._downloading = False
        self._status.setStyleSheet("color: red; font-size: 10px;")
        self._status.setText(f"✗ {msg}")

    def _on_skipped(self):
        self._downloading = False
        self._status.setStyleSheet("color: gray; font-size: 10px;")
        self._status.setText("Already downloaded")
