gspread-dataframe
-----------------

.. image:: https://badge.fury.io/py/gspread-dataframe.svg
    :target: https://badge.fury.io/py/gspread-dataframe

.. image:: https://travis-ci.org/robin900/gspread-dataframe.svg?branch=master
    :target: https://travis-ci.org/robin900/gspread-dataframe

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
such as ``pandas.read_csv``. Consult your Pandas documentation for a full
list of options; since the ``'python'`` engine in Pandas is used for parsing,
only options supported by that engine are acceptable:

.. code:: python

    import pandas as pd
    from gspread_dataframe import get_as_dataframe

    worksheet = some_worksheet_obtained_from_gspread_client

    df = get_as_dataframe(worksheet, parse_dates=True, usecols=[0,2], skiprows=1, header=None)

Installation
------------

Requirements
~~~~~~~~~~~~

* Python 2.6+ or Python 3.2+
* gspread (>=3.0.0; to use older versions of gspread, use gspread-dataframe releases of 2.1.1 or earlier)
* Pandas >= 0.14.0

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
