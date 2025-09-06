from ...imports import *

# ── click handlers ───────────────────────────────────────────────────────


def _pick_build_cmd(self, project_dir: str=None):
    # choose yarn/pnpm/npm by lockfile
    project_dir = project_dir or self.path_in
    if os.path.exists(os.path.join(project_dir, "yarn.lock")):
        return "yarn", ["build"]
    if os.path.exists(os.path.join(project_dir, "pnpm-lock.yaml")):
        return "pnpm", ["build"]
    return "npm", ["run", "build"]

def _run_build_qprocess(self, project_dir: str=None):
    # keep GUI responsive
    project_dir = project_dir or self.path_in
    self.proc = QProcess(self)
    self.proc.setWorkingDirectory(project_dir)
    self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

    # Ensure PATH is sane inside QProcess (common issue with GUI apps)
    env = QProcessEnvironment.systemEnvironment()
    # Augment PATH with common user bins and nvm locations
    path = env.value("PATH") or ""
    extras = [
        os.path.expanduser("~/.local/bin"),
        os.path.expanduser("~/.yarn/bin"),
        os.path.expanduser("~/.config/yarn/global/node_modules/.bin"),
        "/usr/local/bin", "/usr/bin", "/bin",
    ]
    # include nvm default if present
    nvm_default = os.path.expanduser("~/.nvm/versions/node")
    if os.path.isdir(nvm_default):
        # grab the highest version bin
        try:
            versions = sorted(os.listdir(nvm_default))
            if versions:
                extras.insert(0, os.path.join(nvm_default, versions[-1], "bin"))
        except Exception:
            pass
    env.insert("PATH", ":".join(extras + [path]))
    self.proc.setProcessEnvironment(env)

    tool, args = self._pick_build_cmd(project_dir)
    self.append_log(f"[build] tool={tool} args={' '.join(args)}\n")

    # build script as a temp file so we can reproduce it outside the GUI
    sh = f'''
set -exo pipefail
cd {shlex.quote(project_dir)}
if [ -s "$HOME/.nvm/nvm.sh" ]; then . "$HOME/.nvm/nvm.sh"; fi
command -v corepack >/dev/null 2>&1 && corepack enable >/dev/null 2>&1 || true
echo "[env] PATH=$PATH"
node -v || true; npm -v || true; yarn -v || true; pnpm -v || true
test -f package.json || (echo ":: No package.json in $(pwd)"; exit 66)
{ "yarn install --frozen-lockfile" if tool=="yarn" else ("pnpm install --frozen-lockfile" if tool=="pnpm" else "npm ci") }
{tool} {" ".join(args)}
'''.strip()

    # write the script to /tmp and chmod +x
    script_path = os.path.join(tempfile.gettempdir(), f"react-build-{os.getpid()}.sh")
    with open(script_path, "w") as _f:
        _f.write(sh + "\n")
    os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    self.append_log(f"[build] script -> {script_path}\n")

    # wire output/finish/error (Qt6 signal enums)
    self.proc.readyRead.connect(self._on_build_output)  # MergedChannels
    self.proc.finished.connect(self._on_build_finished)
    self.proc.errorOccurred.connect(self._on_build_error)

    self.run_btn.setEnabled(False)
    # run the temp script via bash -lc (MergedChannels collects stderr too)
    self.proc.setProgram("bash")
    self.proc.setArguments(["-lc", f"bash {shlex.quote(script_path)} 2>&1"])
    self.proc.start()

def _on_build_finished(self, code: int, status):
    # status is QProcess.ExitStatus
    self.append_log(f"\n\n[build] exited with code {code}\n")
    if code in (66, 67):
        hint = "No package.json" if code == 66 else "No scripts.build in package.json"
        self.append_log(f"[build] preflight failed: {hint}\n")
    self.run_btn.setEnabled(True)
    # One last sync (in case the final lines arrived very late)
    self.set_last_output(self.last_output)

def _on_build_output(self):
     try:
         chunk = bytes(self.proc.readAll()).decode("utf-8", "ignore")
         if chunk:
             # accumulate full log text
             self.last_output = (self.last_output or "") + chunk
             # update raw log view according to current filter choice
             self.apply_log_filter()
             # parse and refresh lists
             
             
             
             
             # local tiny formatter to avoid any circular imports
             def _fmt(e: dict) -> str:
                code = f" {e['code']}" if e.get('code') else ""
                return f"{e['severity'].upper()}{code}: {e['path']}:{e['line']}:{e['col']} — {e['message']}"
             self.set_last_output(self.last_output)
             # also mirror to logger
             logging.getLogger("reactRunner.build").info(chunk.rstrip("\n"))
     except Exception:
         self.append_log("readAllStandardOutput error:\n" + traceback.format_exc() + "\n")


def _on_build_error(self, err):
    # err is QProcess.ProcessError
    self.append_log(f"\n[build] QProcess error: {err} (0=FailedToStart,1=Crashed,2=TimedOut,3=WriteError,4=ReadError,5=Unknown)\n")
    self.run_btn.setEnabled(True)
    # One last sync (in case the final lines arrived very late)
    self.set_last_output(self.last_output)

def show_error_for_item(self, item):
    info = item.text()
    try:
        path, line, col = self._parse_item(info)
        if self.cb_try_alt_ext.isChecked():
            path = resolve_alt_ext(path, self.path_in.text().strip())
        # open in embedded editor instead of VS Code
        self._editor_open_file(path, line, col)
        snippet = self._extract_errors_for_file(self.last_output, path, self.path_in.text().strip())
        self._replace_log(snippet if snippet else f"(No specific lines found for {path})\n\n{self.last_output}")
    except Exception:
        self.append_log("show_error_for_item error:\n" + traceback.format_exc() + "\n")

