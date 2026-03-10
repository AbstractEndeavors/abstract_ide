from ..imports import *
pad_small = (5, 5)
pad_medium = (10, 10)
pad_large = (20, 20)
def create_metadata_check_boxes():
    metaKeys = list(metaDataTypeKeys.keys())
    halfLen = int(len(metaKeys)/2)
    metaChecks1 = metaKeys[:halfLen]
    metaChecks2 = metaKeys[halfLen:]
    checkboxes1 = [
        sg.Checkbox(key.replace('_', ' ').capitalize(),enable_events=True, key=make_check_bool(key), default=True)
        for key in metaChecks1 if key != 'image'
    ]
    checkboxes2 = [
        sg.Checkbox(key.replace('_', ' ').capitalize(),enable_events=True, key=make_check_bool(key), default=True)
        for key in metaChecks2 if key != 'image'
    ]
    return checkboxes1,checkboxes2
# Layout for Filters with Checkboxes
def create_filter_layout():
    # Create checkboxes for each metadata key
    #heckboxes1,checkboxes2 = create_metadata_check_boxes()
    filter_layout = [
        [
            sg.Frame(
                'SOL Amount Threshold:',
                 [[sg.Input(default_text='10', size=(10, 1),
                            key='-SOL_THRESHOLD_INPUT-'),
                   sg.Button('-',
                             size=(3,1),
                             key='-DECREMENT_SOL-',
                             pad=(5,0)),
                   sg.Button('+',
                             size=(3,1),
                             key='-INCREMENT_SOL-',
                             pad=(0,0))
                   ]]
                 ),
            
        [sg.Frame('Timestamp Range:', [[sg.Combo(
                values=['Last 1 min'] + [f"Last {i} min" for i in range(5,55,5)] + ["Last Hour", "Last Day", "Last Week", "Last Month", "All Time"],
                default_value="All Time",
                key='-TIME_RANGE-',
                readonly=True,
                enable_events=True,
                size=(15, 1)
            )]])],
            #sg.Frame('Metadata Filters:',[checkboxes1,[checkboxes2]]),
            [sg.Button('Apply Filters', key='-APPLY_FILTERS-', pad=(10,0))],
        ]
    ]

    return filter_layout


def get_filter_layout():
    # Retrieve the filter layout from get_filter() and wrap it in a frame.
    filter_layout = create_filter_layout()
    filter_frame = sg.Frame('Filter Criteria',
                            font=('Any', 14),
                            layout=filter_layout,
                            pad=pad_small,
                            expand_x=True)
    return filter_frame

