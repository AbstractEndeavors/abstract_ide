from ..imports import *
# ---------------- shell helpers ----------------
def run_command(self, cmd: str) -> str:
    """Run *cmd* in a shell and return stdout (or "" on failure)."""
    try:
        out = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        ).stdout.strip()
        return out
    except subprocess.CalledProcessError as exc:
        self.statusBar().showMessage(f"Error: {exc}", 5000)
        return ""
