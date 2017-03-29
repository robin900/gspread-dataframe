from gspread.models import Cell
from gspread.ns import _ns

import os.path
from xml.etree import ElementTree as ET

FEED = None

with open(os.path.join(os.path.dirname(__file__), 'cell_feed.xml'), 'r') as f:
    FEED = ET.fromstring(f.read())

class MockWorksheet(object):
    def _fetch_cells(self):
        return [Cell(self, elem) for elem in FEED.findall(_ns('entry'))]

    @property
    def _element(self):
        return FEED

if __name__ == '__main__':
    from gspread_dataframe import *
    ws = MockWorksheet()
    df = get_as_dataframe(ws)
