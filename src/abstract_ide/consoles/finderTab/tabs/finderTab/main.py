from ..imports import *
from .initFuncs import initFuncs
# New Tab: Directory Map
class finderTab(QWidget):
    def __init__(self, bus: SharedStateBus):
        super().__init__()
        self.setLayout(QVBoxLayout())
        grid = QGridLayout()
        install_common_inputs(
            self, grid, bus=bus,
            primary_btn=("Run search", self.start_search),
            secondary_btn=("stop search", self.stop_search)

        )
        # Output area
        self.layout().addWidget(QLabel("Results"))
        self.lines_list = []
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.open_one)
        self.layout().addWidget(self.list, stretch=3)
        self._last_results = []
finderTab = initFuncs(finderTab)
