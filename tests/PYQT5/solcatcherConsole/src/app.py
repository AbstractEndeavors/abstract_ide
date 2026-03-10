import sys
from PyQt5.QtWidgets import QApplication
from .main_window import MainWindow
from .models.main_table_model import MainTableModel
from .models.txn_table_model import TxnTableModel
from .controllers.lazy_loader import LazyLoader

def fake_fetch(**kwargs):
    return [
        ["row", "data", "example"]
    ]

app = QApplication(sys.argv)

main_model = MainTableModel(["A", "B", "C"])
txn_model = TxnTableModel(["X", "Y", "Z"])
loader = LazyLoader(fake_fetch)

window = MainWindow(main_model, txn_model, loader)
window.show()

sys.exit(app.exec_())
