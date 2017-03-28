gspread-dataframe
-----------------

If you have pandas (>= 0.14.0) installed, the ``gspread_dataframe``
module offers ``get_as_dataframe`` and ``set_with_dataframe`` functions
to return a worksheet's contents as a DataFrame object, or set a
worksheet's contents using a DataFrame.

.. code:: python

    import pandas as pd
    from gspread_dataframe import get_as_dataframe, set_with_dataframe

    worksheet = some_worksheet_obtained_from_gspread_client

    df = pd.DataFrame.from_records([{'a': i, 'b': i * 2} for i in range(100)])
    set_with_dataframe(worksheet, df)

    df2 = get_as_dataframe(worksheet)

Installation
------------

Requirements
~~~~~~~~~~~~

* Python 2.6+ and Python 3.2+
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
