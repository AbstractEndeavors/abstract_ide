from ..imports import *
from PyQt6.QtWidgets import QWidgetItem
def addItem(self, item):
    self._items.append(item)

def addWidget(self, w):
    # Must wrap widgets in a QWidgetItem and store it,
    # Use Qt’s addWidget => it will call our addItem(...) and reparent the widget.
    QLayout.addWidget(self, w)

def count(self):
    return len(self._items)

def itemAt(self, i):
    return self._items[i] if 0 <= i < len(self._items) else None

def takeAt(self, i):
    return self._items.pop(i) if 0 <= i < len(self._items) else None

def expandingDirections(self):
    return Qt.Orientations(0)

def hasHeightForWidth(self):
    return True

def heightForWidth(self, w):
    return self._doLayout(QRect(0, 0, max(0, w), 0), True)

def setGeometry(self, r):
    QLayout.setGeometry(self, r)              # <-- pass self
    self._doLayout(r, False)

def sizeHint(self):
    return self.minimumSize()

def minimumSize(self):
    s = QSize()
    for it in self._items:
        s = s.expandedTo(it.minimumSize())
    m = self.contentsMargins()
    s += QSize(m.left() + m.right(), m.top() + m.bottom())
    return s

def _doLayout(self, rect, test):
    x = rect.x()
    y = rect.y()
    lineH = 0
    m = self.contentsMargins()
    x += m.left()
    y += m.top()
    right = rect.right() - m.right()

    for it in self._items:
        sz = it.sizeHint()
        w = sz.width()
        h = sz.height()
        if x + w > right and lineH > 0:
            x = rect.x() + m.left()
            y += lineH + self._v
            lineH = 0
        if not test:
            it.setGeometry(QRect(QPoint(x, y), sz))
        x += w + self._h
        lineH = max(lineH, h)

    return y + lineH + m.bottom() - rect.y()
