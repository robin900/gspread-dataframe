from .mock_worksheet import MockWorksheet

from gspread_dataframe import *
from pandas import Series
import numpy as np

import unittest
from functools import partial
from datetime import datetime, date

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

# Tests

class TestWorksheetReads(unittest.TestCase):

    def setUp(self):
        self.sheet = MockWorksheet()

    def test_noargs(self):
        df = get_as_dataframe(self.sheet)
        self.assertEqual(COLUMN_NAMES, list(df.columns.values))
        self.assertEqual(10, len(df.columns))
        self.assertEqual(9, len(df))
        self.assertEqual(None, df.index.name)
        self.assertEqual('RangeIndex', type(df.index).__name__)
        self.assertEqual(list(range(9)), list(df.index.values))

    def test_evaluate_formulas_true(self):
        df = get_as_dataframe(self.sheet, evaluate_formulas=True)
        self.assertEqual(COLUMN_NAMES, list(df.columns.values))
        self.assertEqual(2.226, df['Formula Column'][0])

    def test_evaluate_formulas_false(self):
        df = get_as_dataframe(self.sheet)
        self.assertEqual(COLUMN_NAMES, list(df.columns.values))
        self.assertEqual('=R[0]C[-1]*2', df['Formula Column'][0])

    def test_usecols(self):
        df = get_as_dataframe(self.sheet, usecols=USECOLS_COLUMN_NAMES)
        self.assertEqual(USECOLS_COLUMN_NAMES, list(df.columns.values))

    def test_indexcol(self):
        df = get_as_dataframe(self.sheet, index_col=4)
        self.assertEqual(9, len(df.columns))
        self.assertEqual('Date Column', df.index.name)
        self.assertEqual('Index', type(df.index).__name__)
        self.assertEqual('2017-03-04', df.index.values[0])

    def test_indexcol_none(self):
        df = get_as_dataframe(self.sheet, index_col=False)
        self.assertEqual(10, len(df.columns))
        self.assertEqual(None, df.index.name)
        self.assertEqual('RangeIndex', type(df.index).__name__)
        self.assertEqual(list(range(9)), list(df.index.values))

    def test_header_false(self):
        df = get_as_dataframe(self.sheet, header=None)
        self.assertEqual(10, len(df))

    def test_header_first_row(self):
        df = get_as_dataframe(self.sheet, header=0)
        self.assertEqual(9, len(df))

    def test_skiprows(self):
        df = get_as_dataframe(self.sheet, skiprows=range(1,4))
        self.assertEqual(6, len(df))

    def test_prefix(self):
        df = get_as_dataframe(self.sheet, skiprows=[0], header=None, prefix='COL')
        self.assertEqual(9, len(df))
        self.assertEqual(['COL' + str(i) for i in range(10)], list(df.columns))

    def test_squeeze(self):
        df = get_as_dataframe(self.sheet, usecols=[0], squeeze=True)
        self.assertTrue(isinstance(df, Series))
        self.assertEqual(9, len(df))

    def test_converters_datetime(self):
        df = get_as_dataframe(self.sheet, converters={'Date Column': lambda x: datetime.strptime(x, '%Y-%m-%d')})
        self.assertTrue(datetime(2017,3,1), df['Date Column'][0])

    def test_dtype(self):
        df = get_as_dataframe(self.sheet, engine='c', dtype={'Numeric Column': np.float64})
        self.assertTrue(np.float64(1.113), df['Numeric Column'][0])


