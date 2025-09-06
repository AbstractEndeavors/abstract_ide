

from .functions import (_apply_query, _assert_pyside6, _build_ui, _build_url, _collect_headers, _collect_kv, _collect_table_data, _fetch_label, _json_try, _make_type_combo, _make_value_combo, _maybe_add_body_row, _maybe_add_header_row, _mime_values_for_category, _mk_request, _norm_prefix, _normalized_prefix, _on_api_prefix_changed, _on_base_changed, _on_base_index_changed, _on_base_text_edited, _on_send_error, _on_send_response, _on_type_changed, _populate_endpoints, _probe_session, _setup_logging, canonicalize_slash, detect_api_prefix, fetch_remote_endpoints, logWidgetInit, methodComboInit, on_endpoint_selected, send_request, start_detect_api_prefix_async)

def initFuncs(self):
    try:
        for f in (_apply_query, _assert_pyside6, _build_ui, _build_url, _collect_headers, _collect_kv, _collect_table_data, _fetch_label, _json_try, _make_type_combo, _make_value_combo, _maybe_add_body_row, _maybe_add_header_row, _mime_values_for_category, _mk_request, _norm_prefix, _normalized_prefix, _on_api_prefix_changed, _on_base_changed, _on_base_index_changed, _on_base_text_edited, _on_send_error, _on_send_response, _on_type_changed, _populate_endpoints, _probe_session, _setup_logging, canonicalize_slash, detect_api_prefix, fetch_remote_endpoints, logWidgetInit, methodComboInit, on_endpoint_selected, send_request, start_detect_api_prefix_async):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
