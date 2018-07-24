# -*- coding: utf-8 -*-
from .mock_worksheet import MockWorksheet, CELL_LIST, CELL_LIST_STRINGIFIED, CELL_LIST_STRINGIFIED_NO_THINGY

from gspread_dataframe import *
from gspread.models import Cell
import numpy as np
import pandas as pd
from difflib import SequenceMatcher

import unittest
try:
    from unittest.mock import Mock, MagicMock
except ImportError:
    from mock import Mock, MagicMock
from datetime import datetime

# Expected results

COLUMN_NAMES = [
    'Thingy',
    'Syntax',
    'Numeric Column',
    'Formula Column',
    'Date Column',
    'Values are...',
    'Selection',
    'Label(s) referencible in chart title',
    'Dialect-specific implementations',
    'Notes'
]

USECOLS_COLUMN_NAMES = [
    'Thingy',
    'Numeric Column',
    'Formula Column',
    'Date Column'
]

def append_pandas_read_opts(func):
    def wrapper(*args, **kwargs):
        kwargs['na_values'] = []
        kwargs['default_na_values'] = False
        return func(*args, **kwargs)
    return wrapper

#get_as_dataframe = append_pandas_read_opts(get_as_dataframe)

# Tests

class TestWorksheetReads(unittest.TestCase):

    def setUp(self):
        self.sheet = MockWorksheet()

    def test_noargs(self):
        df = get_as_dataframe(self.sheet)
        self.assertEqual(list(df.columns.values), COLUMN_NAMES)
        self.assertEqual(len(df.columns), 10)
        self.assertEqual(len(df), 9)
        self.assertEqual(df.index.name, None)
        self.assertEqual(type(df.index).__name__, 'RangeIndex')
        self.assertEqual(list(df.index.values), list(range(9)))

    def test_evaluate_formulas_true(self):
        df = get_as_dataframe(self.sheet, evaluate_formulas=True)
        self.assertEqual(list(df.columns.values), COLUMN_NAMES)
        self.assertEqual(df['Formula Column'][0], 2.226)

    def test_evaluate_formulas_false(self):
        df = get_as_dataframe(self.sheet)
        self.assertEqual(list(df.columns.values), COLUMN_NAMES)
        self.assertEqual(df['Formula Column'][0], '=R[0]C[-1]*2')

    def test_usecols(self):
        df = get_as_dataframe(self.sheet, usecols=USECOLS_COLUMN_NAMES)
        self.assertEqual(list(df.columns.values), USECOLS_COLUMN_NAMES)

    def test_indexcol(self):
        df = get_as_dataframe(self.sheet, index_col=4)
        self.assertEqual(len(df.columns), 9)
        self.assertEqual(df.index.name, 'Date Column')
        self.assertEqual(type(df.index).__name__, 'Index')
        self.assertEqual(df.index.values[0], '2017-03-04')

    def test_indexcol_none(self):
        df = get_as_dataframe(self.sheet, index_col=False)
        self.assertEqual(len(df.columns), 10)
        self.assertEqual(df.index.name, None)
        self.assertEqual(type(df.index).__name__, 'RangeIndex')
        self.assertEqual(list(df.index.values), list(range(9)))

    def test_header_false(self):
        df = get_as_dataframe(self.sheet, header=None)
        self.assertEqual(len(df), 10)

    def test_header_first_row(self):
        df = get_as_dataframe(self.sheet, header=0)
        self.assertEqual(len(df), 9)

    def test_skiprows(self):
        df = get_as_dataframe(self.sheet, skiprows=range(1,4))
        self.assertEqual(len(df), 6)

    def test_prefix(self):
        df = get_as_dataframe(self.sheet, skiprows=[0], header=None, prefix='COL')
        self.assertEqual(len(df), 9)
        self.assertEqual(df.columns.tolist(), ['COL' + str(i) for i in range(10)])

    def test_squeeze(self):
        df = get_as_dataframe(self.sheet, usecols=[0], squeeze=True)
        self.assertTrue(isinstance(df, pd.Series))
        self.assertEqual(len(df), 9)

    def test_converters_datetime(self):
        df = get_as_dataframe(self.sheet, converters={'Date Column': lambda x: datetime.strptime(x, '%Y-%m-%d')})
        self.assertEqual(df['Date Column'][0], datetime(2017,3,4))

    def test_dtype_raises(self):
        self.assertRaises(ValueError, get_as_dataframe, self.sheet, dtype={'Numeric Column': np.float64})

    def test_no_nafilter(self):
        df = get_as_dataframe(self.sheet, na_filter=False)
        self.assertEqual(df['Dialect-specific implementations'][7], '')

    def test_nafilter(self):
        df = get_as_dataframe(self.sheet, na_filter=True)
        self.assertTrue(np.isnan(df['Dialect-specific implementations'][7]))

    def test_parse_dates_true(self):
        df = get_as_dataframe(self.sheet, index_col=4, parse_dates=True)
        self.assertEqual(df.index[0], pd.Timestamp('2017-03-04 00:00:00'))

    def test_parse_dates_true_infer(self):
        df = get_as_dataframe(self.sheet, index_col=4, parse_dates=True, infer_datetime_format=True)
        self.assertEqual(df.index[0], pd.Timestamp('2017-03-04 00:00:00'))

    def test_parse_dates_custom_parser(self):
        df = get_as_dataframe(self.sheet, parse_dates=[4], date_parser=lambda x: datetime.strptime(x, '%Y-%m-%d'))
        self.assertEqual(df['Date Column'][0], datetime(2017,3,4))


_original_mock_failure_message = Mock._format_mock_failure_message

def _format_mock_failure_message(self, args, kwargs):
    message = 'Expected call: %s\nActual call: %s'
    expected_string = self._format_mock_call_signature(args, kwargs)
    call_args = self.call_args
    if len(call_args) == 3:
        call_args = call_args[1:]
    actual_string = self._format_mock_call_signature(*call_args)
    msg = (message % (expected_string, actual_string))
    if len(call_args[0]) > 1 and isinstance(call_args[0][1], (str, bytes)) and len(args) > 1 and isinstance(args[1], (str, bytes)) and call_args[0][1] != args[1]:
        import difflib
        sm = difflib.SequenceMatcher(None, call_args[0][1], args[1])
        m = sm.find_longest_match(0, len(call_args[0][1]), 0, len(args[1]))
        msg += "; diff: at index %d, expected %s -- actual %s" % (m.a+m.size, call_args[0][1][m.a+m.size-40:m.a+m.size+40], args[1][m.b+m.size-40:m.b+m.size+40])
    return msg

Mock._format_mock_failure_message = _format_mock_failure_message

# have to patch Cell to make cells comparable
def __eq__(self, other):
    if not isinstance(other, self.__class__):
        return False
    return self.row == other.row and self.col == other.col and self.value == other.value
Cell.__eq__ = __eq__

class TestWorksheetWrites(unittest.TestCase):

    def setUp(self):
        self.sheet = MockWorksheet()
        self.sheet.resize = MagicMock()
        self.sheet.update_cells = MagicMock()
        self.sheet.spreadsheet.values_update = MagicMock()

    def test_write_basic(self):
        df = get_as_dataframe(self.sheet, na_filter=False)
        set_with_dataframe(self.sheet, df, resize=True)
        self.sheet.resize.assert_called_once_with(10, 10)
        self.sheet.update_cells.assert_called_once_with(CELL_LIST_STRINGIFIED, value_input_option='USER_ENTERED')

    def test_include_index_false(self):
        df = get_as_dataframe(self.sheet, na_filter=False)
        df_index = df.set_index('Thingy')
        set_with_dataframe(self.sheet, df_index, resize=True, include_index=False)
        self.sheet.resize.assert_called_once_with(10, 9)
        self.sheet.update_cells.assert_called_once_with(CELL_LIST_STRINGIFIED_NO_THINGY, value_input_option='USER_ENTERED')

    def test_include_index_true(self):
        df = get_as_dataframe(self.sheet, na_filter=False)
        df_index = df.set_index('Thingy')
        set_with_dataframe(self.sheet, df_index, resize=True, include_index=True)
        self.sheet.resize.assert_called_once_with(10, 10)
        self.sheet.update_cells.assert_called_once_with(CELL_LIST_STRINGIFIED, value_input_option='USER_ENTERED')

    def test_write_list_value_to_cell(self):
        df = get_as_dataframe(self.sheet, na_filter=False)
        df.at[0, 'Numeric Column'] = [1,2,3]
        set_with_dataframe(self.sheet, df, resize=True)
        self.sheet.resize.assert_called_once_with(10, 10)
        self.sheet.update_cells.assert_called_once_with(CELL_LIST_STRINGIFIED, value_input_option='USER_ENTERED')
