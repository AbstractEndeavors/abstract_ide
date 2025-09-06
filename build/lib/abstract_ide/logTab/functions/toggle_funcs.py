def _toggle_pause(self, checked: bool):
    # simplest pause: disable the editor to avoid redraw/scroll, cheap and effective
    self._paused = checked
    self.view.setDisabled(checked)
