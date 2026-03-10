from .imports import QWidget, QVBoxLayout, QTableView,Qt

class MainTablePanel(QWidget):
    def __init__(self, model):
        super().__init__()
        layout = QVBoxLayout(self)

        self.table = QTableView()
        self.table.setModel(model)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)
