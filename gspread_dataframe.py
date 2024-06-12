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

WORKSHEET_MAX_CELL_COUNT = 10000000

UNNAMED_COLUMN_NAME_PATTERN = re.compile(r'^Unnamed:\s\d+(?:_level_\d+)?$')

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


def _quote_worksheet_title(title):
    return "'" + title.replace("'", "''") + "'"


def _get_all_values(worksheet, evaluate_formulas):
    data = worksheet.spreadsheet.values_get(
        _quote_worksheet_title(worksheet.title),
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


def get_as_dataframe(worksheet, evaluate_formulas=False, drop_empty_rows=True, drop_empty_columns=True, **options):
    r"""
    Returns the worksheet contents as a DataFrame.

    :param worksheet: the worksheet.
    :param evaluate_formulas: if True, get the value of a cell after
            formula evaluation; otherwise get the formula itself if present.
            Defaults to False.
    :param drop_empty_rows: if True, drop any rows from the DataFrame that have
            only empty (NaN) values. Defaults to True.
    :param drop_empty_columns: if True, drop any columns from the DataFrame
            that have only empty (NaN) values and have no column name 
            (that is, no header value). Named columns (those with a header value)
            that are otherwise empty are retained. Defaults to True.
    :param \*\*options: all the options for pandas.io.parsers.TextParser,
            according to the version of pandas that is installed.
            (Note: TextParser supports only the default 'python' parser engine,
            not the C engine.)
    :returns: pandas.DataFrame
    """
    all_values = _get_all_values(worksheet, evaluate_formulas)
    df = TextParser(all_values, **options).read(options.get("nrows", None))

    # if squeeze=True option was used, df may be a Series.
    # There is special Series logic for our two drop options.
    if isinstance(df, pd.Series):
        if drop_empty_rows:
            df = df.dropna()
        # if this Series is empty and unnamed, it's droppable,
        # and we should return an empty DataFrame instead.
        if drop_empty_columns and df.empty and (not df.name or UNNAMED_COLUMN_NAME_PATTERN.search(df.name)):
           df = pd.DataFrame() 

    # Else df is a DataFrame.
    else:
        if drop_empty_rows:
            df = df.dropna(how='all', axis=0)
            _reconstruct_if_multi_index(df, 'index')
        if drop_empty_columns:
            labels_to_drop = _find_labels_of_empty_unnamed_columns(df)
            if labels_to_drop:
                df = df.drop(labels=labels_to_drop, axis=1)
                _reconstruct_if_multi_index(df, 'columns')

    return df

def _reconstruct_if_multi_index(df, attrname):
    # pandas, even as of 2.2.2, has a bug where a MultiIndex
    # will simply preserve the dropped labels in each level
    # when asked by .levels and .levshape, although the dropped
    # labels won't appear in to_numpy(). We must therefore reconstruct
    # the MultiIndex via to_numpy() -> .from_tuples, and then
    # assign it to the dataframe's appropriate attribute.
    index = getattr(df, attrname)
    if not isinstance(index, pd.MultiIndex):
        return
    reconstructed = pd.MultiIndex.from_tuples(index.to_numpy())
    setattr(df, attrname, reconstructed)


def _label_represents_unnamed_column(label):
    if isinstance(label, str) and UNNAMED_COLUMN_NAME_PATTERN.search(label):
        return True
    # unnamed columns will have an int64 label if header=False was used.
    elif isinstance(label, np.int64):
        return True
    elif isinstance(label, tuple):
        return all([_label_represents_unnamed_column(item) for item in label])
    else:
        return False

def _find_labels_of_empty_unnamed_columns(df):
    return [ 
        label for label 
        in df.columns.to_numpy() 
        if _label_represents_unnamed_column(label) and df[label].isna().all() 
    ]

def _determine_level_count(index):
    if hasattr(index, "levshape"):
        return len(index.levshape)
    return 1

def _index_names(index):
    names = []
    if hasattr(index, "names"):
        names = [ i if i != None else "" for i in index.names ]
    elif index.name not in (None, ""):
        names = [index.name]
    if not any([n not in (None, "") for n in names]):
        names = []
    return names

def set_with_dataframe(
    worksheet,
    dataframe,
    row=1,
    col=1,
    include_index=False,
    include_column_header=True,
    resize=False,
    allow_formulas=True,
    string_escaping="default",
):
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
    """
    # x_pos, y_pos refers to the position of data rows only,
    # excluding any header rows in the google sheet.
    # If header-related params are True, the values are adjusted
    # to allow space for the headers.
    y, x = dataframe.shape
    index_col_size = 0
    column_header_size = 0
    index_names = _index_names(dataframe.index)
    column_names_not_labels = _index_names(dataframe.columns)
    if include_index:
        index_col_size = _determine_level_count(dataframe.index)
        x += index_col_size
    if include_column_header:
        column_header_size = _determine_level_count(dataframe.columns)
        y += column_header_size
        # if included index has name(s) it needs its own header row to accommodate columns' index names
        if column_header_size > 1 and include_index and index_names:
            y += 1
    if row > 1:
        y += row - 1
    if col > 1:
        x += col - 1
    if resize:
        worksheet.resize(y, x)
    else:
        _resize_to_minimum(worksheet, y, x)

    updates = []

    if include_column_header:
        elts = list(dataframe.columns)
        # if columns object is multi-index, it will span multiple rows
        extra_header_row = None
        if column_header_size > 1:
            elts = list(dataframe.columns)
            if include_index:
                extra = tuple(column_names_not_labels) \
                        if column_names_not_labels \
                        else ("",) * column_header_size
                extra = [ extra ]
                if index_col_size > 1:
                    extra = extra + [ ("",) * column_header_size ] * (index_col_size - 1)
                elts = extra + elts
                # if index has names, they need their own header row
                if index_names:
                    extra_header_row = list(index_names) + [ "" ] * len(dataframe.columns)
            for level in range(0, column_header_size):
                for idx, tup in enumerate(elts):
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
            if extra_header_row:
                for idx, val in enumerate(extra_header_row):
                    updates.append(
                        (
                            row,
                            col + idx,
                            _cellrepr(
                                val, allow_formulas, string_escaping
                            ),
                        )
                    )
                row += 1

        else:
            # columns object is not multi-index, columns object's "names"
            # can not be written anywhere in header and be parseable to pandas.
            elts = list(dataframe.columns)
            if include_index:
                # if index has names, they do NOT need their own header row
                if index_names:
                    elts = index_names + elts
                else:
                    elts = ([""] * index_col_size) + elts
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
            if not isinstance(index_value, (list, tuple)):
                index_value = [index_value]
            value_row = list(index_value) + list(value_row)
        values.append(value_row)
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
