#!/usr/bin/env python3
"""
wireframeTab — a snap-to-grid UI-wireframe canvas as an ideConsole tab.

Map out a UI by dragging labeled boxes onto a grid. Each box carries a semantic
ROLE from a fixed palette (Container, Nav, Sidebar, Button, Input, Text, Image,
List, Note) that colour-codes and variant-renders it, plus a free-text LABEL
that says what it represents in your own words. A Properties panel and a live
Legend keep the sketch self-documenting; layouts save/load as JSON and export
to PNG.

Architecture (per the design panel): QGraphicsView/QGraphicsScene so item
hit-testing, selection, rubber-band, movement and inline text editing come from
Qt rather than hand-rolled paint code. Undo is snapshot-based — each edit stores
the whole scene as JSON before/after, which is trivially correct for a tool this
size (a wireframe is a few dozen boxes) and avoids fragile item-pointer juggling.
"""
import json

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction, QBrush, QColor, QFont, QImage, QKeySequence, QPainter, QPen,
    QUndoCommand, QUndoStack,
)
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGraphicsRectItem,
    QGraphicsScene, QGraphicsTextItem, QGraphicsView, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSpinBox, QSplitter, QToolBar,
    QVBoxLayout, QWidget, QListWidget, QListWidgetItem, QGroupBox,
)

CANVAS_W, CANVAS_H = 1280, 800
DEFAULT_GRID = 20
HANDLE = 7                      # half-size of a resize handle, view-ish px
SCHEMA = "wireframe.v1"

# ── role palette: the single source of truth for colour + variant rendering ──
# variant drives paint(): plain / rounded / underline / imagecross / textlines /
# dividers / note (borderless translucent callout).
ROLE_PALETTE = {
    "container": {"name": "Container", "fill": "#EAF2FB", "border": "#4A90D9", "variant": "plain"},
    "nav":       {"name": "Nav",       "fill": "#D6E4F0", "border": "#2C6FB5", "variant": "plain"},
    "sidebar":   {"name": "Sidebar",   "fill": "#E8E8F7", "border": "#6A5ACD", "variant": "plain"},
    "button":    {"name": "Button",    "fill": "#DFF0D8", "border": "#3C763D", "variant": "rounded"},
    "input":     {"name": "Input",     "fill": "#FFFFFF", "border": "#999999", "variant": "underline"},
    "text":      {"name": "Text",      "fill": "#FFFFFF", "border": "#CCCCCC", "variant": "textlines"},
    "image":     {"name": "Image",     "fill": "#EEEEEE", "border": "#AAAAAA", "variant": "imagecross"},
    "list":      {"name": "List",      "fill": "#FFF8E1", "border": "#C9A227", "variant": "dividers"},
    "note":      {"name": "Note",      "fill": "#FFF9C4", "border": "#E0D060", "variant": "note"},
}
ROLE_ORDER = ["container", "nav", "sidebar", "button", "input", "text", "image", "list", "note"]


def role_name(role):
    return ROLE_PALETTE.get(role, ROLE_PALETTE["container"])["name"]


# ─────────────────────────────── label ────────────────────────────────────
class LabelItem(QGraphicsTextItem):
    """Centered, double-click-editable label living inside a ShapeItem."""

    def __init__(self, text, parent):
        super().__init__(text, parent)
        self.setDefaultTextColor(QColor("#222222"))
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        opt = self.document().defaultTextOption()
        opt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.document().setDefaultTextOption(opt)

    def start_edit(self):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        cur = self.textCursor()
        cur.select(cur.SelectionType.Document)
        self.setTextCursor(cur)

    def focusOutEvent(self, event):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        super().focusOutEvent(event)
        parent = self.parentItem()
        if parent is not None:
            parent._commit_label(self.toPlainText())


# ─────────────────────────────── shape ────────────────────────────────────
class ShapeItem(QGraphicsRectItem):
    """One wireframe box: a grid-placed rect with a role and an in-shape label.

    Placement is entirely in setPos(); the rect is kept at (0,0,w,h) so the grid
    origin and the item's local origin agree, which makes move-snapping a simple
    round of the proposed position.
    """
    TYPE = QGraphicsRectItem.UserType + 1

    def __init__(self, x, y, w, h, role="container", label=None, code="", sid=None):
        super().__init__(0, 0, w, h)
        self.sid = sid
        self.code = code                       # short auto placeholder shown on canvas
        self.role = role if role in ROLE_PALETTE else "container"
        self.label = label if label else role_name(self.role)   # the real identifier
        self.setPos(x, y)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        # On canvas we show the compact CODE (a, b, …) so long labels never
        # overflow the boxes; the full label lives in the Legend key. The same
        # text item is temporarily switched to the label while editing it.
        self._text = LabelItem(self.code, self)
        f = QFont(); f.setBold(True); f.setPointSize(11)
        self._text.setFont(f)
        self._resizing = None          # handle name while resizing, else None
        self._layout_text()

    def type(self):
        return ShapeItem.TYPE

    # -- geometry helpers --
    def size(self):
        r = self.rect()
        return r.width(), r.height()

    def set_size(self, w, h):
        self.prepareGeometryChange()
        self.setRect(0, 0, max(1, w), max(1, h))
        self._layout_text()

    def _layout_text(self):
        r = self.rect()
        self._text.setTextWidth(max(20, r.width() - 8))
        br = self._text.boundingRect()
        self._text.setPos((r.width() - br.width()) / 2,
                          (r.height() - br.height()) / 2)

    def _grid(self):
        sc = self.scene()
        return sc.grid_size if isinstance(sc, WireframeScene) else DEFAULT_GRID

    def _snap_on(self):
        sc = self.scene()
        return sc.snap if isinstance(sc, WireframeScene) else True

    # -- role / label --
    def set_role(self, role):
        if role in ROLE_PALETTE:
            self.role = role
            self.update()

    def set_label(self, text):
        """Set the identifier from the Properties panel (canvas keeps the code)."""
        self.label = text.strip() if text.strip() else role_name(self.role)

    def _commit_label(self, text):
        """Called when inline label editing ends: store it, revert display to code."""
        text = text.strip()
        self.label = text if text else role_name(self.role)
        self._text.setPlainText(self.code)     # back to the compact code
        self._layout_text()
        sc = self.scene()
        if isinstance(sc, WireframeScene):
            sc.editEnded.emit()        # commit is undoable
            sc.changed_notify()        # legend shows the label — refresh

    def edit_label(self):
        """Double-click: temporarily show the full label for inline editing."""
        sc = self.scene()
        if isinstance(sc, WireframeScene):
            sc.editBegan.emit()        # snapshot before the edit so it's undoable
        self._text.setPlainText(self.label)
        self._layout_text()
        self._text.start_edit()

    # -- snapping during move --
    def itemChange(self, change, value):
        if (change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange
                and self._snap_on() and not self._resizing):
            g = self._grid()
            return QPointF(round(value.x() / g) * g, round(value.y() / g) * g)
        return super().itemChange(change, value)

    # -- interactive resize (handles drawn in paint when selected) --
    def _handle_at(self, pos):
        """Return a handle name ('nw','n',...,'e') if pos is on a handle, else None."""
        if not self.isSelected():
            return None
        r = self.rect()
        xs = {"w": 0, "x": r.width() / 2, "e": r.width()}
        ys = {"n": 0, "y": r.height() / 2, "s": r.height()}
        names = {"nw": ("w", "n"), "n": ("x", "n"), "ne": ("e", "n"),
                 "e": ("e", "y"), "se": ("e", "s"), "s": ("x", "s"),
                 "sw": ("w", "s"), "w": ("w", "y")}
        for name, (hx, hy) in names.items():
            cx, cy = xs[hx], ys[hy]
            if abs(pos.x() - cx) <= HANDLE and abs(pos.y() - cy) <= HANDLE:
                return name
        return None

    def mousePressEvent(self, event):
        h = self._handle_at(event.pos())
        sc = self.scene()
        if isinstance(sc, WireframeScene):
            sc.editBegan.emit()        # snapshot before any drag (move or resize)
        if h:
            self._resizing = h
            self._start_rect = QRectF(self.rect())
            self._start_pos = QPointF(self.pos())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            self._do_resize(event.pos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_resizing = self._resizing
        self._resizing = None
        if was_resizing:
            self._snap_size()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
        sc = self.scene()
        if isinstance(sc, WireframeScene):
            sc.editEnded.emit()        # commit move/resize to undo
            sc.changed_notify()

    def _do_resize(self, pos):
        r = QRectF(self._start_rect)
        h = self._resizing
        # move the grabbed edge(s) to the cursor (in item-local coords)
        left, top, right, bottom = r.left(), r.top(), r.right(), r.bottom()
        if "w" in h:
            left = min(pos.x(), right - 1)
        if "e" in h:
            right = max(pos.x(), left + 1)
        if "n" in h:
            top = min(pos.y(), bottom - 1)
        if "s" in h:
            bottom = max(pos.y(), top + 1)
        # a west/north drag changes the origin: shift pos, keep rect at 0,0
        new_w = right - left
        new_h = bottom - top
        self.setPos(self._start_pos.x() + left, self._start_pos.y() + top)
        self.set_size(new_w, new_h)

    def _snap_size(self):
        if not self._snap_on():
            return
        g = self._grid()
        w, hgt = self.size()
        self.set_size(max(g, round(w / g) * g), max(g, round(hgt / g) * g))
        self.setPos(round(self.pos().x() / g) * g, round(self.pos().y() / g) * g)

    def mouseDoubleClickEvent(self, event):
        self.edit_label()
        event.accept()

    # -- painting --
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = ROLE_PALETTE.get(self.role, ROLE_PALETTE["container"])
        r = self.rect()
        variant = pal["variant"]
        fill = QColor(pal["fill"])
        if variant == "note":
            fill.setAlpha(200)
        painter.setBrush(QBrush(fill))
        if variant == "note":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(r, 4, 4)
        else:
            pen = QPen(QColor(pal["border"]))
            pen.setWidth(2)
            painter.setPen(pen)
            if variant == "rounded":
                painter.drawRoundedRect(r, 8, 8)
            else:
                painter.drawRect(r)
        self._paint_variant(painter, r, variant, QColor(pal["border"]))
        if self.isSelected():
            self._paint_handles(painter, r)

    def _paint_variant(self, painter, r, variant, border):
        hint = QColor(border)
        hint.setAlpha(120)
        painter.setPen(QPen(hint, 1))
        if variant == "underline":
            y = r.bottom() - 6
            painter.drawLine(int(r.left() + 6), int(y), int(r.right() - 6), int(y))
        elif variant == "imagecross":
            painter.drawLine(r.topLeft(), r.bottomRight())
            painter.drawLine(r.topRight(), r.bottomLeft())
        elif variant == "textlines":
            n = max(1, int(r.height() // 14))
            for i in range(min(n, 4)):
                yy = r.top() + 10 + i * 12
                if yy > r.bottom() - 6:
                    break
                w = r.width() - 12 if i < 3 else (r.width() - 12) * 0.5
                painter.drawLine(int(r.left() + 6), int(yy), int(r.left() + 6 + w), int(yy))
        elif variant == "dividers":
            step = max(18, int(r.height() // 4))
            yy = r.top() + step
            while yy < r.bottom() - 4:
                painter.drawLine(int(r.left() + 4), int(yy), int(r.right() - 4), int(yy))
                yy += step

    def _paint_handles(self, painter, r):
        painter.setPen(QPen(QColor("#1E6FD9"), 1))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        for cx in (r.left(), r.center().x(), r.right()):
            for cy in (r.top(), r.center().y(), r.bottom()):
                if cx == r.center().x() and cy == r.center().y():
                    continue
                painter.drawRect(QRectF(cx - HANDLE / 2, cy - HANDLE / 2, HANDLE, HANDLE))

    # -- serialization --
    def to_dict(self):
        return {"id": self.sid, "code": self.code,
                "x": int(self.pos().x()), "y": int(self.pos().y()),
                "w": int(self.size()[0]), "h": int(self.size()[1]),
                "role": self.role, "label": self.label,
                "z": self.zValue()}

    @classmethod
    def from_dict(cls, d):
        it = cls(d.get("x", 0), d.get("y", 0), d.get("w", 120), d.get("h", 60),
                 role=d.get("role", "container"), label=d.get("label", ""),
                 code=d.get("code", ""), sid=d.get("id"))
        it.setZValue(d.get("z", 0))
        return it


# ─────────────────────────────── scene ────────────────────────────────────
class WireframeScene(QGraphicsScene):
    editBegan = pyqtSignal()          # a mutation is about to happen (snapshot)
    editEnded = pyqtSignal()          # a mutation finished (push undo)
    sceneChanged = pyqtSignal()       # composition changed (refresh legend)

    def __init__(self, parent=None):
        super().__init__(0, 0, CANVAS_W, CANVAS_H, parent)
        self.grid_size = DEFAULT_GRID
        self.snap = True
        self.grid_visible = True
        self._next_id = 1
        self._next_code = 1        # 1->a, 2->b, ... 27->aa

    def new_id(self):
        sid = "s%d" % self._next_id
        self._next_id += 1
        return sid

    @staticmethod
    def _code_for(n):
        """1-indexed integer -> spreadsheet-style letters (1=a, 26=z, 27=aa)."""
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(97 + r) + s
        return s

    @staticmethod
    def _code_num(code):
        n = 0
        for ch in code:
            if "a" <= ch <= "z":
                n = n * 26 + (ord(ch) - 96)
            else:
                return 0
        return n

    def new_code(self):
        code = self._code_for(self._next_code)
        self._next_code += 1
        return code

    def snap_point(self, pt):
        if not self.snap:
            return pt
        g = self.grid_size
        return QPointF(round(pt.x() / g) * g, round(pt.y() / g) * g)

    def shapes(self):
        return [i for i in self.items() if isinstance(i, ShapeItem)]

    def changed_notify(self):
        self.sceneChanged.emit()

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        painter.fillRect(self.sceneRect(), QColor("#FBFBFD"))
        if self.grid_visible:
            g = self.grid_size
            painter.setPen(QPen(QColor("#E3E6EC"), 1))
            r = self.sceneRect()
            x = 0
            while x <= r.width():
                painter.drawLine(int(x), 0, int(x), int(r.height()))
                x += g
            y = 0
            while y <= r.height():
                painter.drawLine(0, int(y), int(r.width()), int(y))
                y += g
        painter.setPen(QPen(QColor("#9AA3B2"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.sceneRect())

    # serialize / rebuild — the basis of snapshot undo and save/load
    def serialize(self):
        shapes = sorted(self.shapes(), key=lambda s: s.zValue())
        return {"schema": SCHEMA,
                "canvas": {"w": int(self.sceneRect().width()), "h": int(self.sceneRect().height())},
                "grid": {"size": self.grid_size, "snap": self.snap, "visible": self.grid_visible},
                "shapes": [s.to_dict() for s in shapes],
                "next_id": self._next_id, "next_code": self._next_code}

    def load(self, state):
        for it in self.shapes():
            self.removeItem(it)
        grid = state.get("grid", {})
        self.grid_size = grid.get("size", DEFAULT_GRID)
        self.snap = grid.get("snap", True)
        self.grid_visible = grid.get("visible", True)
        self._next_id = state.get("next_id", 1)
        self._next_code = state.get("next_code", 1)
        maxn = maxc = 0
        for d in state.get("shapes", []):
            if not d.get("id"):
                d["id"] = self.new_id()
            if not d.get("code"):
                d["code"] = self.new_code()    # backfill codes for old files
            it = ShapeItem.from_dict(d)
            self.addItem(it)
            try:
                maxn = max(maxn, int(str(it.sid).lstrip("s")))
            except ValueError:
                pass
            maxc = max(maxc, self._code_num(it.code))
        self._next_id = max(self._next_id, maxn + 1)
        self._next_code = max(self._next_code, maxc + 1)
        self.update()
        self.sceneChanged.emit()


# ─────────────────────────────── view ─────────────────────────────────────
class WireframeView(QGraphicsView):
    """Rubber-band selection by default; arms a click-drag create gesture when
    add-mode is on; Ctrl+wheel zoom about the cursor; space/middle-drag pan."""
    created = pyqtSignal(object)      # emits a freshly created ShapeItem

    def __init__(self, scene, tab):
        super().__init__(scene)
        self._tab = tab
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMouseTracking(True)
        self._add_mode = False
        self._drawing = None          # (start_scene_pt, temp_item)
        self._panning = False

    def set_add_mode(self, on):
        self._add_mode = on
        self.setDragMode(QGraphicsView.DragMode.NoDrag if on
                         else QGraphicsView.DragMode.RubberBandDrag)
        self.setCursor(Qt.CursorShape.CrossCursor if on else Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            self._tab._report_zoom()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.MiddleButton
                or (self._add_mode is False and event.modifiers() & Qt.KeyboardModifier.AltModifier)):
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if self._add_mode and event.button() == Qt.MouseButton.LeftButton:
            sc = self.scene()
            p = sc.snap_point(self.mapToScene(event.pos()))
            item = ShapeItem(p.x(), p.y(), sc.grid_size, sc.grid_size,
                             role=self._tab.current_role(),
                             code=sc.new_code(), sid=sc.new_id())
            sc.addItem(item)
            self._drawing = (p, item)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            h = self.horizontalScrollBar(); v = self.verticalScrollBar()
            h.setValue(h.value() - int(delta.x()))
            v.setValue(v.value() - int(delta.y()))
            event.accept()
            return
        if self._drawing:
            start, item = self._drawing
            sc = self.scene()
            cur = sc.snap_point(self.mapToScene(event.pos()))
            x, y = min(start.x(), cur.x()), min(start.y(), cur.y())
            w, hgt = abs(cur.x() - start.x()), abs(cur.y() - start.y())
            item.setPos(x, y)
            item.set_size(max(sc.grid_size, w), max(sc.grid_size, hgt))
            event.accept()
            return
        self._tab._report_cursor(self.mapToScene(event.pos()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.CrossCursor if self._add_mode
                           else Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        if self._drawing:
            _, item = self._drawing
            self._drawing = None
            self.created.emit(item)     # tab wraps it in an undo command
            event.accept()
            return
        super().mouseReleaseEvent(event)


# ─────────────────────────────── undo ─────────────────────────────────────
class SnapshotCommand(QUndoCommand):
    """Whole-scene before/after snapshot. Robust and simple: undo/redo just
    rebuild the scene from serialized JSON, so no command can desync the model."""

    def __init__(self, scene, before, after, text="edit"):
        super().__init__(text)
        self._scene = scene
        self._before = before
        self._after = after
        self._applied = False          # skip the first redo() (push already did it)

    def undo(self):
        self._scene.load(self._before)

    def redo(self):
        if not self._applied:
            self._applied = True
            return
        self._scene.load(self._after)


# ─────────────────────────── side panels ──────────────────────────────────
class PropertiesPanel(QGroupBox):
    def __init__(self, tab):
        super().__init__("Properties")
        self._tab = tab
        self._item = None
        form = QFormLayout(self)
        self.role = QComboBox()
        for r in ROLE_ORDER:
            self.role.addItem(role_name(r), r)
        self.role.activated.connect(self._role_changed)
        self.code = QLabel("—")
        self.label = QLineEdit()
        self.label.editingFinished.connect(self._label_changed)
        self.sx = self._spin(); self.sy = self._spin()
        self.sw = self._spin(1); self.sh = self._spin(1)
        for s in (self.sx, self.sy, self.sw, self.sh):
            s.editingFinished.connect(self._geom_changed)
        form.addRow("Code", self.code)
        form.addRow("Role", self.role)
        form.addRow("Label", self.label)
        form.addRow("X", self.sx); form.addRow("Y", self.sy)
        form.addRow("W", self.sw); form.addRow("H", self.sh)
        self.setEnabled(False)

    def _spin(self, lo=0):
        s = QSpinBox(); s.setRange(lo, 10000); s.setSingleStep(DEFAULT_GRID); return s

    def bind(self, item):
        self._item = item
        if item is None:
            self.setEnabled(False)
            self.code.setText("—")
            return
        self.setEnabled(True)
        self.code.setText(item.code or "—")
        self.role.setCurrentIndex(ROLE_ORDER.index(item.role) if item.role in ROLE_ORDER else 0)
        self.label.setText(item.label)
        self.sx.setValue(int(item.pos().x())); self.sy.setValue(int(item.pos().y()))
        self.sw.setValue(int(item.size()[0])); self.sh.setValue(int(item.size()[1]))

    def _role_changed(self):
        if self._item:
            self._tab.apply(lambda: self._item.set_role(self.role.currentData()))

    def _label_changed(self):
        if self._item and self.label.text() != self._item.label:
            self._tab.apply(lambda: self._item.set_label(self.label.text()))

    def _geom_changed(self):
        if self._item:
            self._tab.apply(lambda: (self._item.setPos(self.sx.value(), self.sy.value()),
                                     self._item.set_size(self.sw.value(), self.sh.value())))


class LegendPanel(QGroupBox):
    """The key: one row per shape mapping its canvas CODE -> the full label."""

    def __init__(self, tab):
        super().__init__("Legend (code → label)")
        self._tab = tab
        lay = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.itemClicked.connect(self._select)
        lay.addWidget(self.list)

    def refresh(self, scene):
        self.list.clear()
        for s in sorted(scene.shapes(), key=lambda s: WireframeScene._code_num(s.code)):
            it = QListWidgetItem("%s   %s" % ((s.code or "?").ljust(3), s.label))
            it.setData(Qt.ItemDataRole.UserRole, s.sid)
            it.setToolTip("%s · %s" % (role_name(s.role), s.label))
            it.setBackground(QColor(ROLE_PALETTE[s.role]["fill"]))
            self.list.addItem(it)

    def _select(self, item):
        sid = item.data(Qt.ItemDataRole.UserRole)
        for s in self._tab.scene.shapes():
            s.setSelected(s.sid == sid)


# ─────────────────────────────── the tab ──────────────────────────────────
class wireframeTab(QWidget):
    def __init__(self, bus=None, parent=None):
        super().__init__(parent)
        self.bus = bus                 # convention only; not wired in v1
        self._path = None
        self._undo = QUndoStack(self)
        self._before = None

        self.scene = WireframeScene(self)
        self.view = WireframeView(self.scene, self)
        self.props = PropertiesPanel(self)
        self.legend = LegendPanel(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._build_toolbar())
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.view)
        right = QWidget(); rl = QVBoxLayout(right)
        rl.addWidget(self.props); rl.addWidget(self.legend); rl.addStretch(1)
        split.addWidget(right)
        split.setStretchFactor(0, 1); split.setSizes([1000, 260])
        outer.addWidget(split, 1)
        self.status = QLabel("")
        outer.addWidget(self.status)

        self.scene.editBegan.connect(self._begin)
        self.scene.editEnded.connect(self._commit)
        self.scene.sceneChanged.connect(lambda: self.legend.refresh(self.scene))
        self.scene.selectionChanged.connect(self._on_selection)
        self.view.created.connect(self._on_created)
        self.legend.refresh(self.scene)
        self._report_zoom()

    # -- toolbar --
    def _build_toolbar(self):
        tb = QToolBar()
        self.add_btn = QPushButton("▭ Add Box"); self.add_btn.setCheckable(True)
        self.add_btn.toggled.connect(self.view.set_add_mode)
        tb.addWidget(self.add_btn)
        self.role_combo = QComboBox()
        for r in ROLE_ORDER:
            self.role_combo.addItem(role_name(r), r)
        tb.addWidget(self.role_combo)
        tb.addSeparator()
        self.snap_chk = QCheckBox("Snap"); self.snap_chk.setChecked(True)
        self.snap_chk.toggled.connect(self._set_snap)
        tb.addWidget(self.snap_chk)
        self.grid_chk = QCheckBox("Grid"); self.grid_chk.setChecked(True)
        self.grid_chk.toggled.connect(self._set_grid_visible)
        tb.addWidget(self.grid_chk)
        tb.addWidget(QLabel(" cell "))
        self.grid_spin = QComboBox()
        for g in ("10", "20", "40"):
            self.grid_spin.addItem(g)
        self.grid_spin.setCurrentText("20")
        self.grid_spin.currentTextChanged.connect(self._set_grid_size)
        tb.addWidget(self.grid_spin)
        tb.addSeparator()
        for label, slot, sc in [("Dup", self.duplicate, "Ctrl+D"),
                                ("Del", self.delete_selected, "Delete"),
                                ("Undo", self._undo.undo, "Ctrl+Z"),
                                ("Redo", self._undo.redo, "Ctrl+Shift+Z"),
                                ("Fit", self.fit, None), ("100%", self.reset_zoom, None)]:
            b = QPushButton(label); b.clicked.connect(slot); tb.addWidget(b)
            if sc:
                a = QAction(self); a.setShortcut(QKeySequence(sc)); a.triggered.connect(slot)
                self.addAction(a)
        tb.addSeparator()
        for label, slot in [("New", self.new), ("Open", self.open), ("Save", self.save),
                            ("Save As", self.save_as),
                            ("Export Map", self.export_map), ("Export PNG", self.export_png)]:
            b = QPushButton(label); b.clicked.connect(slot); tb.addWidget(b)
        for sc, slot in [("Ctrl+S", self.save), ("Ctrl+O", self.open), ("Ctrl+N", self.new)]:
            a = QAction(self); a.setShortcut(QKeySequence(sc)); a.triggered.connect(slot); self.addAction(a)
        return tb

    def current_role(self):
        return self.role_combo.currentData()

    # -- undo plumbing (snapshot before/after) --
    def _begin(self):
        if self._before is None:
            self._before = self.scene.serialize()

    def _commit(self):
        if self._before is None:
            return
        after = self.scene.serialize()
        if after != self._before:
            self._undo.push(SnapshotCommand(self.scene, self._before, after))
        self._before = None
        self.legend.refresh(self.scene)
        self._on_selection()

    def apply(self, mutate):
        """Run a mutation as one undoable step."""
        self._begin()
        mutate()
        self.scene.editEnded.emit()

    # -- creation / selection --
    def _on_created(self, item):
        # the box was added live during the drag; wrap it as one undo step
        before = self.scene.serialize()
        after = before                    # 'after' == current already
        # rebuild a proper before (without this item) for correct undo
        b = {k: (v if k != "shapes" else [s for s in v if s["id"] != item.sid])
             for k, v in before.items()}
        self._undo.push(SnapshotCommand(self.scene, b, after))
        self.legend.refresh(self.scene)
        item.setSelected(True)
        item.edit_label()

    def _on_selection(self):
        sel = [i for i in self.scene.selectedItems() if isinstance(i, ShapeItem)]
        self.props.bind(sel[0] if len(sel) == 1 else None)

    def select_role(self, role):
        for s in self.scene.shapes():
            s.setSelected(s.role == role)

    # -- edits --
    def delete_selected(self):
        sel = [i for i in self.scene.selectedItems() if isinstance(i, ShapeItem)]
        if not sel:
            return
        self._begin()
        for i in sel:
            self.scene.removeItem(i)
        self.scene.editEnded.emit()

    def duplicate(self):
        sel = [i for i in self.scene.selectedItems() if isinstance(i, ShapeItem)]
        if not sel:
            return
        self._begin()
        self.scene.clearSelection()
        g = self.scene.grid_size
        for i in sel:
            d = i.to_dict()
            d["id"] = self.scene.new_id(); d["code"] = self.scene.new_code()
            d["x"] += g; d["y"] += g
            ni = ShapeItem.from_dict(d)
            self.scene.addItem(ni); ni.setSelected(True)
        self.scene.editEnded.emit()

    # -- grid/snap toggles --
    def _set_snap(self, on):
        self.scene.snap = on

    def _set_grid_visible(self, on):
        self.scene.grid_visible = on
        self.scene.update()

    def _set_grid_size(self, txt):
        try:
            self.scene.grid_size = int(txt)
        except ValueError:
            return
        self.scene.update()

    # -- view --
    def fit(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._report_zoom()

    def reset_zoom(self):
        self.view.resetTransform()
        self._report_zoom()

    def _report_zoom(self):
        z = int(self.view.transform().m11() * 100)
        self.status.setText("zoom %d%%" % z)

    def _report_cursor(self, pt):
        self.status.setText("x %d  y %d   ·   zoom %d%%"
                            % (pt.x(), pt.y(), int(self.view.transform().m11() * 100)))

    # -- file ops --
    def new(self):
        if self.scene.shapes() and QMessageBox.question(
                self, "New", "Clear the current wireframe?") != QMessageBox.StandardButton.Yes:
            return
        self._before = None
        self.scene.load({"grid": {"size": self.scene.grid_size, "snap": self.scene.snap,
                                  "visible": self.scene.grid_visible}, "shapes": []})
        self._undo.clear()
        self._path = None

    def open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open wireframe", "", "Wireframe (*.json)")
        if not path:
            return
        try:
            with open(path) as fh:
                state = json.load(fh)
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", str(exc))
            return
        self.scene.load(state)
        self._undo.clear()
        self._path = path
        self._sync_toggles()

    def _sync_toggles(self):
        self.snap_chk.setChecked(self.scene.snap)
        self.grid_chk.setChecked(self.scene.grid_visible)
        self.grid_spin.setCurrentText(str(self.scene.grid_size))

    def save(self):
        if not self._path:
            return self.save_as()
        try:
            with open(self._path, "w") as fh:
                json.dump(self.scene.serialize(), fh, indent=2)
            self.status.setText("saved %s" % self._path)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save wireframe", "wireframe.json",
                                              "Wireframe (*.json)")
        if not path:
            return
        self._path = path
        self.save()

    def export_map(self):
        """Export an annotated map: code -> {label, role, geometry}. Pairs with
        the PNG snapshot (which shows the codes) as a self-documenting deliverable."""
        path, _ = QFileDialog.getSaveFileName(self, "Export annotation map",
                                              "wireframe.map.json", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w") as fh:
                json.dump(self.annotation_map(), fh, indent=2)
            self.status.setText("exported map %s" % path)
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def annotation_map(self):
        """{ code: {label, role, x, y, w, h} } ordered by code."""
        out = {}
        for s in sorted(self.scene.shapes(), key=lambda s: WireframeScene._code_num(s.code)):
            out[s.code or "?"] = {"label": s.label, "role": s.role,
                                  "x": int(s.pos().x()), "y": int(s.pos().y()),
                                  "w": int(s.size()[0]), "h": int(s.size()[1])}
        return out

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG snapshot", "wireframe.png", "PNG (*.png)")
        if not path:
            return
        self.render_png(path)
        self.status.setText("exported %s" % path)

    def render_png(self, path, grid=False):
        """Render the canvas to a PNG. Used by tests and the Export button."""
        self.scene.clearSelection()
        prev = self.scene.grid_visible
        self.scene.grid_visible = grid
        rect = self.scene.sceneRect()
        img = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.white)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene.render(painter, QRectF(img.rect()), rect)
        painter.end()
        self.scene.grid_visible = prev
        return img.save(path)
