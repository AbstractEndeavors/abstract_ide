from .imports import *
class solcatcherConsole(QMainWindow):
    def __init__(self, main_model=None, txn_model=None, loader=None):
        super().__init__()
        self.setWindowTitle("SOL Transaction Dashboard")
        central = QWidget()
        layout = QVBoxLayout(central)

        self.filters = FilterPanel()
        layout.addWidget(self.filters)

        splitter = QSplitter()
        splitter.addWidget(MainTablePanel(main_model))
        splitter.addWidget(TxnPanel(txn_model))
        splitter.addWidget(BotPanel())

        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.filters.apply_btn.clicked.connect(
            lambda: loader.reset()
        )
