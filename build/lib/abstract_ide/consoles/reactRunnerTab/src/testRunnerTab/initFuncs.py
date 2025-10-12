

from .functions import (_base_path, _build_args_json, _current_mode, _group_key_from, _have_babel, _inspect_exports_babel, _inspect_exports_regex, _install_analyzers, _introspect_file_exports, _load_functions_folder, _load_functions_folder_grouped, _load_packages, _load_pkg_functions, _looks_server_safe, _node_cmd, _on_path_changed, _resolve_entry, _run_node_script, _update_topbar_visibility, load_all, open_function_file, open_item, reload_all, run_function, show_inputs)

def initFuncs(self):
    try:
        for f in (_base_path, _build_args_json, _current_mode, _group_key_from, _have_babel, _inspect_exports_babel, _inspect_exports_regex, _install_analyzers, _introspect_file_exports, _load_functions_folder, _load_functions_folder_grouped, _load_packages, _load_pkg_functions, _looks_server_safe, _node_cmd, _on_path_changed, _resolve_entry, _run_node_script, _update_topbar_visibility, load_all, open_function_file, open_item, reload_all, run_function, show_inputs):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
