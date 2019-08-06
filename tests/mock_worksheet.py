import os.path
import json
from gspread.models import Cell
from gspread_dataframe import _cellrepr

def contents_of_file(filename, et_parse=True):
    with open(os.path.join(os.path.dirname(__file__), filename), 'r') as f:
        return json.load(f)

SHEET_CONTENTS_FORMULAS = contents_of_file('sheet_contents_formulas.json')
SHEET_CONTENTS_EVALUATED = contents_of_file('sheet_contents_evaluated.json')
CELL_LIST = [
   Cell(row=i+1, col=j+1, value=value)
   for i, row in enumerate(contents_of_file('cell_list.json'))
   for j, value in enumerate(row)
]
CELL_LIST_STRINGIFIED = [
   Cell(row=i+1, col=j+1, value=_cellrepr(value, allow_formulas=True))
   for i, row in enumerate(contents_of_file('cell_list.json'))
   for j, value in enumerate(row)
]

_without_index = contents_of_file('cell_list.json')
for _r in _without_index:
    del _r[0]

CELL_LIST_STRINGIFIED_NO_THINGY = [
   Cell(row=i+1, col=j+1, value=_cellrepr(value, allow_formulas=True))
   for i, row in enumerate(_without_index)
   for j, value in enumerate(row)
]

class MockWorksheet(object):
    def __init__(self):
        self.row_count = 10
        self.col_count = 10
        self.id = 'fooby'
        self.title = 'gspread dataframe test'
        self.spreadsheet = MockSpreadsheet()

class MockSpreadsheet(object):

    def values_get(self, *args, **kwargs):
        if kwargs.get('params', {}).get('valueRenderOption') == 'UNFORMATTED_VALUE':
            return SHEET_CONTENTS_EVALUATED
        if kwargs.get('params', {}).get('valueRenderOption') == 'FORMULA':
            return SHEET_CONTENTS_FORMULAS

if __name__ == '__main__':
    from gspread_dataframe import *
    ws = MockWorksheet()
