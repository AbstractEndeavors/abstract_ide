# Update main table layout to include a "Load More" button
def get_main_table_layout(main_data, main_columns):
    main_table = [
        [sg.Table(
            values=get_main_data_columns(main_columns, main_data),
            headings=main_columns[:-1],
            display_row_numbers=True,
            auto_size_columns=True,
            num_rows=15,
            key='-MAIN_TABLE-',
            enable_events=True,
            select_mode=sg.TABLE_SELECT_MODE_BROWSE,
            justification='left',
            expand_x=True,
            expand_y=True,
            tooltip="Main Data Table"
        )],
        [
            sg.Button('Load More', key='-LOAD_MORE-', size=(15, 1))
        ]
    ]
    return main_table
