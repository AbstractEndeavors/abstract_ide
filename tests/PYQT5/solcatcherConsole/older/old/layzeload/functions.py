# Globals to manage pagination
from ...imports import *
from ...display_utils import metaKeys,make_check_bool
from ...managers.configUtils import *
current_page = 0
page_size = 50
filters = {"sol_amount": 1, "operator": ">", "timestamp": None, "timestamp_operator": "<"}
def get_from_key(txn,key):
    function_map = {
    #'mint':get_mint,
    #'timestamp':get_timestamps,
    # 'price':get_txn_price,
    'sol_mount':get_sol_amount,
    'token_amount':get_token_amount}
    # 'signature':get_signature,
    # 'isBuy':get_is_buy,
    # 'user_address':get_user_address}
    function = function_map.get(key)
    if function:
        value = get_any_value(txn,key)
    else:
        value = get_for_key(txn,key)
    return value
def getMetaChecks(values):
    filterChecks={}
    false_bools = ['updateAuthority','freezeAuthority','mintAuthority']
    for key in metaKeys:
        value = values.get(make_check_bool(key))
        if value:
            filterChecks[key] = value
            if key in false_bools and value:
                filterChecks[key] = False
        
    return filterChecks
def apply_filters(values):
    filtered_data=filters
    filtered_data['sol_amount'] = float(values['-SOL_THRESHOLD_INPUT-'])
    filtered_data['timestamp'] = get_min_timestamp(values['-TIME_RANGE-']) or None
    filtered_data['metaDataKeys']=getMetaChecks(values)
    return filtered_data
def load_more_data(values,window,current_page,columns):
    """
    Load more data into the main table dynamically.
    """

    filtered_values = apply_filters(values)
    # Fetch data with filters and pagination
    data = fetch_filtered_transactions_paginated(
        **filtered_values,
        limit=page_size,
        offset=current_page * page_size
    )

    # Append rows to the main table
    table = window['-MAIN_TABLE-']
    existing_data = table.Values or []
    table.update(values=existing_data + [[get_from_key(dict(row),col) for col in columns] for row in data])

    # Increment page count
    current_page += 1
    return current_page
