import subprocess,re
# optional regex fallback (works for simple cases of `export function foo(...)` or `export const foo = (...) =>`)
export_fn_re = re.compile(
    r"""
    ^\s*export\s+
    (?:
      (?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\) |
      const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=> 
    )
    """,
    re.M | re.X,
)
ROOT = "/var/www/modules/packages/abstract-apis"
INSPECT_MJS = "/var/www/modules/packages/inspect-dts.mjs"  # expects to print JSON: [{name, params:[{name,type},...]}, ...]
