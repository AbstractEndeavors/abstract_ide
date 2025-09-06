# qt_green_screen.py
from .imports import *

class imageTab(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Greenscreen Inspector (PyQt6)")
        self.resize(1400, 700)

        # --- central widgets ---
        central = QWidget()
        self.setCentralWidget(central)

        self.orig = LabeledImage("Original")
        self.allg = LabeledImage("All Green (orig colors)")
        self.blur = LabeledImage("Blur/Edge Band (orig colors)")
        self.blur_thresh = LabeledImage("Blur/Edge Band (Threshold colors)")
        
        images_row = QHBoxLayout()
        images_row.addLayout(self.orig, 1)
        images_row.addLayout(self.allg, 1)
        images_row.addLayout(self.blur, 1)
        images_row.addLayout(self.blur_thresh, 1)
                

        # Controls: thresholds and buttons
        self.weakSpin = QSpinBox()
        self.weakSpin.setRange(0, 100)
        self.weakSpin.setValue(40)  # maps to 0.40
        self.weakSpin.setSuffix(" %")
        self.strongSpin = QSpinBox()
        self.strongSpin.setRange(0, 100)
        self.strongSpin.setValue(60)  # maps to 0.60
        self.strongSpin.setSuffix(" %")

        form = QFormLayout()
        form.addRow("Weak threshold (g ratio):", self.weakSpin)
        form.addRow("Strong threshold (g ratio):", self.strongSpin)

        self.selectBtn = QPushButton("Select Image")
        self.runBtn = QPushButton("Run")
        self.saveCompareBtn = QPushButton("Save Side-by-Side PNG")
        self.saveCompareBtn = QPushButton("Save Side-by-Side PNG")
        
        # Disable Run button until an image is selected
        self.runBtn.setEnabled(False)
        self.selectBtn.clicked.connect(self._open)
        self.runBtn.clicked.connect(self._run)
        self.saveCompareBtn.clicked.connect(self._save_combined)

        controls = QHBoxLayout()
        controls.addWidget(self.selectBtn)
        controls.addLayout(form, 0)
        controls.addWidget(self.runBtn)
        controls.addWidget(self.saveCompareBtn)
        controls.addStretch(1)

        layout = QVBoxLayout(central)
        layout.addLayout(images_row, 1)
        layout.addLayout(controls, 0)

        # menu: open
        open_act = QAction("Open…", self)
        open_act.triggered.connect(self._open)
        self.menuBar().addAction(open_act)

        self.input_path: str | None = None
        self.paths = (None, None, None)  # (orig, all, blur)

    def _open(self):
        try:
            path, _ = QFileDialog.getOpenFileName(
                self, "Choose an image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
            )
            if not path:
                return
            self.input_path = path
            self._set_pix(self.orig, path)
            # Clear others
            self.allg.set_pixmap(QPixmap())
            self.blur.set_pixmap(QPixmap())
            self.blur_thresh.set_pixmap(QPixmap())
            # Enable Run button
            self.runBtn.setEnabled(True)
            self.statusBar().showMessage(f"Selected: {path}", 3000)
        except Exception as e:
            print(f"{e}")
    def _gvals(self):
        try:
            weak = self.weakSpin.value() / 100.0
            strong = self.strongSpin.value() / 100.0
            # ensure weak < strong
            if weak >= strong:
                strong = min(0.99, weak + 0.05)
                self.strongSpin.setValue(int(round(strong * 100)))
            return weak, strong
        except Exception as e:
            print(f"{e}")
    def _run(self):
        try:
            if not self.input_path:
                self.statusBar().showMessage("Open an image first.", 3000)
                return
            weak, strong = self._gvals()
            orig, allg, blur, blur_thresh = run_all(self.input_path, weak, strong)
            self.paths = (orig, allg, blur)
            self._set_pix(self.allg, allg)
            self._set_pix(self.blur, blur)
            self._set_pix(self.blur_thresh, blur_thresh)
        except Exception as e:
            print(f"{e}")
    def _set_pix(self, slot: LabeledImage, path: str):
        try:
            if not path or not os.path.exists(path):
                slot.set_pixmap(QPixmap())
                return
            pix = QPixmap(path)
            # fit to label size while keeping aspect ratio
            if slot.view.width() > 0 and slot.view.height() > 0:
                pix = pix.scaled(
                    slot.view.width(), slot.view.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            slot.set_pixmap(pix)
        except Exception as e:
            print(f"{e}")
    def resizeEvent(self, e):
        super().resizeEvent(e)
        try:
            # rescale displayed images when window size changes
            if self.input_path:
                self._set_pix(self.orig, self.input_path)
            if self.paths[1]:
                self._set_pix(self.allg, self.paths[1])
            if self.paths[2]:
                self._set_pix(self.blur, self.paths[2])
            if self.paths[3]:
                self._set_pix(self.blur_thresh, self.paths[3])
        except Exception as e:
            print(f"{e}")
    def _save_combined(self):
        try:
            if not all(self.paths):
                self.statusBar().showMessage("Run detection first.", 3000)
                return
            # Build a side-by-side PNG
            from PIL import Image
            img_o = Image.open(self.paths[0]).convert("RGBA")
            img_a = Image.open(self.paths[1]).convert("RGBA")
            img_b = Image.open(self.paths[2]).convert("RGBA")
            img_c = Image.open(self.paths[3]).convert("RGBA")
            # uniform height to original
            if img_a.height != img_o.height:
                img_a = img_a.resize((int(img_a.width * img_o.height / img_a.height), img_o.height))
            if img_b.height != img_o.height:
                img_b = img_b.resize((int(img_b.width * img_o.height / img_b.height), img_o.height))
            if img_c.height != img_o.height:
                img_c = img_b.resize((int(img_c.width * img_o.height / img_c.height), img_o.height))
            W = img_o.width + img_c.width + img_c.width
            H = img_o.height
            combo = Image.new("RGBA", (W, H))
            x = 0
            for im in (img_o, img_a, img_b.img_c):
                combo.paste(im, (x, 0))
                x += im.width

            out_path, _ = QFileDialog.getSaveFileName(
                self, "Save comparison", "greenscreen_comparison.png", "PNG (*.png)"
            )
            if out_path:
                combo.save(out_path, "PNG")
                self.statusBar().showMessage(f"Saved: {out_path}", 3000)
        except Exception as e:
            print(f"{e}")
def startImageConsole():
    startConsole(imageTab)
