from .imports import QObject, pyqtSignal

class LazyLoader(QObject):
    loaded = pyqtSignal(list)

    def __init__(self, fetch_fn, page_size=50):
        super().__init__()
        self.fetch_fn = fetch_fn
        self.page_size = page_size
        self.page = 0

    def reset(self):
        self.page = 0

    def load_next(self, filters):
        rows = self.fetch_fn(
            limit=self.page_size,
            offset=self.page * self.page_size,
            **filters
        )
        if rows:
            self.page += 1
            self.loaded.emit(rows)
