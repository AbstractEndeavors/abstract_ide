from ..imports import *
# ---------------- smart file opener ----------------
def open_file(self) -> None:
    path, _ = QFileDialog.getOpenFileName(self, "Open file")
    if not path:
        return
    base = os.path.basename(path).lower()
    self.refresh()  # ensure latest list
    for win_id, pid, title, *_ in self.windows:
        if base in title.lower():
            # bring to front
            self.run_command(f"xdotool windowactivate {win_id}")
            self.statusBar().showMessage(f"Activated existing window for {base}", 3000)
            return
    # not found – open new
    self.run_command(f"xdg-open '{path}' &")  # async launch
    # give the app a moment to create its window, then refresh
    time.sleep(1.5)
    self.refresh()
    self.statusBar().showMessage(f"Opened {base}", 3000)

