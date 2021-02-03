# -*- coding: utf-8 -*-

import os
import re
import random
import unittest
import itertools
import uuid
import json
from datetime import datetime, date
from gspread.exceptions import APIError
import pandas as pd
from gspread_dataframe import \
    get_as_dataframe, \
    set_with_dataframe, \
    _resize_to_minimum

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

from oauth2client.service_account import ServiceAccountCredentials

import gspread
from gspread import utils

try:
    unicode
except NameError:
    basestring = unicode = str


CONFIG_FILENAME = os.path.join(os.path.dirname(__file__), "tests.config")
CREDS_FILENAME = os.path.join(os.path.dirname(__file__), "creds.json")
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive.file",
]

I18N_STR = u"Iñtërnâtiônàlizætiøn"  # .encode('utf8')

CELL_LIST_FILENAME = os.path.join(os.path.dirname(__file__), "cell_list.json")

STRING_ESCAPING_PATTERN = re.compile(r"(?:'\+|3e50)").match


def read_config(filename):
    config = ConfigParser.ConfigParser()
    with open(filename) as fp:
        if hasattr(config, "read_file"):
            read_func = config.read_file
        else:
            read_func = config.readfp
        read_func(fp)
    return config


def read_credentials(filename):
    return ServiceAccountCredentials.from_json_keyfile_name(filename, SCOPE)


def gen_value(prefix=None):
    if prefix:
        return u"%s %s" % (prefix, gen_value())
    else:
        return unicode(uuid.uuid4())


class GspreadDataframeTest(unittest.TestCase):
    config = None
    gc = None

    @classmethod
    def setUpClass(cls):
        try:
            cls.config = read_config(CONFIG_FILENAME)
            credentials = read_credentials(CREDS_FILENAME)
            cls.gc = gspread.authorize(credentials)
        except IOError as e:
            msg = "Can't find %s for reading test configuration. "
            raise Exception(msg % e.filename)

    def setUp(self):
        if self.__class__.gc is None:
            self.__class__.setUpClass()
        self.assertTrue(isinstance(self.gc, gspread.client.Client))


class WorksheetTest(GspreadDataframeTest):
    """Test for gspread_dataframe using a gspread.Worksheet."""

    spreadsheet = None

    @classmethod
    def setUpClass(cls):
        super(WorksheetTest, cls).setUpClass()
        ss_id = cls.config.get("Spreadsheet", "id")
        cls.spreadsheet = cls.gc.open_by_key(ss_id)
        cls.spreadsheet.batch_update(
            {
                "requests": [
                    {
                        "updateSpreadsheetProperties": {
                            "properties": {"locale": "en_US"},
                            "fields": "locale",
                        }
                    }
                ]
            }
        )
        try:
            test_sheet = cls.spreadsheet.worksheet("wksht_int_test")
            if test_sheet:
                # somehow left over from interrupted test, remove.
                cls.spreadsheet.del_worksheet(test_sheet)
        except gspread.exceptions.WorksheetNotFound:
            pass  # expected

    def setUp(self):
        super(WorksheetTest, self).setUp()
        if self.__class__.spreadsheet is None:
            self.__class__.setUpClass()
        self.sheet = self.spreadsheet.add_worksheet("wksht_int_test", 20, 20)
        self.__class__.spreadsheet.batch_update(
            {
                "requests": [
                    {
                        "updateSpreadsheetProperties": {
                            "properties": {"locale": "en_US"},
                            "fields": "locale",
                        }
                    }
                ]
            }
        )

    def tearDown(self):
        self.spreadsheet.del_worksheet(self.sheet)

    def test_roundtrip(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)

        self.sheet.resize(10, 10)
        cell_list = self.sheet.range("A1:J10")
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)

        df = get_as_dataframe(self.sheet)
        set_with_dataframe(
            self.sheet, df, string_escaping=STRING_ESCAPING_PATTERN
        )
        df2 = get_as_dataframe(self.sheet)
        self.assertTrue(df.equals(df2))

    def test_numeric_values_with_spanish_locale(self):
        # set locale!
        self.__class__.spreadsheet.batch_update(
            {
                "requests": [
                    {
                        "updateSpreadsheetProperties": {
                            "properties": {"locale": "es_ES"},
                            "fields": "locale",
                        }
                    }
                ]
            }
        )
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)

        self.sheet.resize(10, 10)
        cell_list = self.sheet.range("A1:J10")
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)

        df = get_as_dataframe(self.sheet)
        set_with_dataframe(
            self.sheet, df, string_escaping=STRING_ESCAPING_PATTERN
        )
        df2 = get_as_dataframe(self.sheet)
        # check that some numeric values in numeric column are intact
        self.assertEqual(3.804, df2["Numeric Column"][3])
        self.assertTrue(df.equals(df2))

    def test_nrows(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)

        self.sheet.resize(10, 10)
        cell_list = self.sheet.range("A1:J10")
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)

        for nrows in (9, 6, 0):
            df = get_as_dataframe(self.sheet, nrows=nrows)
            self.assertEqual(nrows, len(df))


    def test_resize_to_minimum_large(self):
        self.sheet.resize(100, 26)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        # Large increase that requires exact re-sizing to avoid exceeding 
        # cell limit: this should result in 1000000 rows and 2 columns.
        # The sheets API, however, applies new rowCount first, then
        # checks against cell count limit before applying new colCount!
        # So to avoid a 400 response, we must in these cases have
        # _resize_to_minimum call resize twice, first with the value
        # that will reduce cell count and second with the value that
        # will increase cell count.
        _resize_to_minimum(self.sheet, 1000000, 2)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        self.assertEqual(1000000, self.sheet.row_count)
        self.assertEqual(2, self.sheet.col_count)
        # let's test the other case, where if columnCount were applied
        # first the limit would be exceeded.
        _resize_to_minimum(self.sheet, 10000, 26)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        self.assertEqual(10000, self.sheet.row_count)
        self.assertEqual(26, self.sheet.col_count)

    def test_resize_to_minimum(self):
        self.sheet.resize(100, 26)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        # min rows < current, no change
        _resize_to_minimum(self.sheet, 20, None)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        self.assertEqual(100, self.sheet.row_count)
        self.assertEqual(26, self.sheet.col_count)
        # min cols < current, no change
        _resize_to_minimum(self.sheet, None, 2)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        self.assertEqual(100, self.sheet.row_count)
        self.assertEqual(26, self.sheet.col_count)
        # increase rows
        _resize_to_minimum(self.sheet, 200, None)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        self.assertEqual(200, self.sheet.row_count)
        self.assertEqual(26, self.sheet.col_count)
        # increase cols
        _resize_to_minimum(self.sheet, None, 27)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        self.assertEqual(200, self.sheet.row_count)
        self.assertEqual(27, self.sheet.col_count)
        # increase both
        _resize_to_minimum(self.sheet, 201, 28)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        self.assertEqual(201, self.sheet.row_count)
        self.assertEqual(28, self.sheet.col_count)
        # large increase that exact re-sizing cannot keep below cell limit
        # this should result in a 400 ApiError
        with self.assertRaises(APIError):
            _resize_to_minimum(self.sheet, 1000000, None)
        
    def test_multiindex(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)
        mi = list(
            pd.MultiIndex.from_product(
                [["A", "B"], ["one", "two", "three", "four", "five"]]
            )
        )
        column_names = ["Category", "Subcategory"] + rows[0]
        rows = [column_names] + [
            list(index_tup) + row for row, index_tup in zip(rows[1:], mi)
        ]
        cell_list = self.sheet.range("A1:L10")
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)
        self.sheet.resize(10, 12)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        df = get_as_dataframe(self.sheet, index_col=[0, 1])
        set_with_dataframe(
            self.sheet,
            df,
            resize=True,
            include_index=True,
            string_escaping=STRING_ESCAPING_PATTERN,
        )
        df2 = get_as_dataframe(self.sheet, index_col=[0, 1])
        self.assertTrue(df.equals(df2))

    def test_multiindex_column_header(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)
        column_headers = [
            "SQL",
            "SQL",
            "SQL",
            "SQL",
            "SQL",
            "Misc",
            "Misc",
            "Misc",
            "Misc",
            "Misc",
        ]
        rows = [column_headers] + rows
        cell_list = self.sheet.range("A1:J11")
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)
        self.sheet.resize(11, 10)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        df = get_as_dataframe(self.sheet, header=[0, 1])
        self.assertEqual((2, 10), getattr(df.columns, "levshape", None)),
        set_with_dataframe(
            self.sheet,
            df,
            resize=True,
            string_escaping=STRING_ESCAPING_PATTERN,
        )
        df2 = get_as_dataframe(self.sheet, header=[0, 1])
        self.assertTrue(df.equals(df2))

    def test_int64_json_issue35(self):
        df = pd.DataFrame(
            {
                'a':pd.Series([1, 2, 3],dtype='int64',index=pd.RangeIndex(start=0, stop=3, step=1)),
                'b':pd.Series([4, 5, 6],dtype='int64',index=pd.RangeIndex(start=0, stop=3, step=1))
            },
            index=pd.RangeIndex(start=0, stop=3, step=1)
        )
        set_with_dataframe(
            self.sheet,
            df,
            resize=True,
            include_index=True
        )
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        df2 = get_as_dataframe(self.sheet, dtype={'a': 'int64', 'b': 'int64'}, index_col=0)
        self.assertTrue(df.equals(df2))

    def test_multiindex_column_header_and_multiindex(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)
        mi = list(
            pd.MultiIndex.from_product(
                [["A", "B"], ["one", "two", "three", "four", "five"]]
            )
        )
        column_headers = [
            "",
            "",
            "SQL",
            "SQL",
            "SQL",
            "SQL",
            "SQL",
            "Misc",
            "Misc",
            "Misc",
            "Misc",
            "Misc",
        ]
        column_names = ["Category", "Subcategory"] + rows[0]
        rows = (
            [column_headers]
            + [column_names]
            + [list(index_tup) + row for row, index_tup in zip(rows[1:], mi)]
        )
        cell_list = self.sheet.range("A1:L11")
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)
        self.sheet.resize(11, 12)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        df = get_as_dataframe(self.sheet, index_col=[0, 1], header=[0, 1])
        # fixup because of pandas.read_csv limitations
        df.columns.names = [None, None]
        df.index.names = ["Category", "Subcategory"]
        # set and get, round-trip
        set_with_dataframe(
            self.sheet,
            df,
            resize=True,
            include_index=True,
            string_escaping=STRING_ESCAPING_PATTERN,
        )
        df2 = get_as_dataframe(self.sheet, index_col=[0, 1], header=[0, 1])
        self.assertTrue(df.equals(df2))
