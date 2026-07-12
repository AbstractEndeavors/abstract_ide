from ..imports import *


def fix_ts_import_path(path):
    """
    Normalize a module import path:
      - If path exists as-is, return it
      - If missing extension, try .ts/.tsx/.js
      - If directory, try directory/index.ts|.js
    Returns a valid real path or original.
    """
    if os.path.exists(path):
        return path
    for ext in TS_EXTS:
        if os.path.exists(path + ext):
            return path + ext
    if os.path.isdir(path):
        for ext in TS_EXTS:
            cand = os.path.join(path, "index" + ext)
            if os.path.exists(cand):
                return cand
    return path


def resolve_secure_import():
    """
    Resolve:
        /var/www/modules/packages/abstract-apis/src/functions/secure_utils/imports
    by checking all available extension variants.
    """
    requested = "/var/www/modules/packages/abstract-apis/src/functions/secure_utils/imports"
    print("Requested Path:", requested)
    resolved = fix_ts_import_path(requested)
    print("\nResolved Path:", resolved)
    if os.path.exists(resolved):
        print("\n✅ File found and resolved correctly.")
    else:
        print("\n❌ File not found. Nothing with .ts/.tsx/.js exists.")
    return resolved
