import operator
import FreeSimpleGUI as sg

def sort_table(table_data, cols):
    """
    Sort a table (list of rows) by multiple columns.
    :param table_data: A list of lists where each inner list is a row.
    :param cols: A tuple or list of column indices to sort by.
    :return: Sorted table data.
    """
    # Sort in reverse order so that earlier columns in the tuple have higher priority.
    for col in reversed(cols):
        try:
            table_data = sorted(table_data, key=operator.itemgetter(col))
        except Exception as e:
            sg.popup_error('Error in sort_table', f'Exception sorting by column {col}: {e}')
    return table_data

def handle_sort_event(event, data, headings, window, table_key='-TABLE-'):
    """
    Checks for a header click event and sorts the table accordingly.

    :param event: The event returned by the window.read() loop.
    :param data: Full table data, with the header row at index 0.
    :param headings: List of table headings.
    :param window: The PySimpleGUI window.
    :param table_key: Key for the Table element.
    :return: The updated table data (including the header row).
    """
    # The event from a table click will be a tuple: (table_key, '+CLICKED+', (row, col))
    if isinstance(event, tuple) and event[0] == table_key:
        row, col = event[2]
        # If the header was clicked, row will be -1 and col will be >= 0.
        if row == -1 and col != -1:
            # Sort by the clicked column, using a secondary sort on column 0 for stability.
            sorted_body = sort_table(data[1:], (col, 0))
            # Update the table element (display only the body rows).
            window[table_key].update(values=sorted_body)
            # Return the updated full data (header + sorted body).
            return [data[0]] + sorted_body
    return data
