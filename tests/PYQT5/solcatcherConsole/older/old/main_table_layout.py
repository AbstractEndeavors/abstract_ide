from ..imports import *
# Define padding constants
pad_small = (5, 5)
pad_medium = (10, 10)
pad_large = (20, 20)
from .filter_layout import get_filter_layout
def get_main_table(main_data,main_columns):
    pools,pool_rows,pool_data,pool_values,pool_ids = get_main_data_columns(main_data,main_columns)
    main_table = [
        [sg.Table(
            
            values=pool_values,  # Exclude 'txn_history'
            headings=main_columns[:-1],
            display_row_numbers=True,
            auto_size_columns=True,
            num_rows=15,
            key='-MAIN_TABLE-',
            enable_events=True,
            select_mode=sg.TABLE_SELECT_MODE_BROWSE,
            justification='left',
            enable_click_events=True,
            expand_x=True,
            expand_y=True,
            tooltip="Main Data Table"
        )]
    ]
    return main_table

def get_column(data):
    return sg.Column(
    data,
    expand_x=True,
    expand_y=True
    )
def get_meta_bool(key):
    lower_key = key.lower()
    return metadatas.get(lower_key) or False
def create_metadata_layout(init_data):
    metadata_elements = []
    columns = []
    for key,value in metadata_check_bools.items():
        if key == 'image':
            continue  # Image will be handled separately
        insert_key = make_insert(key)
        if key == 'mintAuthority':
            columns.append(get_column(metadata_elements))
            columns.append(sg.VSeparator())
            metadata_elements = []
        metadata_elements.append([sg.Checkbox(f"{key.replace('_', ' ').capitalize()}:",enable_events=True, key=make_check_bool(key), default=value), 
             sg.Text(init_data.get(key, 'N/A'), size=(40, 1), key=insert_key)]  
        )
    columns.append(get_column(metadata_elements))
    return [columns]
def get_pairs_data_layout(main_table,image_layout):
    pairs_data_layout = [
        [
            sg.Column(
                main_table,
                expand_x=True,
                expand_y=True
                ),
            sg.VSeparator(),
            sg.Column(
                image_layout,
                vertical_alignment='top',
                pad=(20, 0),
                scrollable=True,
                size=(400, 400)
                )
        ]
    ]
    return pairs_data_layout

def create_image_layout(image_data,init_data):
    image_layout = [
        [sg.Image(data=image_data,
                  key='-IMAGE-',
                  size=(200, 200),
                  tooltip="Asset Image"),get_filter_layout()]
    ] + create_metadata_layout(init_data or {})
    return image_layout
def get_main_table_layout(main_data,main_columns,image_data=None,init_data=None):
    # Layout for Main Data Table
    main_table_layout = get_main_table(
        main_data,
        main_columns
        )

    # Layout for Asset Details (Image and Metadata)
    image_layout = create_image_layout(
        image_data,
        init_data
        )

    # Combine Main Table and Asset Details Side by Side
    pairs_data_layout = get_pairs_data_layout(
        main_table_layout,
        image_layout
        )

    main_table_frame = sg.Frame('Pairs Data',
                                pairs_data_layout,
                                pad=pad_small,
                                expand_x=True,
                                expand_y=True)
    return main_table_frame
