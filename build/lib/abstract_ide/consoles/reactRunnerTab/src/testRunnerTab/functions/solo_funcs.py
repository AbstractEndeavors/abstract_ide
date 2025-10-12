def _node_cmd(self, *, esm: bool, need_tsx: bool) -> list[str]:
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
    
def _introspect_file_exports(self, file_path: str) -> list[str]:
        """Try ESM import, then CJS require; return exported names."""
        # 1) Try ESM import
        script_esm = f"""
    import * as m from 'file://{file_path}';
    console.log(JSON.stringify(Object.keys(m)));
    """
        r = subprocess.run(["node", "--input-type=module", "-e", script_esm], capture_output=True, text=True)
        if r.returncode == 0:
            try:
                names = json.loads(r.stdout.strip())
                return [n for n in names if isinstance(n, str)]
            except Exception:
                pass

        # 2) Fallback CJS require
        script_cjs = f"""
    try {{
      const m = require("{file_path.replace('"','\\"')}");
      console.log(JSON.stringify(Object.keys(m)));
    }} catch (e) {{
      console.log("[]");
    }}
    """
        r = subprocess.run(["node", "-e", script_cjs], capture_output=True, text=True)
        try:
            names = json.loads((r.stdout or "[]").strip())
            return [n for n in names if isinstance(n, str)]
        except Exception:
            return []


    