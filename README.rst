gspread-dataframe
-----------------

.. image:: https://badge.fury.io/py/gspread-dataframe.svg
    :target: https://badge.fury.io/py/gspread-dataframe

.. image:: https://travis-ci.com/robin900/gspread-dataframe.svg?branch=master
    :target: https://travis-ci.com/robin900/gspread-dataframe

.. image:: https://img.shields.io/pypi/dm/gspread-dataframe.svg
    :target: https://pypi.org/project/gspread-dataframe

.. image:: https://readthedocs.org/projects/gspread-dataframe/badge/?version=latest
    :target: https://gspread-dataframe.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This package allows easy data flow between a worksheet in a Google spreadsheet
and a Pandas DataFrame. Any worksheet you can obtain using the ``gspread`` package
can be retrieved as a DataFrame with ``get_as_dataframe``; DataFrame objects can
be written to a worksheet using ``set_with_dataframe``:

.. code:: python

    import pandas as pd
    from gspread_dataframe import get_as_dataframe, set_with_dataframe

    worksheet = some_worksheet_obtained_from_gspread_client

    df = pd.DataFrame.from_records([{'a': i, 'b': i * 2} for i in range(100)])
    set_with_dataframe(worksheet, df)

    df2 = get_as_dataframe(worksheet)

The ``get_as_dataframe`` function supports the keyword arguments
that are supported by your Pandas version's text parsing readers,
such as ``pandas.read_csv``. Consult `your Pandas documentation for a full list of options <https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html>`__. Since the ``'python'`` engine in Pandas is used for parsing,
only options supported by that engine are acceptable:

.. code:: python

    import pandas as pd
    from gspread_dataframe import get_as_dataframe

    worksheet = some_worksheet_obtained_from_gspread_client

    df = get_as_dataframe(worksheet, parse_dates=True, usecols=[0,2], skiprows=1, header=None)

Formatting Google worksheets for DataFrames
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you install the ``gspread-formatting`` package, you can additionally format a Google worksheet to suit the  
DataFrame data you've just written. See the `package documentation for details <https://github.com/robin900/gspread-formatting#formatting-a-worksheet-using-a-pandas-dataframe>`__, but here's a short example using the default formatter:

.. code:: python

    import pandas as pd
    from gspread_dataframe import get_as_dataframe, set_with_dataframe
    from gspread_formatting.dataframe import format_with_dataframe

    worksheet = some_worksheet_obtained_from_gspread_client

    df = pd.DataFrame.from_records([{'a': i, 'b': i * 2} for i in range(100)])
    set_with_dataframe(worksheet, df)
    format_with_dataframe(worksheet, df, include_column_header=True)

    
Installation
------------

Requirements
~~~~~~~~~~~~

* Python 2.7, 3+
* gspread (>=3.0.0; to use older versions of gspread, use gspread-dataframe releases of 2.1.1 or earlier)
* Pandas >= 0.24.0

From PyPI
~~~~~~~~~

.. code:: sh

    pip install gspread-dataframe

From GitHub
~~~~~~~~~~~

.. code:: sh

    git clone https://github.com/robin900/gspread-dataframe.git
    cd gspread-dataframe
    python setup.py install
