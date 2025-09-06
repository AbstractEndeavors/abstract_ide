from .imports import *
from .green_screen_delimiter import *
# From functions.py
def run_all(input_path: str, weak: float, strong: float, out_dir_name="new_pics"):
    base_dir = os.path.dirname(input_path)
    out_dir = os.path.join(base_dir, out_dir_name)
    os.makedirs(out_dir, exist_ok=True)

    all_path = os.path.join(out_dir, "all_green.png")
    blur_path = os.path.join(out_dir, "green_screen_blur.png")
    blur_path_thresh = os.path.join(out_dir, "green_screen_blur.png")
    detect_all_green(input_path, all_path, strong_thresh=strong, weak_thresh=weak)
    detect_greenscreen_blur(input_path, blur_path)
    detect_greenscreen_blur_thresh(input_path, blur_path_thresh, strong_thresh=strong, weak_thresh=weak)

    return input_path, all_path, blur_path,blur_path_thresh

class LabeledImage(QVBoxLayout):
    """Small helper layout: a bold label and a scaled image view."""
    def __init__(self, title: str):
        super().__init__()
        self.title = QLabel(f"<b>{title}</b>")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.view = QLabel("Select an image to begin")
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setFrameShape(QFrame.Shape.StyledPanel)
        self.view.setMinimumSize(320, 240)

        self.addWidget(self.title)
        self.addWidget(self.view)

    def set_pixmap(self, pix: QPixmap):
        self.view.setPixmap(pix)
