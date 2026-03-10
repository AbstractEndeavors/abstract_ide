from ..imports import *
from .bot_layout import create_bot_panel  # Adjust the import if needed

# Define padding constants
pad_small = (5, 5)
pad_medium = (10, 10)
pad_large = (20, 20)
def get_image_component(key=None, size=None, tooltip=None):
    size = size or (800, 400)
    return [sg.Image(key=key, size=size, tooltip=tooltip)]

def get_txn_chart(key=None, size=None, tooltip=None):
    key = key or '-CHART-'
    size = size or (200, 200)
    tooltip = tooltip or "Transaction Chart"
    return get_image_component(key=key, size=size, tooltip=tooltip)

def get_from_key(txn, key):
    function_map = {
        # 'mint': get_mint,
        # 'timestamp': get_timestamps,
        # 'price': get_txn_price,
        'sol_mount': get_sol_amount,
        'token_amount': get_token_amount,
        # 'signature': get_signature,
        # 'isBuy': get_is_buy,
        # 'user_address': get_user_address
    }
    function = function_map.get(key)
    if function:
        value = function(txn)
    else:
        value = txn.get(key)
    return value

def user_profit_display():
    """Return the profit display as a list of rows using title frames for labels."""
    user_combo = sg.Combo([], size=(25, 1), key='-USER_COMBO-', enable_events=True)
    frame = [[sg.Frame('User Profits', [
            # Row 1: User combo plus SOL and Token displays in their own frames.
            [
                user_combo,
                sg.Frame('SOL', [[sg.Text('', key='-USER_PROFITS_SOL-')]], pad=(2, 2)),
                sg.Frame('Token', [[sg.Text('', key='-USER_PROFITS_TOKEN-')]], pad=(2, 2))
            ]],pad=(2, 0),
        title_color='blue'
    )],
            [sg.HorizontalSeparator()],
            # Row 2: Sell, Buy, and Total each in a frame.
            [sg.Frame('User Volume', [[
                sg.Frame('Sell', [[sg.Text('3', key='-USER_VOLUME_SELL-')]], pad=(2, 2)),
                sg.Frame('Buy', [[sg.Text('2', key='-USER_VOLUME_BUY-')]], pad=(2, 2)),
                sg.Frame('Total', [[sg.Text('5', key='-USER_VOLUME_TOTAL-')]], pad=(2, 2))
            ]],pad=(2, 0),
        title_color='blue'
    ),
            
            # Row 3: Token Amount, SOL, and Avg each in a frame.
            sg.Frame('User Averages', [[
                sg.Frame('Token Amount', [[sg.Text('', key='-USER_AVGPRICE_TOKEN_AMOUNT-')]], pad=(2, 2)),
                sg.Frame('SOL', [[sg.Text('', key='-USER_AVGPRICE_SOL-')]], pad=(2, 2)),
                sg.Frame('Avg', [[sg.Text('', key='-USER_AVGPRICE_AVG-')]], pad=(2, 2))
            ]],
        pad=(2, 0),
        title_color='blue'
    )]
        ]
    return [frame]

def get_user_info_layout(pad_small):
    user_info = sg.Table(
        values=[], 
        headings=['Timestamp', 'Price', 'SOL Amount', 'Token Amount', 'Type', 'Signature'],
        key='-USER_TXN_TABLE-', 
        auto_size_columns=True, 
        justification='left', 
        num_rows=5,
        expand_x=True,
        expand_y=True,
        tooltip="User Transaction History"
    )
    

    return [[user_info],user_profit_display()]

def get_transacton_history_layout(txn_columns, txn_data, padding):
    txn_table = sg.Table(
        values=[[txn.get(col, '') for col in txn_columns] for txn in txn_data],
        headings=txn_columns,
        display_row_numbers=True,
        auto_size_columns=True,
        num_rows=10,
        key='-TXN_TABLE-',
        enable_events=True,
        justification='left',
        expand_x=True,
        expand_y=True,
        tooltip="Transaction History"
    )
    
    return [[txn_table],get_user_info_layout(pad_small)]

def get_txn_info_bot_layout(txn_table_frame,chart, bot_frame):
    txn_info_bot_layout = [[
        sg.Column(txn_table_frame, vertical_alignment='top'),
        sg.VSeparator(),
        sg.Column([chart], vertical_alignment='top'),
        sg.VSeparator(),
        sg.Column([[bot_frame]], vertical_alignment='top')  # Wrapped bot_frame in a list of lists
    ]]
    return txn_info_bot_layout

def get_txn_history_layout(txn_data, txn_columns, chart_data=None):
    # Layout for Transaction History
    txn_table = get_transacton_history_layout(txn_columns, txn_data, pad_small)
    txn_table_frame = [[sg.Frame('Transaction History', txn_table, pad=pad_small, expand_x=True, expand_y=True)]]

    # Layout for User Information (wrap the table in a frame)
    user_info = get_user_info_layout(pad_small)
    user_info_frame = get_txn_chart(key='-CHART-', size=(300,300), tooltip='transactons chart')

    # Bot Panel (assuming create_bot_panel() returns a valid layout)
    bot_frame = create_bot_panel()

    # IMPORTANT: Pass the wrapped frame (user_info_frame) instead of reusing user_info.
    txn_info_bot_layout = get_txn_info_bot_layout(txn_table_frame, user_info_frame, bot_frame)
    return txn_info_bot_layout

def main():
    # Example transaction data and columns for demonstration purposes.
    txn_columns = ['Timestamp', 'Price', 'SOL Amount', 'Token Amount', 'Type', 'Signature']
    txn_data = [
        {
            'Timestamp': '2025-02-14 10:00',
            'Price': 100,
            'SOL Amount': 1,
            'Token Amount': 50,
            'Type': 'Buy',
            'Signature': 'abc123'
        },
        # Add more transaction dictionaries here if needed.
    ]

    # Build the overall layout.
    layout = get_txn_history_layout(txn_data, txn_columns)

    # Create the window.
    window = sg.Window("Transaction History", layout, resizable=True, finalize=True)

    # Event loop.
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED:
            break

        # Add event handling logic here.
        print("Event:", event)
        print("Values:", values)

    window.close()

if __name__ == "__main__":
    main()
