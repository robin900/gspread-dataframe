# -*- coding: utf-8 -*-

import os
import re
import random
import unittest
import itertools
import uuid
import json
from datetime import datetime, date
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe

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


CONFIG_FILENAME = os.path.join(os.path.dirname(__file__), 'tests.config')
CREDS_FILENAME = os.path.join(os.path.dirname(__file__), 'creds.json')
SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive.file'
]

I18N_STR = u'Iñtërnâtiônàlizætiøn'  # .encode('utf8')

CELL_LIST_FILENAME = os.path.join(os.path.dirname(__file__), 'cell_list.json')

def read_config(filename):
    config = ConfigParser.ConfigParser()
    with open(filename) as fp:
        if hasattr(config, 'read_file'):
            read_func = config.read_file
        else:
            read_func = config.readfp
        read_func(fp)
    return config


def read_credentials(filename):
    return ServiceAccountCredentials.from_json_keyfile_name(filename, SCOPE)


def gen_value(prefix=None):
    if prefix:
        return u'%s %s' % (prefix, gen_value())
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
        ss_id = cls.config.get('Spreadsheet', 'id')
        cls.spreadsheet = cls.gc.open_by_key(ss_id)
        try:
            test_sheet = cls.spreadsheet.worksheet('wksht_int_test')
            if test_sheet:
                # somehow left over from interrupted test, remove.
                cls.spreadsheet.del_worksheet(test_sheet)
        except gspread.exceptions.WorksheetNotFound:
            pass # expected

    def setUp(self):
        super(WorksheetTest, self).setUp()
        if self.__class__.spreadsheet is None:
            self.__class__.setUpClass()
        self.sheet = self.spreadsheet.add_worksheet('wksht_int_test', 20, 20)

    def tearDown(self):
        self.spreadsheet.del_worksheet(self.sheet)

    def test_roundtrip(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)

        self.sheet.resize(10, 10)
        cell_list = self.sheet.range('A1:J10')
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)

        df = get_as_dataframe(self.sheet)
        set_with_dataframe(self.sheet, df)
        df2 = get_as_dataframe(self.sheet)
        self.assertTrue(df.equals(df2))

    def test_nrows(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)

        self.sheet.resize(10, 10)
        cell_list = self.sheet.range('A1:J10')
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)

        for nrows in (9,6,0):
            df = get_as_dataframe(self.sheet, nrows=nrows)
            self.assertEqual(nrows, len(df))

    def test_multiindex(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)
        mi = list(pd.MultiIndex.from_product([['A', 'B'], ['one', 'two', 'three', 'four', 'five']]))
        column_names = ['Category', 'Subcategory'] + rows[0]
        rows = [ column_names ] + [ list(index_tup) + row for row, index_tup in zip(rows[1:], mi) ]
        cell_list = self.sheet.range('A1:L10')
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)
        self.sheet.resize(10, 12)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        df = get_as_dataframe(self.sheet, index_col=[0,1])
        set_with_dataframe(self.sheet, df, resize=True, include_index=True)
        df2 = get_as_dataframe(self.sheet, index_col=[0,1])
        self.assertTrue(df.equals(df2))

    def test_multiindex_column_header(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)
        column_headers = [
            'SQL', 'SQL', 'SQL', 'SQL', 'SQL', 
            'Misc', 'Misc', 'Misc', 'Misc', 'Misc'
        ]
        rows = [ column_headers ] + rows 
        cell_list = self.sheet.range('A1:J11')
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)
        self.sheet.resize(11, 10)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        df = get_as_dataframe(self.sheet, header=[0,1])
        self.assertEqual((2, 10), getattr(df.columns, 'levshape', None)), 
        set_with_dataframe(self.sheet, df, resize=True)
        df2 = get_as_dataframe(self.sheet, header=[0,1])
        self.assertTrue(df.equals(df2))

    def test_multiindex_column_header_and_multiindex(self):
        # populate sheet with cell list values
        rows = None
        with open(CELL_LIST_FILENAME) as f:
            rows = json.load(f)
        mi = list(pd.MultiIndex.from_product([['A', 'B'], ['one', 'two', 'three', 'four', 'five']]))
        column_headers = [
            '', '', 
            'SQL', 'SQL', 'SQL', 'SQL', 'SQL', 
            'Misc', 'Misc', 'Misc', 'Misc', 'Misc'
        ]
        column_names = ['Category', 'Subcategory'] + rows[0]
        rows = [ column_headers ] + [ column_names ] + [ list(index_tup) + row for row, index_tup in zip(rows[1:], mi) ]
        cell_list = self.sheet.range('A1:L11')
        for cell, value in zip(cell_list, itertools.chain(*rows)):
            cell.value = value
        self.sheet.update_cells(cell_list)
        self.sheet.resize(11, 12)
        self.sheet = self.sheet.spreadsheet.worksheet(self.sheet.title)
        df = get_as_dataframe(self.sheet, index_col=[0,1], header=[0,1])
        # fixup because of pandas.read_csv limitations
        df.columns.names = [None, None]
        df.index.names = ['Category', 'Subcategory']
        # set and get, round-trip
        set_with_dataframe(self.sheet, df, resize=True, include_index=True)
        df2 = get_as_dataframe(self.sheet, index_col=[0,1], header=[0,1])
        self.assertTrue(df.equals(df2))

