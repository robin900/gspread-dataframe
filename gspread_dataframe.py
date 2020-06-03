# -*- coding: utf-8 -*-

"""
gspread_dataframe
~~~~~~~~~~~~~~~~~

This module contains functions to retrieve a gspread worksheet as a
`pandas.DataFrame`, and to set the contents of a worksheet
using a `pandas.DataFrame`. To use these functions, have
Pandas 0.14.0 or greater installed.
"""
from gspread.utils import fill_gaps
from gspread.models import Cell
import logging
import re

try:
    from collections.abc import defaultdict
except ImportError:
    from collections import defaultdict
try:
    from itertools import chain, zip_longest
except ImportError:
    from itertools import chain, izip_longest as zip_longest

logger = logging.getLogger(__name__)

# pandas import and version check

import pandas as pd
major, minor = tuple([int(i) for i in
    re.search(r'^(\d+)\.(\d+)\..+$', pd.__version__).groups()
    ])
if (major, minor) < (0, 14):
    raise ImportError("pandas version too old (<0.14.0) to support gspread_dataframe")
logger.debug(
    "Imported satisfactory (>=0.14.0) Pandas module: %s",
    pd.__version__)
from pandas.io.parsers import TextParser

__all__ = ('set_with_dataframe', 'get_as_dataframe')

def _cellrepr(value, allow_formulas):
    """
    Get a string representation of dataframe value.

    :param :value: the value to represent
    :param :allow_formulas: if True, allow values starting with '='
            to be interpreted as formulas; otherwise, escape
            them with an apostrophe to avoid formula interpretation.
    """
    if pd.isnull(value) is True:
        return ""
    if isinstance(value, float):
        value = repr(value)
    else:
        value = str(value)
    if value.startswith("'") or ((not allow_formulas) and value.startswith('=')):
        value = "'%s" % value
    return value

def _resize_to_minimum(worksheet, rows=None, cols=None):
    """
    Resize the worksheet to guarantee a minimum size, either in rows,
    or columns, or both.

    Both rows and cols are optional.
    """
    # get the current size
    current_cols, current_rows = (
        worksheet.col_count,
        worksheet.row_count
        )
    if rows is not None and rows <= current_rows:
        rows = None
    if cols is not None and cols <= current_cols:
        cols = None

    if cols is not None or rows is not None:
        worksheet.resize(rows, cols)

def _get_all_values(worksheet, evaluate_formulas):
    data = worksheet.spreadsheet.values_get(
        worksheet.title,
        params={
            'valueRenderOption': ('UNFORMATTED_VALUE' if evaluate_formulas else 'FORMULA'),
            'dateTimeRenderOption': 'FORMATTED_STRING'
        }
    )
    (row_offset, column_offset) = (1, 1)
    (last_row, last_column) = (worksheet.row_count, worksheet.col_count)
    values = data.get('values', [])

    rect_values = fill_gaps(
        values,
        rows=last_row - row_offset + 1,
        cols=last_column - column_offset + 1
    )

    cells = [
        Cell(row=i + row_offset, col=j + column_offset, value=value)
        for i, row in enumerate(rect_values)
        for j, value in enumerate(row)
    ]

    # defaultdicts fill in gaps for empty rows/cells not returned by gdocs
    rows = defaultdict(lambda: defaultdict(str))
    for cell in cells:
        row = rows.setdefault(int(cell.row), defaultdict(str))
        row[cell.col] = cell.value

    if not rows:
        return []

    all_row_keys = chain.from_iterable(row.keys() for row in rows.values())
    rect_cols = range(1, max(all_row_keys) + 1)
    rect_rows = range(1, max(rows.keys()) + 1)

    return [[rows[i][j] for j in rect_cols] for i in rect_rows]

def get_as_dataframe(worksheet,
                     evaluate_formulas=False,
                     **options):
    r"""
    Returns the worksheet contents as a DataFrame.

    :param worksheet: the worksheet.
    :param evaluate_formulas: if True, get the value of a cell after
            formula evaluation; otherwise get the formula itself if present.
            Defaults to False.
    :param \*\*options: all the options for pandas.io.parsers.TextParser,
            according to the version of pandas that is installed.
            (Note: TextParser supports only the default 'python' parser engine,
            not the C engine.)
    :returns: pandas.DataFrame
    """
    all_values = _get_all_values(worksheet, evaluate_formulas)
    return TextParser(all_values, **options).read(options.get('nrows', None))

def _determine_index_column_size(index):
    if hasattr(index, 'levshape'):
        return len(index.levshape)
    return 1

def _determine_column_header_size(columns):
    if hasattr(columns, 'levshape'):
        return len(columns.levshape)
    return 1

def set_with_dataframe(worksheet,
                       dataframe,
                       row=1,
                       col=1,
                       include_index=False,
                       include_column_header=True,
                       resize=False,
                       allow_formulas=True):
    """
    Sets the values of a given DataFrame, anchoring its upper-left corner
    at (row, col). (Default is row 1, column 1.)

    :param worksheet: the gspread worksheet to set with content of DataFrame.
    :param dataframe: the DataFrame.
    :param include_index: if True, include the DataFrame's index as an
            additional column. Defaults to False.
    :param include_column_header: if True, add a header row or rows before data with
            column names. (If include_index is True, the index's name(s) will be
            used as its columns' headers.) Defaults to True.
    :param resize: if True, changes the worksheet's size to match the shape
            of the provided DataFrame. If False, worksheet will only be
            resized as necessary to contain the DataFrame contents.
            Defaults to False.
    :param allow_formulas: if True, interprets `=foo` as a formula in
            cell values; otherwise all text beginning with `=` is escaped
            to avoid its interpretation as a formula. Defaults to True.
    """
    # x_pos, y_pos refers to the position of data rows only,
    # excluding any header rows in the google sheet.
    # If header-related params are True, the values are adjusted
    # to allow space for the headers.
    y, x = dataframe.shape
    index_col_size = 0
    column_header_size = 0
    if include_index:
        index_col_size = _determine_index_column_size(dataframe.index)
        x += index_col_size
    if include_column_header:
        column_header_size = _determine_column_header_size(dataframe.columns)
        y += column_header_size
    if resize:
        worksheet.resize(y, x)
    else:
        _resize_to_minimum(worksheet, y, x)

    updates = []

    if include_column_header:
        elts = list(dataframe.columns)
        # if columns object is hierarchical multi-index, it will span multiple rows
        if column_header_size > 1:
            elts = list(dataframe.columns)
            if include_index:
                if hasattr(dataframe.index, 'names'):
                    index_elts = dataframe.index.names
                else:
                    index_elts = dataframe.index.name
                if not isinstance(index_elts, (list, tuple)):
                    index_elts = [ index_elts ]
                elts = [ ((None,) * (column_header_size - 1)) + (e,) for e in index_elts ] + elts
            for level in range(0, column_header_size):
                for idx, tup in enumerate(elts):
                    updates.append((row, col+idx, _cellrepr(tup[level], allow_formulas)))
                row += 1
        else:
            elts = list(dataframe.columns)
            if include_index:
                if hasattr(dataframe.index, 'names'):
                    index_elts = dataframe.index.names
                else:
                    index_elts = dataframe.index.name
                if not isinstance(index_elts, (list, tuple)):
                    index_elts = [ index_elts ]
                elts = list(index_elts) + elts
            for idx, val in enumerate(elts):
                updates.append(
                    (row,
                     col+idx,
                     _cellrepr(val, allow_formulas))
                )
            row += 1

    values = []
    for value_row, index_value in zip_longest(dataframe.values, dataframe.index):
        if include_index:
            if not isinstance(index_value, (list, tuple)):
                index_value = [ index_value ]
            value_row = list(index_value) + list(value_row)
        values.append(value_row)
    for y_idx, value_row in enumerate(values):
        for x_idx, cell_value in enumerate(value_row):
            updates.append(
                (y_idx+row,
                 x_idx+col,
                 _cellrepr(cell_value, allow_formulas))
            )

    if not updates:
        logger.debug("No updates to perform on worksheet.")
        return

    cells_to_update = [ Cell(row, col, value) for row, col, value in updates ]
    logger.debug("%d cell updates to send", len(cells_to_update))

    resp = worksheet.update_cells(cells_to_update, value_input_option='USER_ENTERED')
    logger.debug("Cell update response: %s", resp)
