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
from gspread import Cell
import pandas as pd
import numpy as np
from pandas.io.parsers import TextParser
import logging
import re
from numbers import Real
from six import string_types, ensure_text

try:
    from collections.abc import defaultdict
except ImportError:
    from collections import defaultdict
try:
    from itertools import chain, zip_longest
except ImportError:
    from itertools import chain, izip_longest as zip_longest

logger = logging.getLogger(__name__)

__all__ = ("set_with_dataframe", "get_as_dataframe")

WORKSHEET_MAX_CELL_COUNT = 5000000

def _escaped_string(value, string_escaping):
    if value in (None, ""):
        return ""
    if string_escaping == "default":
        if value.startswith("'"):
            return "'%s" % value
    elif string_escaping == "off":
        return value
    elif string_escaping == "full":
        return "'%s" % value
    elif callable(string_escaping):
        if string_escaping(value):
            return "'%s" % value
    else:
        raise ValueError(
            "string_escaping parameter must be one of: "
            "'default', 'off', 'full', any callable taking one parameter"
        )
    return value


def _cellrepr(value, allow_formulas, string_escaping):
    """
    Get a string representation of dataframe value.

    :param :value: the value to represent
    :param :allow_formulas: if True, allow values starting with '='
            to be interpreted as formulas; otherwise, escape
            them with an apostrophe to avoid formula interpretation.
    """
    if pd.isnull(value) is True:
        return ""
    if isinstance(value, Real):
        return value
    if not isinstance(value, string_types):
        value = str(value)

    value = ensure_text(value, encoding='utf-8')

    if (not allow_formulas) and value.startswith("="):
        return "'%s" % value
    else:
        return _escaped_string(value, string_escaping)


def _resize_to_minimum(worksheet, rows=None, cols=None):
    """
    Resize the worksheet to guarantee a minimum size, either in rows,
    or columns, or both.

    Both rows and cols are optional.
    """
    current_rows, current_cols = (worksheet.row_count, worksheet.col_count)
    desired_rows, desired_cols = (rows, cols)
    if desired_rows is not None and desired_rows <= current_rows:
        desired_rows = current_rows
    if desired_cols is not None and desired_cols <= current_cols:
        desired_cols = current_cols
    resize_cols_first = False
    if desired_rows is not None and desired_cols is not None:
        # special case: if desired sheet size now > cell limit for sheet,
        # resize to exactly rows x cols, which in certain cases will 
        # allow worksheet to stay within cell limit.
        if desired_rows * desired_cols > WORKSHEET_MAX_CELL_COUNT:
            desired_rows, desired_cols = (rows, cols)

        # Large increase that requires exact re-sizing to avoid exceeding
        # cell limit might be, for example, 1000000 rows and 2 columns,
        # for a worksheet that currently has 100 rows and 26 columns..
        # The sheets API, however, applies new rowCount first, then
        # checks against cell count limit before applying new colCount!
        # In the above case, applying new rowCount produces 26 million
        # cells, the limit is exceeded, and API aborts the change and
        # returns a 400 response.
        # So to avoid a 400 response, we must in these cases have
        # _resize_to_minimum call resize twice, first with the value
        # that will reduce cell count and second with the value that
        # will increase cell count.
        # We don't seem to need to address the reversed case, where
        # columnCount is applied first, since Sheets API seems to apply
        # rowCount first in all cases. There is test coverage of this
        # reversed case, to guard against Sheets API changes in future.
        if (
            cols is not None and 
            cols < current_cols and 
            desired_rows * current_cols > WORKSHEET_MAX_CELL_COUNT
        ):
            resize_cols_first = True

    if desired_cols is not None or desired_rows is not None:
        if resize_cols_first:
            worksheet.resize(cols=desired_cols)
            worksheet.resize(rows=desired_rows)
        else:
            worksheet.resize(desired_rows, desired_cols)


def _get_all_values(worksheet, evaluate_formulas):
    data = worksheet.spreadsheet.values_get(
        worksheet.title,
        params={
            "valueRenderOption": (
                "UNFORMATTED_VALUE" if evaluate_formulas else "FORMULA"
            ),
            "dateTimeRenderOption": "FORMATTED_STRING",
        },
    )
    (row_offset, column_offset) = (1, 1)
    (last_row, last_column) = (worksheet.row_count, worksheet.col_count)
    values = data.get("values", [])

    rect_values = fill_gaps(
        values,
        rows=last_row - row_offset + 1,
        cols=last_column - column_offset + 1,
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


def _safe_isnan(val):
    return isinstance(val, float) and np.isnan(val)


def _dataframe_with_corrected_multiIndex(df):
    _nlev = df.index.nlevels
    prev_values = (float('nan'),) * (_nlev - 1)
    new_index_values = []
    for idx_row in df.index.to_numpy():
        if any([_safe_isnan(i) for i in idx_row[0:-1]]):
            # replace each nan with elt from prev_values
            idx_row = tuple( (prev_values[idx] if idx < _nlev and _safe_isnan(i) else i) for idx, i in enumerate(idx_row) )
        else:
            prev_values = tuple(idx_row)
        new_index_values.append(idx_row)
    # TODO preserve columns; and preserve index names somehow!
    new_index = pd.MultiIndex.from_tuples(new_index_values, names=tuple(df.index.names))
    return pd.DataFrame(df.to_numpy(), columns=df.columns.to_numpy(), index=new_index)


def get_as_dataframe(worksheet, evaluate_formulas=False, handle_MultiIndex='repeat', **options):
    """
    Returns the worksheet contents as a DataFrame.

    :param worksheet: the worksheet.
    :param evaluate_formulas: if True, get the value of a cell after
            formula evaluation; otherwise get the formula itself if present.
            Defaults to False.
    :param handle_MultiIndex: XXX TODO.
    :param \*\*options: all the options for pandas.io.parsers.TextParser,
            according to the version of pandas that is installed.
            (Note: TextParser supports only the default 'python' parser engine,
            not the C engine.)
    :returns: pandas.DataFrame
    """
    all_values = _get_all_values(worksheet, evaluate_formulas)
    df = TextParser(all_values, **options).read(options.get("nrows", None))
    if handle_MultiIndex in ('blank', 'merge') and df.index.nlevels > 1:
        df = _dataframe_with_corrected_multiIndex(df)
    return df


def _determine_index_column_size(index):
    if hasattr(index, "levshape"):
        return len(index.levshape)
    return 1


def _determine_column_header_size(columns):
    if hasattr(columns, "levshape"):
        return len(columns.levshape)
    return 1

def set_with_dataframe(worksheet,
                       dataframe,
                       row=1,
                       col=1,
                       include_index=False,
                       include_column_header=True,
                       resize=False,
                       allow_formulas=True,
                       string_escaping='default',
                       handle_MultiIndex='repeat'):
    """
    Sets the values of a given DataFrame, anchoring its upper-left corner
    at (row, col). (Default is row 1, column 1.)

    :param worksheet: the gspread worksheet to set with content of DataFrame.
    :param dataframe: the DataFrame.
    :param row: Row at which to start writing the DataFrame. Default is 1.
    :param col: Column  at which to start writing the DataFrame. Default is 1.
    :param include_index: if True, include the DataFrame's index as an
            additional column. Defaults to False.
    :param include_column_header: if True, add a header row or rows before data
            with column names. (If include_index is True, the index's name(s)
            will be used as its columns' headers.) Defaults to True.
    :param resize: if True, changes the worksheet's size to match the shape
            of the provided DataFrame. If False, worksheet will only be
            resized as necessary to contain the DataFrame contents.
            Defaults to False.
    :param allow_formulas: if True, interprets `=foo` as a formula in
            cell values; otherwise all text beginning with `=` is escaped
            to avoid its interpretation as a formula. Defaults to True.
    :param string_escaping: determines when string values are escaped as text
            literals (by adding an initial `'` character) in requests to
            Sheets API.
            Four parameter values are accepted:
              - 'default': only escape strings starting with a literal `'`
                           character
              - 'off': escape nothing; cell values starting with a `'` will be
                       interpreted by sheets as an escape character followed by
                       a text literal.
              - 'full': escape all string values
              - any callable object: will be called once for each cell's string
                     value; if return value is true, string will be escaped
                     with preceding `'` (A useful technique is to pass a
                     regular expression bound method, e.g.
                     `re.compile(r'^my_regex_.*$').search`.)
            The escaping done when allow_formulas=False (escaping string values
            beginning with `=`) is unaffected by this parameter's value.
            Default value is `'default'`.
    :param handle_MultiIndex: determines how cells are populated with higher-level values
                              from a MultiIndex, if the DataFrame uses a MultiIndex.
                              Three parameter values are accepted:
                                - 'repeat': the higher-level values appear in their own cells
                                            for every row.
                                - 'blank': higher-level values are left blank in rows where
                                           the previous row has the same higher-level value.
                                - 'merge': higher-level values are left blank in rows where
                                           the previous row has the same higher-level value;
                                           in addition, all of the cells in a column or columns
                                           representing the same higher-level value or values
                                           are merged into a single cell.
                              Default value is 'repeat'.

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

    using_multiindex = index_col_size > 1
    using_column_multiindex = column_header_size > 1

    updates = []

    if include_column_header:
        elts = list(dataframe.columns)
        # if columns object is multi-index, it will span multiple rows
        if using_column_multiindex:
            elts = list(dataframe.columns)
            if include_index:
                if hasattr(dataframe.index, "names"):
                    index_elts = dataframe.index.names
                else:
                    index_elts = dataframe.index.name
                if not isinstance(index_elts, (list, tuple)):
                    index_elts = [index_elts]
                elts = [
                    ((None,) * (column_header_size - 1)) + (e,)
                    for e in index_elts
                ] + elts
            for level in range(0, column_header_size):
                for idx, tup in enumerate(elts):
                    # TODO use blank values when handle_MultiIndex in ('blank', 'merge')
                    # TODO also issue some mergeCells requests when == 'merge'
                    updates.append(
                        (
                            row,
                            col + idx,
                            _cellrepr(
                                tup[level], allow_formulas, string_escaping
                            ),
                        )
                    )
                row += 1
        else:
            elts = list(dataframe.columns)
            if include_index:
                if hasattr(dataframe.index, "names"):
                    index_elts = dataframe.index.names
                else:
                    index_elts = dataframe.index.name
                if not isinstance(index_elts, (list, tuple)):
                    index_elts = [index_elts]
                elts = list(index_elts) + elts
            for idx, val in enumerate(elts):
                updates.append(
                    (
                        row,
                        col + idx,
                        _cellrepr(val, allow_formulas, string_escaping),
                    )
                )
            row += 1

    values = []
    for value_row, index_value in zip_longest(
        dataframe.to_numpy('object'), dataframe.index.to_numpy('object')
    ):
        if include_index:
            if not using_multiindex:
                index_value = [ index_value ]
            value_row = list(index_value) + list(value_row)
        values.append(value_row)

    merge_cell_requests = []

    # if using_multiindex:
    # - 'repeat' or other value: do nothing
    # = 'blank': blank out index values that match those of preceding row
    # - 'merge': do same as blank, but remember which cell ranges to do mergeCells for.
    if include_index and using_multiindex and handle_MultiIndex in ('blank', 'merge'):
        index_runs = []
        current_run_rows = []
        current_run_index_values = ()
        for row_idx, value_row in enumerate(values):
            index_values = tuple(value_row[0:index_col_size])
            if current_run_index_values != index_values:
                if current_run_index_values:
                    index_runs.append( (current_run_index_values, current_run_rows[0], current_run_rows[-1]) )
                current_run_rows = [ row_idx ]
                current_run_index_values = index_values
            else:
                current_run_rows.append(row_idx)
        if current_run_rows:
            index_runs.append( (current_run_index_values, current_run_rows[0], current_run_rows[-1]) )
        
        # for each _column_ of the index, find the full consecutive run (or runs) of a single value in that column.
        column_runs = []
        for col_idx in range(index_col_size):
            sliced_runs = [ (c[0][col_idx], (c[1], c[2])) for c in index_runs ]
            current_run = None
            current_run_rows = ()
            for run in sliced_runs:
                if not current_run_rows or run[0] != current_run:
                    if current_run_rows:
                        column_runs.append( (col_idx, current_run, current_run_rows) )
                    current_run = run[0]
                    current_run_rows = run[1]
                else:
                    current_run_rows = (current_run_rows[0], run[1][1])
            if current_run_rows:
                column_runs.append( (col_idx, current_run, current_run_rows) )

        # then for each "column run", blank out the values after the first row's value, and construct a mergeCells request.
        for col_idx, col_value, row_idxs in column_runs:
            start_idx, end_idx_inclusive = row_idxs
            for i in range(start_idx+1, end_idx_inclusive+1):
                values[i][col_idx] = ''
            if handle_MultiIndex == 'merge':
                merge_cell_requests.append({ 'mergeCells': { 'range': GridRange(XXX), 'mergeType': 'MERGE_ALL' } })


    for y_idx, value_row in enumerate(values):
        for x_idx, cell_value in enumerate(value_row):
            updates.append(
                (
                    y_idx + row,
                    x_idx + col,
                    _cellrepr(cell_value, allow_formulas, string_escaping),
                )
            )

    if not updates:
        logger.debug("No updates to perform on worksheet.")
        return

    cells_to_update = [Cell(row, col, value) for row, col, value in updates]
    logger.debug("%d cell updates to send", len(cells_to_update))

    resp = worksheet.update_cells(
        cells_to_update, value_input_option="USER_ENTERED"
    )
    logger.debug("Cell update response: %s", resp)

    if merge_cell_requests:
        logger.debug("Sending batch of %d mergeCells requests", len(merge_cell_requests))
        resp = worksheet.batch_update(merge_cell_requests)
        logger.debug("mergeCells batch update response: %s", resp)
