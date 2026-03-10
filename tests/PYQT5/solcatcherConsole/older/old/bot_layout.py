from ..imports import *

# Define padding constants
pad_small = (5, 5)
pad_medium = (10, 10)
pad_large = (20, 20)

def derive_total_supply(virtual_sol_reserves: int, virtual_token_reserves: int, minimum_liquidity: int = 0) -> float:
    total_supply = math.sqrt(virtual_sol_reserves * virtual_token_reserves) * (4000000000 / 126235294117647)
    return total_supply

def calculate_initial_liquidity(reserve0: float, reserve1: float, minimum_liquidity: float = 0):
    liquidity = math.sqrt(reserve0 * reserve1)
    liquidity_adjusted = liquidity - minimum_liquidity
    return liquidity_adjusted

def get_capital(string):
    return f"{string[0].upper()}{string[1:].lower()}"

def get_slippage():
    slippage_slider = [
        sg.Slider(
            range=(1, 100), orientation='h', size=(20, 15), default_value=15,
            key='-BOT_SLIPPAGE_PERCENT_SLIDER-', enable_events=True
        )
    ]
    slippage_input = [
        sg.Input(
            default_text='15', size=(5, 1), key='-BOT_SLIPPAGE_PERCENT-',
            tooltip='Slippage percentage (1-100%)', enable_events=True
        )
    ]
    return [sg.Frame('Slippage (%)', [slippage_input, slippage_slider], pad=pad_small)]

def get_bot_controls(buy=True):
    typ = 'BUY' if buy else 'SELL'
    capital = get_capital(typ)
    lower = typ.lower()
    return [
        [sg.Text(f'{capital} Bot Controls', font=('Any', 12, 'bold'))],
        [
            sg.Button(f'Start {capital} Bot', key=f'-START_{typ}_BOT-', size=(15, 1), button_color=('white', 'green')),
            sg.Button(f'Stop {capital} Bot', key=f'-STOP_{typ}_BOT-', size=(15, 1), button_color=('white', 'red'))
        ],
        [
            sg.Text(f'Percent Target {capital} (%):', size=(20, 1)),
            sg.Input(default_text='10', size=(5, 1), key=f'-PERCENT_{typ}-', tooltip=f'Percentage to {lower}'),
            sg.Slider(range=(1, 100), orientation='h', size=(20, 15), default_value=10, key=f'-PERCENT_{typ}_SLIDER-', enable_events=True)
        ],
        [
            sg.Text('Time Frame:', size=(20, 1)),
            sg.Combo(['1 Minute', '5 Minutes', '15 Minutes', '30 Minutes', '1 Hour'], default_value='5 Minutes',
                     key=f'-TIME_FRAME_{typ}-', readonly=True, tooltip=f'Time frame for {lower} bot')
        ]
    ]

def get_bot_reset_setting():
    return [
        [sg.Button('Reset Bot Settings', key='-RESET_BOT-', size=(20, 1), tooltip='Reset all bot settings')],
        [sg.Text('Bot Status:'), sg.Text('Idle', key='-BOT_STATUS-', text_color='blue', size=(20, 1))],
        [sg.Multiline(size=(60, 10), key='-BOT_LOG-', disabled=True, autoscroll=True, tooltip='Bot activity logs')]
    ]

def create_automated_bot_panel():
    bot_layout = [
        [sg.Text('Automated Bot Controls', font=('Any', 14), justification='center', expand_x=True)],
        [sg.HorizontalSeparator()],
        *get_bot_controls(buy=True),
        [sg.HorizontalSeparator()],
        *get_bot_controls(buy=False),
        [sg.HorizontalSeparator()],
        *get_bot_reset_setting()
    ]
    return sg.Frame('Automated Bot Panel', bot_layout, pad=pad_small, expand_x=True)

def get_quantity_frame():
    tokens = sg.Frame('Tokens', [
        [sg.Input('0', key='-BOT_QUANTITY_TOKENS-', size=(10, 1), enable_events=True, tooltip='Tokens to buy/sell')]
    ])
    sol = sg.Frame('SOL', [
        [sg.Input('0.01', key='-BOT_QUANTITY_SOL-', size=(10, 1), enable_events=True, tooltip='SOL amount to spend')]
    ])
    max_sol = sg.Frame('Max SOL Cost', [
        [sg.Text('0', key='-BOT_MAX_SOL_COST-', size=(10, 1), tooltip='Max SOL including slippage')]
    ])
    percent = sg.Frame('Percent', [
        [sg.Input('10', key='-BOT_QUANTITY_PERCENT-', size=(5, 1), tooltip='Percent of supply', enable_events=True)],
        [sg.Slider(range=(1, 100), orientation='h', size=(20, 15), default_value=10,
                   key='-BOT_QUANTITY_PERCENT_SLIDER-', enable_events=True)]
    ])
    slippage = get_slippage()
    return sg.Frame('Trade Details', [[tokens, sol, max_sol, percent], slippage], pad=pad_small)

def get_reserves_frame():
    return sg.Frame('Pool Reserves', [
        [sg.Text('Virtual SOL:'), sg.Text('0', key='-VIRTUAL_SOL_RESERVES-', size=(15, 1))],
        [sg.Text('Virtual Tokens:'), sg.Text('0', key='-VIRTUAL_TOKEN_RESERVES-', size=(15, 1))]
    ], pad=pad_small)

def create_manual_controls_panel():
    manual_layout = [
        [sg.Text('Manual Buy and Sell Controls', font=('Any', 14), justification='center', expand_x=True)],
        [sg.HorizontalSeparator()],
        [
            sg.Button('Manual Buy', key='-MANUAL_BUY-', size=(15, 1), button_color=('white', 'green')),
            sg.Button('Manual Sell', key='-MANUAL_SELL-', size=(15, 1), button_color=('white', 'red'))
        ],
        [sg.Text('Token Details:')],
        [sg.Text('Mint:'), sg.Input(key='-BOT_MINT-', size=(40, 1), tooltip='Token mint address')],
        [sg.Text('Symbol:'), sg.Input(key='-BOT_SYMBOL-', size=(15, 1), tooltip='Token symbol')],
        [sg.Text('Price (SOL):'), sg.Text('0', key='-BOT_PRICE-', size=(15, 1), tooltip='Current price per token')],
        [get_quantity_frame()],
        [get_reserves_frame()],
        [sg.Button('Submit Order', key='-SUBMIT_ORDER-', size=(15, 1))]
    ]
    return sg.Frame('Manual Controls', manual_layout, pad=pad_small, expand_x=True)

def create_bot_panel():
    tab_manual = sg.Tab('Manual Controls', [[create_manual_controls_panel()]])
    tab_automated = sg.Tab('Automated Bot', [[create_automated_bot_panel()]])
    return sg.TabGroup([[tab_manual, tab_automated]], expand_x=True, expand_y=True)
