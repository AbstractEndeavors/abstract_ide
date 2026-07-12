from ..imports import *

# `_`-prefixed variants that existed alongside funcs.py. Kept as faithful
# delegators to the canonical implementations (both are bound onto the instance
# by initFuncs, so self.<name> resolves at call time).


def _looks_server_safe(self, file_path):
    """Quick sniff to avoid trying to execute browser-only modules."""
    return self.looks_server_safe(file_path)


def _inspect_exports_regex(self, file_path):
    return self.inspect_exports_regex(file_path)


def _group_key_from(self, scan_root, file_path):
    return self.group_key_from(scan_root, file_path)


def _have_babel(self):
    """Return True if @babel/parser and @babel/traverse are resolvable."""
    return self.have_babel()


def _inspect_exports_babel(self, file_path):
    return self.inspect_exports_babel(file_path)


def _introspect_file_exports(self, file_path):
    """Try ESM import, then CJS require; return exported names."""
    return introspect_file_exports(file_path)
