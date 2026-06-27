import os
import subprocess
import shlex

def resolve_directory_input(path: str) -> str:
    """
    Resolve a directory input that may be:
      - local path
      - symlink
      - GVFS-mounted SFTP
      - sftp:// URL (auto-mount via gio)

    Returns a normalized local directory path.
    Raises ValueError if it cannot be resolved.
    """
    if not path:
        raise ValueError("Empty directory path")

    path = path.strip()

    # Case 1: already a valid local directory
    expanded = os.path.realpath(os.path.expanduser(path))
    if os.path.isdir(expanded):
        return expanded

    # Case 2: sftp:// URL → try GVFS mount
    if path.startswith("sftp://"):
        try:
            subprocess.run(
                ["gio", "mount", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

            # Ask gio where it mounted it
            proc = subprocess.run(
                ["gio", "info", path],
                capture_output=True,
                text=True,
            )

            for line in proc.stdout.splitlines():
                if "local path:" in line:
                    local_path = line.split("local path:", 1)[1].strip()
                    local_path = os.path.realpath(local_path)
                    if os.path.isdir(local_path):
                        return local_path

        except Exception as e:
            raise ValueError(f"Failed to resolve SFTP path: {path}") from e

    raise ValueError(f"Directory could not be resolved: {path}")
