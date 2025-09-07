from .imports import *

class WrappingGrid(QWidget):
    """
    A simple, predictable grid that wraps items across rows based on the
    current width. Ideal for lots of small 'function' buttons.

    Key behaviors:
      - Recomputes columns on resize (height-for-width feel).
      - Optional min item width and max columns constraints.
      - Horizontal expansion; vertical grows as needed.
    """
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        h_spacing: int = 8,
        v_spacing: int = 6,
        margins: Union[int, Sequence[int]] = 0,
        min_item_width: Optional[int] = None,
        max_cols: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setHorizontalSpacing(h_spacing)
        self.grid.setVerticalSpacing(v_spacing)
        if isinstance(margins, int):
            self.grid.setContentsMargins(margins, margins, margins, margins)
        else:
            ml, mt, mr, mb = (list(margins) + [0, 0, 0, 0])[:4]
            self.grid.setContentsMargins(ml, mt, mr, mb)

        self._widgets: list[QWidget] = []
        self._min_item_width = min_item_width
        self._max_cols = max_cols

        # Expand horizontally so the grid can actually wrap.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    # ---------------------------
    # Public API (accouterments)
    # ---------------------------
    def addWidget(self, w: QWidget) -> None:  # noqa: N802 (Qt-compatible name)
        self._widgets.append(w)
        self._relayout()

    def addWidgets(self, widgets: Iterable[QWidget]) -> None:
        self._widgets.extend(widgets)
        self._relayout()

    def addButtons(
        self,
        names: Iterable[Union[str, tuple[str, Optional[callable]]]],
    ) -> list[QPushButton]:
        """
        Convenience: create QPushButtons and add them.
        Accepts: ["Run","Build"] or [("Run", on_run), ("Build", on_build)]
        """
        made: list[QPushButton] = []
        for entry in names:
            if isinstance(entry, tuple):
                text, cb = entry[0], (entry[1] if len(entry) > 1 else None)
            else:
                text, cb = str(entry), None
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            if cb is not None:
                btn.clicked.connect(cb)  # type: ignore[arg-type]
            made.append(btn)
            self.addWidget(btn)
        return made

    def clear(self) -> None:
        """Remove all widgets (keeps instances alive; caller may re-parent/dispose)."""
        self._widgets.clear()
        while self.grid.count():
            self.grid.takeAt(0)
        self.update()

    def setMinItemWidth(self, px: Optional[int]) -> None:
        self._min_item_width = px
        self._relayout()

    def setMaxCols(self, n: Optional[int]) -> None:
        self._max_cols = n
        self._relayout()

    def setSpacing(self, h: Optional[int] = None, v: Optional[int] = None) -> None:
        if h is not None:
            self.grid.setHorizontalSpacing(h)
        if v is not None:
            self.grid.setVerticalSpacing(v)
        self._relayout()

    # ---------------------------
    # QWidget overrides
    # ---------------------------
    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        self._relayout()

    # ---------------------------
    # Internal layout
    # ---------------------------
    def _relayout(self) -> None:
        # Clear grid positions but keep widgets
        while self.grid.count():
            self.grid.takeAt(0)
        if not self._widgets:
            return

        margins = self.grid.contentsMargins()
        avail_w = max(1, self.width() - (margins.left() + margins.right()))
        hsp = self.grid.horizontalSpacing()
        hsp = 0 if hsp is None else max(0, hsp)

        item_w = self._min_item_width or max(1, self._typical_item_width())
        cols = max(1, (avail_w + hsp) // (item_w + hsp))
        if self._max_cols is not None:
            cols = max(1, min(cols, self._max_cols))

        for i, w in enumerate(self._widgets):
            r = i // cols
            c = i % cols
            self.grid.addWidget(w, r, c)

    def _typical_item_width(self) -> int:
        # Use the widest sizeHint among the first few items for stability.
        sample = self._widgets[:8] if len(self._widgets) > 8 else self._widgets
        return max((w.sizeHint().width() for w in sample), default=80)

