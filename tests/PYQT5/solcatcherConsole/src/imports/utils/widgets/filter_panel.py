from .imports import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton, QLineEdit, QGroupBox

class FilterPanel(QGroupBox):
    def __init__(self):
        super().__init__("Filter Criteria")
        layout = QVBoxLayout(self)

        sol_row = QHBoxLayout()
        sol_row.addWidget(QLabel("SOL Threshold"))
        self.sol_input = QLineEdit("10")
        sol_row.addWidget(self.sol_input)
        layout.addLayout(sol_row)

        time_row = QHBoxLayout()
        self.time_combo = QComboBox()
        self.time_combo.addItems([
            "All Time", "Last 1 min", "Last 5 min",
            "Last Hour", "Last Day", "Last Week"
        ])
        time_row.addWidget(QLabel("Time Range"))
        time_row.addWidget(self.time_combo)
        layout.addLayout(time_row)

        self.apply_btn = QPushButton("Apply Filters")
        layout.addWidget(self.apply_btn)

    def get_filters(self):
        return {
            "sol_amount": float(self.sol_input.text()),
            "timestamp": self.time_combo.currentText()
        }
