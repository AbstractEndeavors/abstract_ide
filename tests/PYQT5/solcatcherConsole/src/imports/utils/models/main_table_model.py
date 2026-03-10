from .imports import QAbstractTableModel, Qt, QModelIndex

class MainTableModel(QAbstractTableModel):
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
