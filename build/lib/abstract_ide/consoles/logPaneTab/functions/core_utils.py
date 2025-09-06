from ..imports import *
# replace your AppRunner.start with this version
def append_line(self, line: str):
    try:
        self.view.appendPlainText(line.rstrip("\n"))
        if self.auto_scroll.isChecked():
            self.view.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    except Exception as e:
        print(f"{e}")
