from .imports import *

class FileUtilsMixin:

    def open_file(self) -> None:

        path, _ = QFileDialog.getOpenFileName(self, "Open file")
        if not path:
            return

        base = os.path.basename(path).lower()

        self.refresh()

        for win_id, pid, title, *_ in self.windows:

            if title.lower().endswith(base):

                self.run_command(f"xdotool windowactivate {win_id}")
                self.statusBar().showMessage(
                    f"Activated existing window for {base}", 3000
                )
                return

        self.run_command(f"xdg-open '{path}' &")

        time.sleep(1.5)

        self.refresh()

        self.statusBar().showMessage(f"Opened {base}", 3000)
