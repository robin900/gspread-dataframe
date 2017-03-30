# -*- coding: utf-8 -*-

"""
gspread_dataframe
~~~~~~~~~~~~~~~~~

This module contains functions to retrieve a gspread worksheet as a
`pandas.DataFrame`, and to set the contents of a worksheet
using a `pandas.DataFrame`. To use these functions, have
Pandas 0.14.0 or greater installed.
"""
from gspread.ns import _ns, _ns1, ATOM_NS, BATCH_NS, SPREADSHEET_NS
from gspread.utils import finditem, numericise as num
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from collections import defaultdict
import itertools
import logging
import re

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

CELLS_FEED_REL = SPREADSHEET_NS + '#cellsfeed'

GOOGLE_SHEET_CELL_UPDATES_LIMIT = 40000

def _cellrepr(value, allow_formulas):
    """
    Get a string representation of dataframe value.

    :param :value: the value to represent
    :param :allow_formulas: if True, allow values starting with '='
            to be interpreted as formulas; otherwise, escape
            them with an apostrophe to avoid formula interpretation.
    """
    if pd.isnull(value):
        return ""
    value = str(value)
    if (not allow_formulas) and value.startswith('='):
        value = "'%s" % value
    return value

def _resize_to_minimum(worksheet, rows=None, cols=None):
    """
    Resize the worksheet to guarantee a minimum size, either in rows,
    or columns, or both.

    Both rows and cols are optional.
    """
    # get the current size
    feed = worksheet.client.get_cells_feed(worksheet)

    current_cols, current_rows = (
        num(feed.find(_ns1('colCount')).text),
        num(feed.find(_ns1('rowCount')).text),
        )
    if rows is not None and rows <= current_rows:
        rows = None
    if cols is not None and cols <= current_cols:
        cols = None

    if cols is not None or rows is not None:
        worksheet.resize(rows, cols)

def _get_all_values(worksheet, evaluate_formulas):
    cells = worksheet._fetch_cells()

    # defaultdicts fill in gaps for empty rows/cells not returned by gdocs
    rows = defaultdict(lambda: defaultdict(str))
    for cell in cells:
        row = rows.setdefault(int(cell.row), defaultdict(str))
        row[cell.col] = cell.value if evaluate_formulas else cell.input_value

    if not rows:
        return []

    all_row_keys = itertools.chain.from_iterable(row.keys() for row in rows.values())
    rect_cols = range(1, max(all_row_keys) + 1)
    rect_rows = range(1, max(rows.keys()) + 1)

    return [[rows[i][j] for j in rect_cols] for i in rect_rows]

def get_as_dataframe(worksheet,
                     evaluate_formulas=False,
                     **options):
    """
    Returns the worksheet contents as a DataFrame.

    :param worksheet: the worksheet.
    :param evaluate_formulas: if True, get the value of a cell after
            formula evaluation; otherwise get the formula itself if present.
            Defaults to False.
    :param \*\*options: all the options for pandas.io.parsers.TextParser,
            according to the version of pandas that is installed.
            (Note: TextParser supports only the 'python' parser engine.)
    :returns: pandas.DataFrame
    """
    all_values = _get_all_values(worksheet, evaluate_formulas)
    return TextParser(all_values, **options).read()

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
    :param include_column_header: if True, add a header row before data with
            column names. (If include_index is True, the index's name will be
            used as its column's header.) Defaults to True.
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
    if include_index:
        col += 1
    if include_column_header:
        row += 1
    if resize:
        worksheet.resize(y + row - 1, x + col - 1)
    else:
        _resize_to_minimum(worksheet, y + row - 1, x + col - 1)

    updates = []

    if include_column_header:
        for idx, val in enumerate(dataframe.columns):
            updates.append(
                (row - 1,
                 col+idx,
                 _cellrepr(val, allow_formulas))
            )
    if include_index:
        for idx, val in enumerate(dataframe.index):
            updates.append(
                (idx+row,
                 col-1,
                 _cellrepr(val, allow_formulas))
            )
        if include_column_header:
            updates.append(
                (row-1,
                 col-1,
                 _cellrepr(dataframe.index.name, allow_formulas))
            )

    for y_idx, value_row in enumerate(dataframe.values):
        for x_idx, cell_value in enumerate(value_row):
            updates.append(
                (y_idx+row,
                 x_idx+col,
                 _cellrepr(cell_value, allow_formulas))
            )

    if not updates:
        logger.debug("No updates to perform on worksheet.")
        return

    # Google limits cell update requests such that the submitted
    # set of updates cannot contain 40,000 cells or more.
    # Make update batches with less than 40,000 elements.
    update_batches = [
        updates[x:x+GOOGLE_SHEET_CELL_UPDATES_LIMIT]
        for x in range(0, len(updates), GOOGLE_SHEET_CELL_UPDATES_LIMIT)
        ]
    logger.debug("%d cell updates to send, will send %d batches of "
        "%d cells maximum", len(updates), len(update_batches), GOOGLE_SHEET_CELL_UPDATES_LIMIT)

    for batch_num, update_batch in enumerate(update_batches):
        batch_num += 1
        logger.debug("Sending batch %d of cell updates", batch_num)
        feed = Element('feed', {
            'xmlns': ATOM_NS,
            'xmlns:batch': BATCH_NS,
            'xmlns:gs': SPREADSHEET_NS
            })

        id_elem = SubElement(feed, 'id')
        id_elem.text = (
            finditem(
                lambda i: i.get('rel') == CELLS_FEED_REL,
                worksheet._element.findall(_ns('link'))
            ).get('href')
            )
        for rownum, colnum, input_value in update_batch:
            code = 'R%sC%s' % (rownum, colnum)
            entry = SubElement(feed, 'entry')
            SubElement(entry, 'batch:id').text = code
            SubElement(entry, 'batch:operation', {'type': 'update'})
            SubElement(entry, 'id').text = id_elem.text + '/' + code
            SubElement(entry, 'link', {
                'rel': 'edit',
                'type': "application/atom+xml",
                'href': id_elem.text + '/' + code})

            SubElement(entry, 'gs:cell', {
                'row': str(rownum),
                'col': str(colnum),
                'inputValue': input_value})

        data = ElementTree.tostring(feed)

        worksheet.client.post_cells(worksheet, data)

    logger.debug("%d total update batches sent", len(update_batches))

