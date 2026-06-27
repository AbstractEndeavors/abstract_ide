import sys
from PyQt6.QtWidgets import QApplication
from abstract_database import DatabaseBrowser
from gui.main_window import MainWindow
from gui.controller import DBController

app = QApplication(sys.argv)

browser = DatabaseBrowser(dbUrl='postgresql://solcatcher:solcatcher123!!!456@23.126.105.154:5432/solcatcher')
ui = MainWindow()
controller = DBController(ui, browser)

ui.show()
sys.exit(app.exec())
