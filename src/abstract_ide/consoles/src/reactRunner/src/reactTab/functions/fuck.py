from .imports import *
def fix_ts_import_path(path: str) -> str:
    """
    Normalize a module import path:
      - If path exists as-is, return it
      - If missing extension, try .ts/.tsx/.js
      - If directory, try directory/index.ts|.js
    Returns a valid real path or original.
    """

    # 1) Exact match
    if os.path.exists(path):
        return path

    # 2) Try extension variations
    for ext in TS_EXTS:
        candidate = path + ext
        if os.path.exists(candidate):
            return candidate

    # 3) If path is a directory, look for index.ts / index.js inside
    if os.path.isdir(path):
        for ext in TS_EXTS:
            candidate = os.path.join(path, "index" + ext)
            if os.path.exists(candidate):
                return candidate

    # If nothing works — return original (Node will error)
    return path


def resolve_secure_import():
    """
    Resolve:
        /var/www/modules/packages/abstract-apis/src/functions/secure_utils/imports
    by checking all available extension variants.
    """

    base_import = (
        "/var/www/modules/packages/abstract-apis/src/"
        "functions/secure_utils/imports"
    )

    resolved = fix_ts_import_path(base_import)

    print("Requested Path:")
    print(" ", base_import)
    print("\nResolved Path:")
    print(" ", resolved)

    if not os.path.exists(resolved):
        print("\n❌ File not found. Nothing with .ts/.tsx/.js exists.")
    else:
        print("\n✅ File found and resolved correctly.")


if __name__ == "__main__":
    resolve_secure_import()
