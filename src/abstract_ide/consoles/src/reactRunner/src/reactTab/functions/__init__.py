# reactTab methods, bound onto the tab instance by initFuncs (dev mode scans
# this package and binds every module-level `def name(self, ...)`).
#
# Recovered 2026-07-11 from the orphaned functions/__pycache__ bytecode
# (funcs / fuck / solo_funcs .cpython-313.pyc) after the migration lost the
# source. The embedded Babel / ESM / tsx JavaScript came back verbatim from the
# bytecode string constants; the Python control flow is reconstructed from the
# compiled name/call sequences, so the node-introspection paths are best-effort
# and worth testing. reload_all/update_topbar_visibility (called from __init__)
# are guarded so the tab always loads.
