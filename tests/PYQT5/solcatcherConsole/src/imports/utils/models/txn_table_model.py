# display/models/txn_table_model.py
from .imports import QAbstractTableModel, Qt, QModelIndex,QObject,pyqtSignal

class TxnTableModel(QAbstractTableModel):
    def __init__(self, columns, rows=None):
        super().__init__()
        self.columns = columns
        self.rows = rows or []

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return str(self.rows[index.row()][index.column()])
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.columns[section]
        return None

    def append_rows(self, new_rows):
        start = len(self.rows)
        self.beginInsertRows(QModelIndex(), start, start + len(new_rows) - 1)
        self.rows.extend(new_rows)
        self.endInsertRows()
class LazyTxnLoader(QObject):
    loaded = pyqtSignal(list)

    def __init__(self, fetch_fn, page_size=50):
        super().__init__()
        self.page = 0
        self.page_size = page_size
        self.fetch_fn = fetch_fn

    def load_next(self, filters):
        rows = self.fetch_fn(
            limit=self.page_size,
            offset=self.page * self.page_size,
            **filters
        )
        self.page += 1
        self.loaded.emit(rows)
