from ..imports import *
def open_item(path):
        #path = "self.path_in or self._base_path()"
        path = path or os.getcwd()
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def _have_babel(self,cwd=None) -> bool:
        #cwd = self._base_path()
        script = "require('@babel/parser'); require('@babel/traverse'); console.log('OK')"
        r = subprocess.run(["node", "-e", script], capture_output=True, text=True, cwd=cwd)
        return r.returncode == 0 and "OK" in (r.stdout or "")

def _run_node_script(cmd: list[str], script: str,cwd=None,capture_output=True, text=True):
        """
        Run node with our project root as cwd so dev-deps resolve.
        """
        return subprocess.run(
            cmd + ["-e", script],
            capture_output=capture_output, text=text,
            cwd=cwd
        )

def _node_cmd(*, esm: bool, need_tsx: bool) -> list[str]:
        """
        Node 20+: use --import=tsx instead of --loader.
        need_tsx: True for .ts/.tsx entries; False otherwise.
        """
        cmd = ["node"]
        if need_tsx:
            cmd.append("--import=tsx")
        if esm:
            cmd.append("--input-type=module")
        return cmd

def _looks_server_safe(self, file_path: str) -> bool:
        """
        Quick sniff to avoid trying to execute browser-only modules.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                head = fh.read(4096)
        except Exception:
            return True
        browser_markers = (" from 'react'", ' from "react"', "window.", "document.", "navigator.")
        server_hint = file_path.endswith((".server.ts", ".server.tsx", ".server.js", ".server.mjs"))
        return server_hint or not any(m in head for m in browser_markers)

    

def _inspect_exports_regex(self, file_path: str) -> list[dict]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                src = fh.read()
        except Exception:
            return []
        out = []
        for m in _export_fn_re.finditer(src):
            name = m.group(1) or m.group(3)
            params_src = (m.group(2) or m.group(4) or "").strip()
            pnames = [p.strip().split(":")[0].split("=")[0] for p in params_src.split(",") if p.strip()]
            out.append({"name": name, "params": [{"name": n, "type": "any"} for n in pnames if n]})
        return out

    

def _group_key_from(self, scan_root: str, file_path: str) -> str:
        rel = os.path.relpath(file_path, scan_root)
        parts = rel.split(os.sep)
        return parts[0] if len(parts) > 1 else "(root)"

    

def _have_babel(self) -> bool:
        """Return True if @babel/parser and @babel/traverse are resolvable."""
        script = "require('@babel/parser'); require('@babel/traverse'); console.log('OK')"
        r = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        return r.returncode == 0 and "OK" in (r.stdout or "")

    

def _inspect_exports_babel(self, file_path: str) -> list[dict]:
        """
        Use Babel to parse a file and return [{name, params}] of exported functions.
        Requires @babel/parser and @babel/traverse.
        """
        js = rf"""
    const fs = require('fs');
    const p  = {json.dumps(file_path)};
    const code = fs.readFileSync(p, 'utf8');

    let parser, traverse;
    try {{
      parser = require('@babel/parser');
      traverse = require('@babel/traverse').default;
    }} catch (e) {{
      console.log('[]');
      process.exit(0);
    }}

    const ast = parser.parse(code, {{
      sourceType: 'module',
      plugins: [
        'typescript','jsx','classProperties','decorators-legacy',
        'exportDefaultFrom','exportNamespaceFrom','dynamicImport','topLevelAwait'
      ]
    }});

    const out = [];
    function paramNames(params) {{
      return (params || []).map((q) => {{
        if (q.type === 'Identifier') return q.name;
        if (q.type === 'AssignmentPattern' && q.left && q.left.type === 'Identifier') return q.left.name;
        if (q.type === 'RestElement' && q.argument && q.argument.type === 'Identifier') return '...' + q.argument.name;
        return '_';
      }});
    }}

    traverse(ast, {{
      ExportNamedDeclaration(path) {{
        const decl = path.node.declaration;
        if (!decl) return;
        if (decl.type === 'FunctionDeclaration') {{
          const name = decl.id ? decl.id.name : 'default';
          out.push({{ name, params: paramNames(decl.params) }});
        }} else if (decl.type === 'VariableDeclaration') {{
          for (const d of decl.declarations) {{
            if (!d.id || d.id.type !== 'Identifier') continue;
            const name = d.id.name;
            const init = d.init;
            if (!init) continue;
            if (init.type === 'ArrowFunctionExpression' || init.type === 'FunctionExpression') {{
              out.push({{ name, params: paramNames(init.params) }});
            }}
          }}
        }}
      }},
      ExportDefaultDeclaration(path) {{
        const decl = path.node.declaration;
        if (!decl) return;
        if (['FunctionDeclaration','ArrowFunctionExpression','FunctionExpression'].includes(decl.type)) {{
          const name = decl.id ? decl.id.name : 'default';
          const params = decl.params ? paramNames(decl.params) : [];
          out.push({{ name, params }});
        }}
      }},
    }});

    console.log(JSON.stringify(out));
    """
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True)
        if r.returncode != 0:
            return []
        try:
            data = json.loads(r.stdout or "[]")
            # normalize shape
            out = []
            for e in data:
                name = e.get("name")
                if not name:
                    continue
                params = e.get("params") or []
                out.append({"name": name, "params": [{"name": n, "type": "any"} for n in params]})
            return out
        except Exception:
            return []
    



def _introspect_file_exports(file_path: str,cwd=None,esm=True, capture_output=True, text=True) -> list[str]:
        need_tsx = file_path.endswith((".ts", ".tsx"))
        # ESM first

        #cwd = self._base_path()
        script_esm = f"import * as m from 'file://{file_path}'; console.log(JSON.stringify(Object.keys(m)));"
        r = subprocess.run(_node_cmd(esm=esm, need_tsx=need_tsx) + ["-e", script_esm],
                           capture_output=capture_output, text=text, cwd=cwd)
        if r.returncode == 0:
            try:
                return [n for n in json.loads(r.stdout.strip()) if isinstance(n, str)]
            except Exception:
                pass
        # CJS fallback
        script_cjs = f"""
    try {{
      const m = require("{file_path.replace('"','\\"')}");
      console.log(JSON.stringify(Object.keys(m)));
    }} catch (e) {{
      console.log("[]");
    }}
    """
        r = subprocess.run(_node_cmd(esm=False, need_tsx=need_tsx) + ["-e", script_cjs],
                           capture_output=capture_output, text=text, cwd=cwd)
        try:
            return [n for n in json.loads((r.stdout or "[]").strip()) if isinstance(n, str)]
        except Exception:
            return []

def _install_analyzers(cwd=None, capture_output=True, text=True):
        #cwd = self._base_path()
        cmd = ["npm", "i", "-D", "@babel/parser", "@babel/traverse", "tsx"]
        r = subprocess.run(cmd, cwd=cwd, capture_output=capture_output, text=text)
        if r.returncode == 0:
            self.log.append("✅ Installed @babel/parser, @babel/traverse, tsx")
        else:
            self.log.append(f"❌ Install failed:\n{r.stderr}")

def _resolve_entry(pkg: str,cwd=None) -> tuple[str, bool]:
        """Return (entry_path, is_esm)"""
        cwd = cwd or os.getcwd()
        pkg_dir  = os.path.join(cwd, pkg)
        dist_js  = os.path.join(pkg_dir, "dist", "index.js")
        dist_cjs = os.path.join(pkg_dir, "dist", "index.cjs")
        if os.path.exists(dist_js):
            return dist_js, True
        if os.path.exists(dist_cjs):
            return dist_cjs, False
        return "", True


    

    


def _inspect_exports_babel(self, file_path: str) -> list[dict]:
        js = rf"""
    const fs = require('fs');
    const p  = {json.dumps(file_path)};
    const code = fs.readFileSync(p, 'utf8');
    let parser, traverse;
    try {{
      parser = require('@babel/parser');
      traverse = require('@babel/traverse').default;
    }} catch (e) {{
      console.log('[]'); process.exit(0);
    }}
    const ast = parser.parse(code, {{
      sourceType: 'module',
      plugins: ['typescript','jsx','classProperties','decorators-legacy',
                'exportDefaultFrom','exportNamespaceFrom','dynamicImport','topLevelAwait']
    }});
    const out = [];
    const paramNames = (ps)=> (ps||[]).map(q => q?.name || (q?.left?.name) || (q?.argument?.name && ('...'+q.argument.name)) || '_');
    traverse(ast, {{
      ExportNamedDeclaration(path) {{
        const d = path.node.declaration;
        if (!d) return;
        if (d.type === 'FunctionDeclaration') {{
          out.push({{name: d.id?d.id.name:'default', params: paramNames(d.params)}});
        }} else if (d.type === 'VariableDeclaration') {{
          for (const q of d.declarations) {{
            if (!q.id || q.id.type !== 'Identifier') continue;
            const name = q.id.name, init = q.init;
            if (!init) continue;
            if (init.type === 'ArrowFunctionExpression' || init.type === 'FunctionExpression') {{
              out.push({{name, params: paramNames(init.params)}});
            }}
          }}
        }}
      }},
      ExportDefaultDeclaration(path) {{
        const d = path.node.declaration;
        if (!d) return;
        if (['FunctionDeclaration','ArrowFunctionExpression','FunctionExpression'].includes(d.type)) {{
          out.push({{name: d.id?d.id.name:'default', params: paramNames(d.params||[]) }});
        }}
      }},
    }});
    console.log(JSON.stringify(out));
    """
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, cwd=self._base_path())
        if r.returncode != 0:
            return []
        try:
            data = json.loads(r.stdout or "[]")
            return [{"name": e.get("name"), "params": [{"name": n, "type": "any"} for n in (e.get("params") or [])]} for e in data if e.get("name")]
        except Exception:
            return []

    



    

def _load_functions_folder_grouped(self, scan_root: str, recursive: bool = True):
        ignore_dirs = {"node_modules", ".next", "dist", "build", ".git", ".turbo", ".cache"}
        exts = (".ts", ".tsx", ".js", ".mjs", ".cjs", ".jsx")
        files = []
        for root, dirs, fs in os.walk(scan_root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for f in fs:
                if f.endswith(exts) and not f.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".test.js", ".spec.js")):
                    files.append(os.path.join(root, f))
        if not files:
            self.log.append(f"ℹ️ No modules found under {scan_root}")
            return

        have_babel = _have_babel(self._base_path())
        groups: dict[str, list[dict]] = {}

        for fpath in sorted(files):
            # extract functions
            items: list[dict] = []
            if have_babel:
                items = _inspect_exports_babel(fpath)
            else:
                items = _inspect_exports_regex(fpath)
                if not items and fpath.endswith((".js", ".mjs", ".cjs")):
                    names = _introspect_file_exports(fpath,cwd=self._base_path())
                    items = [{"name": n, "params": []} for n in names]

            if not items:
                continue

            g = _group_key_from(scan_root, fpath)
            groups.setdefault(g, [])
            for fn in items:
                fn["file"] = fpath
                groups[g].append(fn)

        if not groups:
            msg = "No callable exports found"
            if not have_babel:
                msg += " (tip: yarn add -D @babel/parser @babel/traverse)"
            self.log.append(f"ℹ️ {msg} under {scan_root}")
            return

        # build tabs like “Packages” mode
        for group_name, fns in sorted(groups.items()):
            lw = QListWidget()
            for fn in fns:
                it = QListWidgetItem(fn["name"])
                it.setData(Qt.ItemDataRole.UserRole, fn)  # {name, params?, file}
                lw.addItem(it)
            lw.itemClicked.connect(lambda item, _grp=group_name: self.show_inputs(_grp, item.data(Qt.ItemDataRole.UserRole)))
            self.pkg_func_lists[group_name] = lw
            self.tabs.addTab(lw, group_name)

    # show React subdir only in React mode
    

def _current_mode(self) -> str:
        return self.mode_cb.currentText() if hasattr(self, "mode_cb") else "Packages"

    

def _update_topbar_visibility(self):
        react = (self._current_mode() == "React project")
        self.func_subdir_in.setVisible(react)
    

def show_inputs(self, pkg: str, fn: dict):
        while self.input_form.rowCount():
            self.input_form.removeRow(0)

        self.current_pkg = pkg
        self.current_fn  = fn.get("name")
        self.arg_edits = []

        params = fn.get("params", [])
        if not isinstance(params, list):
            params = []

        for p in params:
            pname = p.get("name", "")
            ptype = p.get("type", "any")
            edit = QLineEdit()
            edit.setPlaceholderText(ptype if pname == "" else ptype)
            label = pname if pname else "(arg)"
            self.input_form.addRow(QLabel(f"{label} ({ptype}):"), edit)
            self.arg_edits.append(edit)

        self.raw_args.clear()
    

def _load_functions_folder(self, scan_root: str, recursive: bool = True):
        """
        Scan a folder for modules and list exported functions per file.
        - Tries Babel static parse for TS/TSX/JS/JSX (no execution).
        - Falls back to dynamic import for JS/MJS/CJS only when Babel is absent.
        """
        ignore_dirs = {"node_modules", ".next", "dist", "build", ".git", ".turbo", ".cache"}
        exts = (".ts", ".tsx", ".js", ".mjs", ".cjs", ".jsx")
        files = []

        for root, dirs, fs in os.walk(scan_root):
            # prune ignored dirs
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for f in fs:
                if not f.endswith(exts):
                    continue
                if f.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".test.js", ".spec.js")):
                    continue
                files.append(os.path.join(root, f))

        if not files:
            self.log.append(f"ℹ️ No modules found under {scan_root}")
            return

        have_babel = _have_babel(self._base_path())
        any_tab = False

        for fpath in sorted(files):
            items: list[dict] = []
            if have_babel:
                items = _inspect_exports_babel(fpath)
            else:
                # fallback: only JS/MJS/CJS safe for dynamic import
                if fpath.endswith((".js", ".mjs", ".cjs")):
                    names = _introspect_file_exports(fpath,cwd=self._base_path())
                    items = [{"name": n, "params": []} for n in names]

            if not items:
                continue

            lw = QListWidget()
            for fn in items:
                meta = {"name": fn["name"], "file": fpath, "params": fn.get("params", [])}
                it = QListWidgetItem(fn["name"])
                it.setData(Qt.ItemDataRole.UserRole, meta)
                lw.addItem(it)

            lw.itemClicked.connect(
                lambda item, _file=fpath: self.show_inputs(os.path.relpath(_file, scan_root),
                                                          item.data(Qt.ItemDataRole.UserRole))
            )
            tab_name = os.path.relpath(fpath, scan_root)
            self.tabs.addTab(lw, tab_name)
            any_tab = True

        if not any_tab:
            msg = "No callable exports found"
            if not have_babel:
                msg += " (tip: npm i -D @babel/parser @babel/traverse for TS/TSX support)"
            self.log.append(f"ℹ️ {msg} under {scan_root}")
    

    

def _current_mode(self) -> str:
        return self.mode_cb.currentText() if hasattr(self, "mode_cb") else "Packages"
    

def _on_path_changed(self, new_text: str):
        """Keep string state in sync when user edits the line edit."""
        self.init_path = new_text.strip()
    

def _base_path(self) -> str:
        """Current base dir (prefer live text from widget, fallback to state/ROOT)."""
        try:
            txt = (self.path_in.text() or "").strip()
        except Exception:
            txt = ""
        return txt or self.init_path or ROOT

    # ---------- Loading (merged) ----------
    

def reload_all(self):
        base = self._base_path()
        self.tabs.clear()
        self.pkg_func_lists = {}
        if not os.path.isdir(base):
            self.log.append(f"❌ Base path is not a directory: {base}")
            return

        mode = self._current_mode()
        if mode == "Packages":
            self._load_packages(base)
        elif mode == "Functions folder":
            self._load_functions_folder_grouped(base)   # <<< new
        else:  # React project
            subdir = (self.func_subdir_in.text().strip() if hasattr(self, "func_subdir_in") else "src/functions") or "src/functions"
            scan_root = os.path.join(base, subdir)
            if not os.path.isdir(scan_root):
                self.log.append(f"ℹ️ React mode: subdir not found: {scan_root}")
                return
            self._load_functions_folder_grouped(scan_root)  # <<< same grouped behavior



    

def load_all(self):
        """Populate tabs from packages under the current base path."""
        base = self._base_path()
        try:
            pkgs = sorted([
                d for d in os.listdir(base)
                if os.path.isdir(os.path.join(base, d))
            ])
        except Exception as e:
            self.log.append(f"❌ Could not list {base}: {e}")
            return

        found_any = False
        for pkg in pkgs:
            items = self._load_pkg_functions(pkg)
            if not items:
                continue
            lw = QListWidget()
            for fn in items:
                it = QListWidgetItem(fn["name"])
                it.setData(Qt.ItemDataRole.UserRole, fn)
                lw.addItem(it)
            lw.itemClicked.connect(
                lambda item, _pkg=pkg: self.show_inputs(_pkg, item.data(Qt.ItemDataRole.UserRole))
            )
            self.pkg_func_lists[pkg] = lw
            self.tabs.addTab(lw, pkg)
            found_any = True

        if not found_any:
            self.log.append(f"ℹ️ No packages with callable exports found under {base}")
    


    

def open_function_file(self):
        if not self.current_fn:
            self.log.append("⚠️ No function selected")
            return
        # if we came from functions-folder/React tab, fn meta includes file
        # pull it from the selected item if present
        cur_widget = self.tabs.currentWidget()
        if isinstance(cur_widget, QListWidget):
            it = cur_widget.currentItem()
            meta = it.data(Qt.ItemDataRole.UserRole) if it else None
            f = meta.get("file") if isinstance(meta, dict) else None
            if f and os.path.exists(f):
                self.log.append(f"📂 Opening: {f}")
                QDesktopServices.openUrl(QUrl.fromLocalFile(f))
                return

        # fallback to packages behavior
        if not self.current_pkg:
            self.log.append("⚠️ No package/file context available")
            return
        pkg_dir = os.path.join(self._base_path(), self.current_pkg)

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
        pkg_dir   = os.path.join(self._base_path(), pkg)
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


    


    # ---------- Runner ----------
    

def _load_packages(self, base: str):
        found_any = False
        try:
            pkgs = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))])
        except Exception as e:
            self.log.append(f"❌ Could not list {base}: {e}")
            return

        for pkg in pkgs:
            items = self._load_pkg_functions(pkg)   # (uses self._base_path internally)
            if not items:
                continue
            lw = QListWidget()
            for fn in items:
                it = QListWidgetItem(fn["name"])
                it.setData(Qt.ItemDataRole.UserRole, fn)
                lw.addItem(it)
            lw.itemClicked.connect(lambda item, _pkg=pkg: self.show_inputs(_pkg, item.data(Qt.ItemDataRole.UserRole)))
            self.pkg_func_lists[pkg] = lw
            self.tabs.addTab(lw, pkg)
            found_any = True

        if not found_any:
            self.log.append(f"ℹ️ No packages with callable exports found under {base}")


    

def _build_args_json(self) -> str:
        """
        Prefer the raw JSON override if provided; otherwise collect from per-param fields.
        """
        raw = (self.raw_args.text() if hasattr(self, "raw_args") else "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("Raw args must be a JSON array")
                return json.dumps(parsed)
            except Exception as e:
                self.log.append(f"❌ Raw args invalid JSON: {e}")
                return "[]"
        args = []
        for edit in getattr(self, "arg_edits", []):
            val = (edit.text() or "").strip()
            if not val:
                continue
            try:
                args.append(json.loads(val))
            except Exception:
                args.append(val)
        return json.dumps(args)

    

def run_function(self):
        """
        Execute the currently selected function, whether it came from:
          - Packages mode (tab == package, entry is dist/index.js|.cjs)
          - Functions folder / React mode (tab item carries 'file' path)
        """
        # figure out what the user selected
        cur = self.tabs.currentWidget()
        if not isinstance(cur, QListWidget):
            self.log.append("⚠️ No function list active")
            return
        item = cur.currentItem()
        if not item:
            self.log.append("⚠️ No function selected")
            return
        meta = item.data(Qt.ItemDataRole.UserRole) or {}
        fn_name = meta.get("name")
        if not fn_name:
            self.log.append("⚠️ Selected item has no function name")
            return

        # args
        args_json = self._build_args_json()

        # decide entry: single file (Functions/React) vs package entry (Packages)
        entry = None
        is_esm_hint = True
        need_tsx = False
        mode = self._current_mode()

        if "file" in meta:
            # Functions folder / React mode
            entry = meta["file"]
            need_tsx = entry.endswith((".ts", ".tsx"))
            # light guard: don't try to run browser-only modules
            if not _looks_server_safe(entry):
                self.log.append(f"⚠️ {os.path.relpath(entry, self._base_path())} looks browser-only; skipping execution.")
                return
        else:
            # Packages mode: current tab label is the package name you used when building tabs
            pkg = self.tabs.tabText(self.tabs.currentIndex())
            if not pkg:
                self.log.append("⚠️ Cannot infer package name from tab")
                return
            self.current_pkg = pkg
            entry, is_esm_hint = self._resolve_entry(pkg,cwd=self._base_path())  # you already have this helper
            if not entry:
                self.log.append(f"❌ No entry file found for package {pkg}")
                return
            need_tsx = entry.endswith((".ts", ".tsx"))

        # Build ESM script first
        if is_esm_hint:
            esm_script = f"""
    import * as m from 'file://{entry}';
    (async () => {{
      try {{
        const fn = m["{fn_name}"];
        if (typeof fn !== 'function') {{
          console.error("ERR", "Export not a function: {fn_name}");
          return;
        }}
        const result = await fn(...{args_json});
        console.log(JSON.stringify(result));
      }} catch (err) {{
        console.error("ERR", err && (err.message || String(err)));
      }}
    }})();
    """.strip()
            r = _run_node_script(_node_cmd(esm=True, need_tsx=need_tsx), esm_script)
            out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
            if r.returncode == 0 and "ERR" not in (r.stderr or ""):
                self.log.append(f"▶️ {os.path.relpath(entry, self._base_path())}:{fn_name}({args_json})\n{out.strip() or '(no output)'}")
                return
            # else: fall back to CJS

        cjs_script = f"""
    const m = require("{entry.replace('"','\\"')}");
    (async () => {{
      try {{
        const fn = m["{fn_name}"];
        if (typeof fn !== 'function') {{
          console.error("ERR", "Export not a function: {fn_name}");
          return;
        }}
        const result = await fn(...{args_json});
        console.log(JSON.stringify(result));
      }} catch (err) {{
        console.error("ERR", err && (err.message || String(err)));
      }}
    }})();
    """.strip()
        r = _run_node_script(_node_cmd(esm=False, need_tsx=need_tsx), cjs_script)
        out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
        self.log.append(f"▶️ {os.path.relpath(entry, self._base_path())}:{fn_name}({args_json})\n{out.strip() or '(no output)'}")
           
