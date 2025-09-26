import os, json, subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QListWidget,
    QTabWidget, QLineEdit, QLabel, QFormLayout, QScrollArea, QListWidgetItem
    
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

ROOT = "/var/www/modules/packages"
INSPECT_MJS = "/var/www/modules/packages/inspect-dts.mjs"  # expects to print JSON: [{name, params:[{name,type},...]}, ...]

def _node_ok():
    try:
        r = subprocess.run(["node", "-v"], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False

def _json_or_str(s: str):
    s = s.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return s

class testRunnerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Abstract Packages Explorer")
        root = QHBoxLayout(self)

        # left: packages as tabs
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # right: dynamic input + log
        right = QVBoxLayout()

        self.input_form = QFormLayout()
        self.input_widget = QWidget()
        self.input_widget.setLayout(self.input_form)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.input_widget)
        right.addWidget(scroll, 2)

        # Raw JSON args (optional override)
        self.raw_args = QLineEdit()
        self.raw_args.setPlaceholderText('Optional raw JSON args array, e.g. ["foo", 123, {"a":1}]')
        right.addWidget(self.raw_args)

        self.btn_run = QPushButton("Run Selected Function")
        self.btn_run.clicked.connect(self.run_function)
        right.addWidget(self.btn_run)

        self.open_dir = QPushButton("Open Packages Dir")
        self.open_dir.clicked.connect(self.open_item)
        right.addWidget(self.open_dir)

        # 🔥 new button
        self.open_fn_btn = QPushButton("Open Function File")
        self.open_fn_btn.clicked.connect(self.open_function_file)
        right.addWidget(self.open_fn_btn)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        right.addWidget(self.log, 3)

        right_container = QWidget()
        right_container.setLayout(right)
        root.addWidget(right_container, 2)

        self.pkg_func_lists: dict[str, QListWidget] = {}
        self.current_pkg: str | None = None
        self.current_fn: str | None = None
        self.arg_edits: list[QLineEdit] = []

        if not _node_ok():
            self.log.append("❌ Node.js not found on PATH. Introspection and execution will fail.")
        self.load_all()

    # ---------- Loading (merged) ----------
    def load_all(self):
        """
        For each package under ROOT:
          1) If dist/index.d.ts exists → use inspect-dts.mjs to get [{name, params}]
          2) Else if dist/index.js exists → get exports and wrap as dicts with empty params
        """
        pkgs = sorted([d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d))])
        for pkg in pkgs:
            items = self._load_pkg_functions(pkg)
            if not items:
                continue

            lw = QListWidget()
            for fn in items:
                it = QListWidgetItem(fn["name"])
                it.setData(Qt.ItemDataRole.UserRole, fn)  # normalized dict
                lw.addItem(it)

            # Avoid late-binding: use default arg in lambda
            lw.itemClicked.connect(lambda item, _pkg=pkg: self.show_inputs(_pkg, item.data(Qt.ItemDataRole.UserRole)))
            self.pkg_func_lists[pkg] = lw
            self.tabs.addTab(lw, pkg)
    def open_item(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(ROOT))

    def open_function_file(self):
        """Try to open the file containing the currently selected function."""
        if not self.current_pkg or not self.current_fn:
            self.log.append("⚠️ No function selected")
            return

        pkg_dir = os.path.join(ROOT, self.current_pkg)

        # 1) prefer source folder
        src_dir = os.path.join(pkg_dir, "src")
        target_file = None

        if os.path.isdir(src_dir):
            # brute-force search for function name in .ts/.tsx
            for root, _, files in os.walk(src_dir):
                for f in files:
                    if f.endswith((".ts", ".tsx")):
                        path = os.path.join(root, f)
                        try:
                            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                                if self.current_fn in fh.read():
                                    target_file = path
                                    break
                        except Exception:
                            continue
                if target_file:
                    break

        # 2) fallback to dist/index.js
        if not target_file:
            dist_js = os.path.join(pkg_dir, "dist", "index.js")
            if os.path.exists(dist_js):
                target_file = dist_js

        if target_file:
            self.log.append(f"📂 Opening file for {self.current_fn}: {target_file}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(target_file))
        else:
            self.log.append(f"❌ Could not locate file for {self.current_fn}")
    def _load_pkg_functions(self, pkg: str) -> list[dict]:
        pkg_dir   = os.path.join(ROOT, pkg)
        dist_js   = os.path.join(pkg_dir, "dist", "index.js")
        dist_cjs  = os.path.join(pkg_dir, "dist", "index.cjs")
        dts_file  = os.path.join(pkg_dir, "dist", "index.d.ts")

        # Prefer d.ts (typed)
        if os.path.exists(dts_file) and os.path.exists(INSPECT_MJS):
            try:
                r = subprocess.run(["node", INSPECT_MJS, pkg_dir], capture_output=True, text=True)
                if r.returncode == 0:
                    data = json.loads(r.stdout)
                    # Normalize: ensure {name, params: [{name,type}]}
                    out = []
                    for entry in data:
                        name = entry.get("name")
                        if not name:
                            continue
                        params = entry.get("params", [])
                        out.append({"name": name, "params": params})
                    if out:
                        return out
                else:
                    self.log.append(f"⚠️ {pkg}: inspect-dts failed:\n{r.stderr.strip()}")
            except Exception as e:
                self.log.append(f"⚠️ {pkg}: inspect-dts error: {e}")

        # Fallback: ESM/CJS exports
        entry_js = dist_js if os.path.exists(dist_js) else (dist_cjs if os.path.exists(dist_cjs) else None)
        if not entry_js:
            return []

        try:
            if entry_js.endswith(".cjs"):
                # CommonJS path: require then Object.keys(module.exports)
                script = f"""
const m = require("{entry_js.replace('"','\\"')}");
console.log(JSON.stringify(Object.keys(m)));
"""
                r = subprocess.run(["node", "-e", script], capture_output=True, text=True)
            else:
                # ESM path: import *
                script = f"""
import * as pkg from 'file://{entry_js}';
console.log(JSON.stringify(Object.keys(pkg)));
"""
                r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)

            if r.returncode != 0:
                self.log.append(f"⚠️ {pkg}: export introspection failed:\n{r.stderr.strip()}")
                return []

            names = json.loads(r.stdout.strip())
            return [{"name": n, "params": []} for n in names if isinstance(n, str)]
        except Exception as e:
            self.log.append(f"⚠️ {pkg}: export introspection error: {e}")
            return []

    # ---------- UI wiring ----------
    def show_inputs(self, pkg: str, fn: dict):
        # Clear old inputs
        while self.input_form.rowCount():
            self.input_form.removeRow(0)

        self.current_pkg = pkg
        self.current_fn  = fn.get("name")
        self.arg_edits = []

        params = fn.get("params", [])
        if not isinstance(params, list):
            params = []

        # Build per-param fields
        for p in params:
            pname = p.get("name", "")
            ptype = p.get("type", "any")
            edit = QLineEdit()
            edit.setPlaceholderText(ptype)
            self.input_form.addRow(QLabel(f"{pname} ({ptype}):"), edit)
            self.arg_edits.append(edit)

        # Clear raw args when switching functions
        self.raw_args.clear()

    def open_item(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(ROOT))

    # ---------- Runner ----------
    def _resolve_entry(self, pkg: str) -> tuple[str, bool]:
        """Return (entry_path, is_esm)"""
        pkg_dir  = os.path.join(ROOT, pkg)
        dist_js  = os.path.join(pkg_dir, "dist", "index.js")
        dist_cjs = os.path.join(pkg_dir, "dist", "index.cjs")
        if os.path.exists(dist_js):
            return dist_js, True
        if os.path.exists(dist_cjs):
            return dist_cjs, False
        return "", True

    def run_function(self):
        if not self.current_pkg or not self.current_fn:
            self.log.append("⚠️ No function selected")
            return

        entry, is_esm = self._resolve_entry(self.current_pkg)
        if not entry:
            self.log.append(f"❌ No entry file found for {self.current_pkg}")
            return

        # Build args
        # 1) Raw JSON override if provided
        args_list = []
        raw = self.raw_args.text().strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    self.log.append("❌ Raw args must be a JSON array")
                    return
                args_list = parsed
            except Exception as e:
                self.log.append(f"❌ Raw args invalid JSON: {e}")
                return
        else:
            # 2) Collect from per-param fields; JSON parse when possible, else use string
            for edit in self.arg_edits:
                val = _json_or_str(edit.text())
                if val is not None:
                    args_list.append(val)

        args_json = json.dumps(args_list)

        if is_esm:
            script = f"""
import * as pkg from 'file://{entry}';
(async () => {{
  try {{
    const fn = pkg["{self.current_fn}"];
    if (typeof fn !== 'function') {{
      console.error("ERR", "Export not a function: {self.current_fn}");
      return;
    }}
    const result = await fn(...{args_json});
    console.log(JSON.stringify(result));
  }} catch (err) {{
    console.error("ERR", err && (err.message || String(err)));
  }}
}})();
"""
            cmd = ["node", "--input-type=module", "-e", script]
        else:
            # CJS
            script = f"""
const pkg = require("{entry.replace('"','\\"')}");
(async () => {{
  try {{
    const fn = pkg["{self.current_fn}"];
    if (typeof fn !== 'function') {{
      console.error("ERR", "Export not a function: {self.current_fn}");
      return;
    }}
    const result = await fn(...{args_json});
    console.log(JSON.stringify(result));
  }} catch (err) {{
    console.error("ERR", err && (err.message || String(err)));
  }}
}})();
"""
            cmd = ["node", "-e", script]

        result = subprocess.run(cmd, capture_output=True, text=True)
        out = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
        self.log.append(f"▶️ {self.current_pkg}:{self.current_fn}({args_json})\n{out.strip() or '(no output)'}")
