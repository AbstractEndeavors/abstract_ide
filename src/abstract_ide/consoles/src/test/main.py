from abstract_gui import QFileDialog,QLabel,startConsole,QMainWindow,QPushButton,QVBoxLayout,QHBoxLayout,QWidget
from flow_layout import FlowLayout
from flow_layout import FlowLayout
from PyQt6.QtWidgets import QLabel, QFileDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
class ImageWidget(QLabel):

    def __init__(self, path):
        super().__init__()

        pix = QPixmap(path)

        self.setPixmap(pix)
        self.setScaledContents(True)

        # thumbnail size
        self.setFixedSize(150,150)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
class ImageWidget(QLabel):

    def __init__(self, path):
        super().__init__()

        pix = QPixmap(path)

        self.setPixmap(pix)
        self.setScaledContents(True)

        # thumbnail size
        self.setFixedSize(150,150)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
def add_push_button(self,layout,btn_vars):
    attrs = []
    for btn_var in btn_vars:
        attr = getattr(self,btn_var.get("name"),QPushButton(btn_var.get("label")))
        attr.clicked.connect(btn_var.get("function"))
        layout.addWidget(attr)
        attrs.append(attr)
    return attr
class windowManager(QMainWindow):

    COLS = ["Window ID", "Title", "PID", "Monitor", "Type", "Selected?"]

    def __init__(self) -> None:
        super().__init__()
        self.type='on'
        self.setWindowTitle("Window Manager")
        self.resize(980, 640)
        self.flow = FlowLayout()
        central = QWidget(self)
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        filt = QHBoxLayout()
        self.sel_type_btn = add_push_button(
            self,
            filt,
            [
                {"label":f"Select-All ({self.type})",
                "function":(lambda: self.print_it(self.type)),
                "name":'sel_type_btn'},
                {"label":"Load Images",
                "function":self.load_images,
                "name":"load_btn"},
                ]
            )
        self.load_btn = QPushButton("Load Images")
        self.load_btn.clicked.connect(self.load_images)
        
        
        filt.addWidget(self.load_btn)
        outer.addLayout(filt)

    def load_images(self):

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select images",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )

        for f in files:
            img = ImageWidget(f)
            self.flow.addWidget(img)
    def print_it(self,variable=None):
        print(f'printed {variable}')
        variable = variable or self.type
        self.type = {"on":"off","off":"on"}[variable]
        self.sel_type_btn.setText(f"Select-All ({self.type})")
    @staticmethod
    def start():
        startConsole(windowManager)

windowManager.start()
