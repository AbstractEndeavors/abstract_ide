import os, shutil, subprocess
import tempfile
import os

# ------------------------------
#  Helpers: search executables
# ------------------------------

def search_directories(base_dirs, names):
    for d in base_dirs:
        if not os.path.isdir(d):
            continue
        for name in names:
            full = os.path.join(d, name)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                return full
    return None


def search_nvm(names):
    """Search ~/.nvm installations for node/npm/npx/tsx globally installed."""
    home = os.path.expanduser("~")
    nvm_root = os.path.join(home, ".nvm", "versions", "node")
    if not os.path.isdir(nvm_root):
        return None

    for version in os.listdir(nvm_root):
        bin_dir = os.path.join(nvm_root, version, "bin")
        if not os.path.isdir(bin_dir):
            continue
        exe = search_directories([bin_dir], names)
        if exe:
            return exe

    return None


def search_path(names):
    for name in names:
        p = shutil.which(name)
        if p:
            return p
    return None


def search_login_shell(names):
    """Ask a login shell where node is — safest fallback."""
    try:
        out = subprocess.check_output(
            ["bash", "-lc", f"which {names[0]}"],
            text=True
        ).strip()
        if os.path.isfile(out):
            return out
    except Exception:
        pass
    return None


def find_executable(names):
    """
    Try:
      1. PATH
      2. common dirs
      3. NVM
      4. login shell
    """
    found = search_path(names)
    if found:
        return found

    COMMON = [
        "/usr/bin",
        "/usr/local/bin",
        "/bin",
        "/opt/homebrew/bin",
        "/opt/local/bin",
        "/snap/bin",
        "/home/linuxbrew/.linuxbrew/bin",
    ]
    found = search_directories(COMMON, names)
    if found:
        return found

    found = search_nvm(names)
    if found:
        return found

    found = search_login_shell(names)
    if found:
        return found

    return None


# ------------------------------
#  Preload executables
# ------------------------------

SUB_PRE_JS = {"node": "exe", "npm": "cmd", "npx": "cmd", "tsx": None}
SUB_JS = {}

for key, value in SUB_PRE_JS.items():
    names = [key]
    if value:
        names.append(f"{key}.{value}")
    SUB_JS[key] = find_executable(names)


def ensure_node_exists():
    if not SUB_JS.get('node'):
        print("Node.js not found on this system")
ensure_node_exists()


# ------------------------------
#  ADD GLOBAL TSX SUPPORT
# ------------------------------

def _inject_env(env: dict) -> dict:
    """
    Ensures PATH + NODE_PATH include global NVM locations,
    so global 'tsx' works everywhere.
    """
    node_path = SUB_JS.get("node")
    if node_path:
        version_bin = os.path.dirname(node_path)
        env["PATH"] = version_bin + ":" + env.get("PATH", "")

        # Find global node_modules under this NVM version
        version_root = os.path.dirname(os.path.dirname(version_bin))
        nm = os.path.join(version_root, "lib", "node_modules")
        if os.path.isdir(nm):
            env["NODE_PATH"] = nm

    return env


# ------------------------------
#  Process execution
# ------------------------------

def runSubProcess(*cmds, **kwargs):
    for cmd in cmds:
        if isinstance(cmd, list):
            # rewrite node/npm/npx/tsx
            k = cmd[0]
            if k in SUB_JS:       # key in resolver
                cmd[0] = SUB_JS[k]
            elif k in ("node", "npm", "npx", "tsx"):  
                # imported names may shadow resolver names → force mapping
                mapped = SUB_JS.get(k)
                if mapped:
                    cmd[0] = mapped


            # Patch environment to include NVM paths
            env = kwargs.get("env", os.environ.copy())
            env = _inject_env(env)
            kwargs["env"] = env
            
            return subprocess.run(cmd, **kwargs)

    raise ValueError("runSubProcess: no valid commands provided")


# ------------------------------
#  Node helpers
# ------------------------------

def node_cmd(*, esm: bool, need_tsx: bool):
    cmd = [SUB_JS["node"]]

    if need_tsx:
        tsx = SUB_JS.get("tsx")
        if tsx:
            cmd += ["--loader", tsx]
        else:
            cmd += ["--loader", "tsx"]

    if esm:
        cmd.append("--input-type=module")

    return cmd


import tempfile
import os

def run_node_script(cmd, script, *, esm=True, cwd=None,
                    capture_output=True, text=True):
    """
    Executes Node with a mode-matching temporary file:
      - esm=True  -> temp .mjs
      - esm=False -> temp .cjs
    This prevents require() errors in ESM and import errors in CJS.
    """

    # pick extension based on mode
    ext = ".mjs" if esm else ".cjs"

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=ext) as f:
        f.write(script)
        temp_path = f.name

    try:
        return runSubProcess(
            cmd + [temp_path],
            capture_output=capture_output,
            text=text,
            cwd=cwd
        )
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass

# ------------------------------
#  Utility
# ------------------------------

def find_project_root(path):
    path = os.path.abspath(path)
    while path != "/":
        if os.path.isfile(os.path.join(path, "package.json")):
            return path
        path = os.path.dirname(path)
    return None
