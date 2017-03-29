from gspread.models import Cell
from gspread.ns import _ns

import os.path
from xml.etree import ElementTree as ET

CELL_FEED = None
WORKSHEET_FEED = None

def contents_of_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), 'r') as f:
        return ET.fromstring(f.read())

CELL_FEED = contents_of_file('cell_feed.xml')
WORKSHEET_FEED = contents_of_file('worksheet_feed.xml')
POST_CELLS_EXPECTED = contents_of_file('post_cells_expected.xml')

class MockWorksheet(object):
    def _fetch_cells(self):
        return [Cell(self, elem) for elem in CELL_FEED.findall(_ns('entry'))]

    @property
    def _element(self):
        return WORKSHEET_FEED

if __name__ == '__main__':
    from gspread_dataframe import *
    ws = MockWorksheet()
    df = get_as_dataframe(ws)
