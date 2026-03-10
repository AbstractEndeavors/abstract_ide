# functions_console.py
from .imports import QLayout,initFuncs
# --- FlowLayout (chips that wrap) -------------------------------------------
class flowLayout(QLayout):
    def __init__(self, parent=None, margin=0, hspacing=8, vspacing=6):
        initFuncs(self)
        QLayout.__init__(self, parent)
        self._items = []
        self._h = hspacing
        self._v = vspacing
        self.setContentsMargins(margin, margin, margin, margin)
        # let the parent compute height-for-width
        self.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
    
    def start():
        startConsole(flowLayout)
