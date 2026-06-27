from .imports import *

def enable_widget(parent, name: str, enabled: bool):
    try:
        getattr(parent, name).setEnabled(enabled)
    except AttributeError:
        print(f"[WARN] No widget {name} in {parent}")

class finderTab(QWidget):
    def __init__(self, bus: SharedStateBus):
        super().__init__()
        initFuncs(self)
        self.setLayout(QVBoxLayout())
        grid = QGridLayout()

        install_common_inputs(
            self, grid, bus=bus,
            primary_btn=("Run search", self.start_search),
            secondary_btn=("Stop search", self.stop_search)


        )
        # Output area
        self.layout().addWidget(QLabel("Results"))
        self.lines_list = []
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.open_one)
        self.layout().addWidget(self.list, stretch=3)
        self._last_results = []
