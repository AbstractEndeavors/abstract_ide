# test_pyqt.py
import sys
from PyQt6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
label = QLabel("✅ PyQt is working")
label.resize(300, 100)
label.show()

sys.exit(app.exec())
