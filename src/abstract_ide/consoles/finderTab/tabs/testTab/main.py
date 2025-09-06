
from abstract_gui.QT6 import *
from initFuncs import initFuncs
# New Tab: Directory Map
class finderTab(ConsoleBase):
    def __init__(self,  *, bus=None, parent=None):
        super().__init__(bus=bus, parent=parent)
        inner = QTabWidget()
        self.layout().addWidget(inner)
    

        grid = QGridLayout()
        install_common_inputs(
            self, grid, bus=bus,
            primary_btn=("Run search", self.start_search)
        )


        # Output area
        
        self.layout().addWidget(QLabel("Results"))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.open_one)
        self.layout().addWidget(self.list, stretch=3)
        self._last_results = []


finderTab = initFuncs(finderTab)
startConsole(finderTab)

