from ..imports import *
from .filter_layout import get_filter_layout
from .main_table_layout import get_main_table_layout
from .txn_utils import get_txn_history_layout
def create_layout(main_data,
                    main_columns,
                    txn_data,
                    txn_columns,
                    image_data=None,
                    init_data=None,
                    chart_data=None):
    filter_layout = get_filter_layout()
    txn_layout = get_txn_history_layout(txn_data, txn_columns, chart_data=None)
    table_layout = get_main_table_layout(main_data,main_columns,image_data=image_data,init_data=init_data)
    # Combine all layouts
    layout = [
        #[sg.Column([[filter_layout]],expand_x=True)],  # Wrapped filter_frame inside a list of lists
        [sg.HorizontalSeparator()],
        [table_layout],
        [sg.HorizontalSeparator()],
        [sg.Column(txn_layout,expand_x=True,expand_y=True)],
        [sg.HorizontalSeparator()],
    ]
    return layout

def get_layout(main_data, main_columns, txn_columns):
    sg.theme('Material1')  # Choose a suitable theme
    txn_data = []
    name = ''
    # Create the layout
    layout = create_layout(
        main_data,
        main_columns,
        txn_data,
        txn_columns,
        image_data=None,
        chart_data=None
    )
    # Create the Window
    window = sg.Window('SOL Transaction Dashboard',
                       layout,
                       finalize=True,
                       resizable=True)
    return window 
