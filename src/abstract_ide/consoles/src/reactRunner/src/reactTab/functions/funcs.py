from ..imports import *

# ---------------------------------------------------------------------------
# Recovered reactTab engine (see functions/__init__.py). Node/Babel/tsx scripts
# are verbatim from bytecode; Python flow reconstructed from the call sequences.
# ---------------------------------------------------------------------------

_BROWSER_MARKERS = ("window.", "document.", "navigator.", "localStorage",
                    "from 'react'", 'from "react"')


# ---------- static export introspection ----------
def looks_server_safe(self, file_path):
    """Quick sniff to avoid trying to execute browser-only modules."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return True
    return not any(m in text for m in _BROWSER_MARKERS)


def inspect_exports_regex(self, file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return []
    out = []
    for m in export_fn_re.finditer(text):
        name = m.group("name") if "name" in (export_fn_re.groupindex or {}) else m.group(1)
        params = []
        try:
            raw = m.group("params") if "params" in (export_fn_re.groupindex or {}) else ""
            for part in raw.split(","):
                part = part.strip()
                if not part:
                    continue
                pname = part.split(":")[0].split("=")[0].strip()
                if pname:
                    params.append({"name": pname, "type": "any"})
        except Exception:
            pass
        out.append({"name": name, "params": params})
    return out


def group_key_from(self, scan_root, file_path):
    rel = os.path.relpath(file_path, scan_root)
    parts = rel.split(os.sep)
    return parts[0] if len(parts) > 1 else "(root)"


def have_babel(self, cwd=None):
    """Return True if @babel/parser and @babel/traverse are resolvable."""
    r = runSubProcess("node", "-e",
                      "require('@babel/parser'); require('@babel/traverse'); console.log('OK')",
                      cwd=cwd)
    return r.returncode == 0 and "OK" in (r.stdout or "")


def inspect_exports_babel(self, file_path):
    """
    Use Babel to parse a file and return [{name, params}] of exported functions.
    Requires @babel/parser and @babel/traverse.
    """
    script = (
        "\n    const fs = require('fs');\n    const p  = " + json.dumps(file_path) +
        ";\n    const code = fs.readFileSync(p, 'utf8');\n\n    let parser, traverse;\n"
        "    try {\n      parser = require('@babel/parser');\n"
        "      traverse = require('@babel/traverse').default;\n    } catch (e) {\n"
        "      console.log('[]');\n      process.exit(0);\n    }\n\n"
        "    const ast = parser.parse(code, {\n      sourceType: 'module',\n      plugins: [\n"
        "        'typescript','jsx','classProperties','decorators-legacy',\n"
        "        'exportDefaultFrom','exportNamespaceFrom','dynamicImport','topLevelAwait'\n"
        "      ]\n    });\n\n    const out = [];\n    function paramNames(params) {\n"
        "      return (params || []).map((q) => {\n"
        "        if (q.type === 'Identifier') return q.name;\n"
        "        if (q.type === 'AssignmentPattern' && q.left && q.left.type === 'Identifier') return q.left.name;\n"
        "        if (q.type === 'RestElement' && q.argument && q.argument.type === 'Identifier') return '...' + q.argument.name;\n"
        "        return '_';\n      });\n    }\n\n    traverse(ast, {\n"
        "      ExportNamedDeclaration(path) {\n        const decl = path.node.declaration;\n"
        "        if (!decl) return;\n        if (decl.type === 'FunctionDeclaration') {\n"
        "          const name = decl.id ? decl.id.name : 'default';\n"
        "          out.push({ name, params: paramNames(decl.params) });\n"
        "        } else if (decl.type === 'VariableDeclaration') {\n"
        "          for (const d of decl.declarations) {\n"
        "            if (!d.id || d.id.type !== 'Identifier') continue;\n"
        "            const name = d.id.name;\n            const init = d.init;\n"
        "            if (!init) continue;\n"
        "            if (init.type === 'ArrowFunctionExpression' || init.type === 'FunctionExpression') {\n"
        "              out.push({ name, params: paramNames(init.params) });\n            }\n          }\n        }\n      },\n"
        "      ExportDefaultDeclaration(path) {\n        const decl = path.node.declaration;\n"
        "        if (!decl) return;\n"
        "        if (['FunctionDeclaration','ArrowFunctionExpression','FunctionExpression'].includes(decl.type)) {\n"
        "          const name = decl.id ? decl.id.name : 'default';\n"
        "          const params = decl.params ? paramNames(decl.params) : [];\n"
        "          out.push({ name, params });\n        }\n      },\n    });\n\n"
        "    console.log(JSON.stringify(out));\n    "
    )
    try:
        r = runSubProcess("node", "-e", script, cwd=self.base_path())
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout)
        for d in data:
            d.setdefault("params", [])
        return data
    except Exception:
        return []


def introspect_file_exports(file_path, cwd=None, esm=True, capture_output=True, text=True):
    node_cmd = resolve_for_node(file_path)
    try:
        if esm:
            r = runSubProcess("node", "--input-type=module", "-e",
                              "import * as m from 'file://" + node_cmd +
                              "'; console.log(JSON.stringify(Object.keys(m)));",
                              cwd=cwd, capture_output=capture_output, text=text)
        else:
            safe = node_cmd.replace('"', '\\"')
            r = runSubProcess("node", "-e",
                              '\n    try {\n      const m = require("' + safe +
                              '");\n      console.log(JSON.stringify(Object.keys(m)));\n'
                              '    } catch (e) {\n      console.log("[]");\n    }',
                              cwd=cwd, capture_output=capture_output, text=text)
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout.strip())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def resolve_entry(pkg, cwd=None):
    """Return (entry_path, is_esm)"""
    cwd = cwd or os.getcwd()
    for cand in ("index.js", "index.cjs"):
        p = os.path.join(cwd, pkg, "dist", cand)
        if os.path.exists(p):
            return p, cand.endswith(".js")
    return None, False


# ---------- mode / path helpers ----------
def current_mode(self):
    if hasattr(self, "mode_cb"):
        return self.mode_cb.currentText()
    return "Packages"


def update_topbar_visibility(self):
    try:
        self.func_subdir_in.setVisible(self.current_mode() == "React project")
    except Exception:
        pass


def on_path_changed(self, new_text):
    """Keep string state in sync when user edits the line edit."""
    self.init_path = (new_text or "").strip()


def base_path(self):
    """Current base dir (prefer live text from widget, fallback to state/ROOT)."""
    try:
        t = self.path_in.text().strip()
        if t:
            return t
    except Exception:
        pass
    return getattr(self, "init_path", None) or ROOT


# ---------- input form ----------
def show_inputs(self, pkg, fn):
    while self.input_form.rowCount():
        self.input_form.removeRow(0)
    self.current_pkg = pkg
    self.current_fn = fn.get("name") if isinstance(fn, dict) else fn
    self.arg_edits = []
    params = fn.get("params", []) if isinstance(fn, dict) else []
    for p in params:
        name = p.get("name", "(arg)") if isinstance(p, dict) else str(p)
        ptype = p.get("type", "any") if isinstance(p, dict) else "any"
        edit = QLineEdit()
        edit.setPlaceholderText(ptype)
        self.arg_edits.append(edit)
        self.input_form.addRow(QLabel(name + " (" + ptype + "):"), edit)
    self.raw_args.clear()


# ---------- scanning ----------
def _exports_for(self, file_path):
    if self.have_babel(self.base_path()):
        return self.inspect_exports_babel(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".js", ".mjs", ".cjs"):
        return [{"name": n, "params": []} for n in introspect_file_exports(file_path)]
    return self.inspect_exports_regex(file_path)


def _build_fn_list(self, entries):
    lst = QListWidget()
    for name, fn in entries:
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, fn)
        lst.addItem(item)
    lst.itemClicked.connect(lambda it: self.show_inputs(
        it.data(Qt.ItemDataRole.UserRole).get("__pkg__"),
        it.data(Qt.ItemDataRole.UserRole)))
    return lst


def load_functions_folder_grouped(self, scan_root, recursive=True):
    groups = {}
    found = False
    for root, _dirs, files in os.walk(scan_root):
        for fn in files:
            if fn.endswith(tuple(TS_EXTS)):
                found = True
                fpath = os.path.join(root, fn)
                exports = self.inspect_exports_babel(fpath) or self.inspect_exports_regex(fpath) \
                    or [{"name": n, "params": []} for n in introspect_file_exports(fpath)]
                key = self.group_key_from(scan_root, fpath)
                for e in exports:
                    e["file"] = fpath
                    groups.setdefault(key, []).append((e["name"], e))
        if not recursive:
            break
    if not found:
        self.log.append("ℹ️ No modules found under " + scan_root)
        return
    self.pkg_func_lists = {}
    for key, entries in sorted(groups.items()):
        lst = QListWidget()
        for name, e in entries:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, e)
            lst.addItem(item)
        lst.itemClicked.connect(lambda it: self.show_inputs(None, it.data(Qt.ItemDataRole.UserRole)))
        self.pkg_func_lists[key] = lst
        self.tabs.addTab(lst, key)


def load_functions_folder(self, scan_root, recursive=True):
    """
    Scan a folder for modules and list exported functions per file.
    - Tries Babel static parse for TS/TSX/JS/JSX (no execution).
    - Falls back to dynamic import for JS/MJS/CJS only when Babel is absent.
    """
    found = False
    entries = []
    for root, _dirs, files in os.walk(scan_root):
        for fn in files:
            if fn.endswith(tuple(TS_EXTS)):
                found = True
                fpath = os.path.join(root, fn)
                exports = self.inspect_exports_babel(fpath) \
                    or [{"name": n, "params": []} for n in introspect_file_exports(fpath)]
                for e in exports:
                    e["file"] = fpath
                    entries.append((e.get("name"), e))
        if not recursive:
            break
    if not found:
        self.log.append("ℹ️ No modules found under " + scan_root)
        return
    lst = QListWidget()
    for name, e in sorted(entries):
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, e)
        lst.addItem(item)
    lst.itemClicked.connect(lambda it: self.show_inputs(None, it.data(Qt.ItemDataRole.UserRole)))
    self.pkg_func_lists["(functions)"] = lst
    self.tabs.addTab(lst, os.path.relpath(scan_root, self.base_path()))


def load_pkg_functions(self, pkg):
    base = self.base_path()
    for cand in ("index.js", "index.cjs", "index.d.ts"):
        entry = os.path.join(base, pkg, "dist", cand)
        if not os.path.exists(entry):
            continue
        try:
            if cand.endswith(".cjs"):
                safe = entry.replace('"', '\\"')
                r = runSubProcess("node", "-e",
                                  '\nconst m = require("' + safe +
                                  '");\nconsole.log(JSON.stringify(Object.keys(m)));\n')
            else:
                r = runSubProcess("node", "--input-type=module", "-e",
                                  "\nimport * as pkg from 'file://" + entry +
                                  "';\nconsole.log(JSON.stringify(Object.keys(pkg)));\n")
            if r.returncode == 0:
                names = json.loads(r.stdout)
                return [{"name": n, "params": []} for n in names]
            self.log.append("⚠️ " + pkg + ": export introspection failed:\n" + (r.stderr or "").strip())
        except Exception as e:
            self.log.append("⚠️ " + pkg + ": export introspection error: " + str(e))
    return []


def load_packages(self, base):
    try:
        pkgs = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    except Exception as e:
        self.log.append("❌ Could not list " + base + ": " + str(e))
        return
    any_found = False
    for pkg in pkgs:
        fns = self.load_pkg_functions(pkg)
        if not fns:
            continue
        any_found = True
        lst = QListWidget()
        for fn in fns:
            item = QListWidgetItem(fn["name"])
            fn["__pkg__"] = pkg
            item.setData(Qt.ItemDataRole.UserRole, fn)
            lst.addItem(item)
        lst.itemClicked.connect(lambda it: self.show_inputs(
            it.data(Qt.ItemDataRole.UserRole).get("__pkg__"),
            it.data(Qt.ItemDataRole.UserRole)))
        self.pkg_func_lists[pkg] = lst
        self.tabs.addTab(lst, pkg)
    if not any_found:
        self.log.append("ℹ️ No packages with callable exports found under " + base)


def load_all(self):
    """Populate tabs from packages under the current base path."""
    self.load_packages(self.base_path())


def reload_all(self):
    try:
        base = self.base_path()
        self.tabs.clear()
        self.pkg_func_lists = {}
        if not os.path.isdir(base):
            self.log.append("❌ Base path is not a directory: " + base)
            return
        mode = self.current_mode()
        if mode == "Packages":
            self.load_packages(base)
        elif mode == "Functions folder":
            self.load_functions_folder_grouped(base)
        else:  # React project
            subdir = self.func_subdir_in.text().strip() if hasattr(self, "func_subdir_in") else "src/functions"
            scan = os.path.join(base, subdir)
            if not os.path.isdir(scan):
                self.log.append("ℹ️ React mode: subdir not found: " + scan)
                return
            self.load_functions_folder_grouped(scan)
    except Exception as e:
        try:
            self.log.append("❌ reload_all failed: " + str(e))
        except Exception:
            pass


# ---------- open / run ----------
def open_item(self):
    QDesktopServices.openUrl(QUrl.fromLocalFile(self.base_path()))


def open_function_file(self):
    lst = self.tabs.currentWidget()
    if not isinstance(lst, QListWidget):
        self.log.append("⚠️ No function list active")
        return
    item = lst.currentItem()
    if not item:
        self.log.append("⚠️ No function selected")
        return
    fn = item.data(Qt.ItemDataRole.UserRole)
    path = fn.get("file") if isinstance(fn, dict) else None
    if path and os.path.exists(path):
        self.log.append("📂 Opening: " + path)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        return
    # fall back to package dist entry
    pkg = self.current_pkg
    if pkg:
        for cand in ("index.js",):
            p = os.path.join(self.base_path(), pkg, "dist", cand)
            if os.path.exists(p):
                self.log.append("📂 Opening file for " + pkg + ": " + p)
                QDesktopServices.openUrl(QUrl.fromLocalFile(p))
                return
    self.log.append("❌ Could not locate file for " + str(self.current_fn))


def build_args_json(self):
    """
    Always return an ARRAY of arguments for TS.
    Normalizes Python dict strings to real JSON objects.
    """
    if hasattr(self, "raw_args") and self.raw_args.text().strip():
        try:
            arr = json.loads(self.raw_args.text().strip())
            if not isinstance(arr, list):
                raise ValueError("Raw args must be a JSON array")
            return json.dumps(arr)
        except Exception as e:
            self.log.append("❌ Raw args invalid JSON: " + str(e))
            return "[]"
    args = []
    for edit in getattr(self, "arg_edits", []):
        args.append(_normalize_arg(edit.text()))
    return json.dumps(args)


def install_analyzers(self):
    r = runSubProcess("npm", "i", "-D", "@babel/parser", "@babel/traverse", "tsx",
                      cwd=self.base_path())
    if r.returncode == 0:
        self.log.append("✅ Installed @babel/parser, @babel/traverse, tsx")
    else:
        self.log.append("❌ Install failed:\n" + (r.stderr or ""))


def run_function(self):
    """Executes TS functions using tsx, with full Python-style kwargs support."""
    lst = self.tabs.currentWidget()
    if not isinstance(lst, QListWidget):
        self.log.append("⚠️ No function list active")
        return
    item = lst.currentItem()
    if not item:
        self.log.append("⚠️ No function selected")
        return
    fn = item.data(Qt.ItemDataRole.UserRole)
    name = fn.get("name") if isinstance(fn, dict) else None
    if not name:
        self.log.append("⚠️ Selected item has no function name")
        return
    path = fn.get("file") if isinstance(fn, dict) else None
    if not path or not os.path.exists(path):
        self.log.append("❌ File not found: " + str(path))
        return
    try:
        args = json.loads(self.build_args_json())
    except Exception:
        args = []
    self.log.append("▶️ " + os.path.relpath(path, self.base_path()) + ":" + name + "(" + json.dumps(args) + ")\n")
    try:
        out = _run_ts_function(os.path.abspath(path), name, args)
        self.log.append(str(out))
    except Exception as e:
        self.log.append("error: " + str(e))


# ---------- node / tsx execution helpers ----------
def resolve_for_node(path):
    """
    Normalizes TS/JS import paths for Node execution.
    Special case:
        If inside src/functions/** and import is '../imports',
        rewrite to ROOT/src/imports.ts.
    """
    path = os.path.abspath(path)
    path = path.replace("\\", "/")
    if path.endswith("/src/functions/imports"):
        base = path.split("/src/functions/")[0]
        return os.path.join(base, "src", "imports.ts")
    if os.path.isdir(path):
        return os.path.join(path, "index")
    return path


def _find_nvm_bin():
    nvm = Path.home() / ".nvm" / "versions" / "node"
    if not nvm.exists():
        raise RuntimeError("NVM Node not found")
    versions = sorted(nvm.iterdir())
    if not versions:
        raise RuntimeError("Node not found in NVM")
    return str(versions[-1] / "bin")


_NODE_BIN = None


def _ensure_node():
    global _NODE_BIN
    if _NODE_BIN is None:
        try:
            _NODE_BIN = _find_nvm_bin()
        except Exception:
            _NODE_BIN = ""
    return os.path.join(_NODE_BIN, "node") if _NODE_BIN else "node"


def _make_esm_call_script(ts_file, export_name, args):
    return (
        '\nimport * as mod from "file://' + ts_file + '";\nconst fn = mod["' + export_name +
        '"];\nif (typeof fn !== "function") {\n  console.error("ERR_NOT_FUNCTION");\n  process.exit(1);\n}\n'
        'Promise.resolve(fn(...' + json.dumps(args) +
        '))\n  .then(r => console.log(JSON.stringify(r)))\n  .catch(e => console.error("ERR", e?.message || e));\n'
    )


def _normalize_arg(val):
    """
    Converts Python dict syntax to JSON safely:
        {'domain': 'abc.com'}  ->  {"domain": "abc.com"}
    """
    if not isinstance(val, str):
        return val
    s = val.replace("'", '"').replace("True", "true").replace("False", "false").replace("None", "null")
    try:
        return json.loads(s)
    except Exception:
        return val


def _run_ts_function(ts_file, export_name, args):
    node = _ensure_node()
    script = _make_esm_call_script(ts_file, export_name, args)
    try:
        r = subprocess.run([node, "--input-type=module", "-e", script],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return {"error": (r.stderr or "").strip()}
        out = (r.stdout or "").strip()
        try:
            return json.loads(out)
        except Exception:
            return out
    except Exception as e:
        return {"error": str(e)}
