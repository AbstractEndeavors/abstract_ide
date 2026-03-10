from .imports import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QGroupBox, Qt

class TxnPanel(QWidget):
    def __init__(self, txn_model):
        super().__init__()
        layout = QHBoxLayout(self)

        table_box = QGroupBox("Transaction History")
        table_layout = QVBoxLayout(table_box)
        self.table = QLabel("Txn table goes here")
        table_layout.addWidget(self.table)

        chart_box = QGroupBox("Chart")
        chart_layout = QVBoxLayout(chart_box)
        chart_layout.addWidget(QLabel("Chart placeholder"))

        layout.addWidget(table_box, 3)
        layout.addWidget(chart_box, 2)
