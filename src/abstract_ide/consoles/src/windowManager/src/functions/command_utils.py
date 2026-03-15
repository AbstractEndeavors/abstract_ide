from .imports import *

class CommandUtilsMixin:

    def run_command(self, cmd: str) -> str:

        try:

            result = subprocess.run(
                cmd,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                check=True
            )

            return result.stdout.strip()

        except subprocess.CalledProcessError as exc:

            self.statusBar().showMessage(
                f"Command error: {exc}", 5000
            )

            return ""
