from .imports import QWidget, QVBoxLayout, QPushButton, QTabWidget, QLabel

class BotPanel(QTabWidget):
    def __init__(self):
        super().__init__()
        self.addTab(self.manual_tab(), "Manual")
        self.addTab(self.auto_tab(), "Automated")

    def manual_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("Manual Controls"))
        l.addWidget(QPushButton("Manual Buy"))
        l.addWidget(QPushButton("Manual Sell"))
        return w

    def auto_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("Automated Bot Controls"))
        l.addWidget(QPushButton("Start Bot"))
        l.addWidget(QPushButton("Stop Bot"))
        return w
