try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os.path
import sys

PY3 = sys.version_info >= (3, 0)

with open(os.path.join(os.path.dirname(__file__), 'VERSION'), 'rb') as f:
    VERSION = f.read()
    if PY3:
        VERSION = VERSION.decode('utf8')
    VERSION = VERSION.strip()

setup(
    name='gspread-dataframe',
    version=VERSION,
    py_modules=['gspread_dataframe'],
    test_suite='tests',
    install_requires=[
        'gspread', 
        'pandas>=0.14.0'
        ],
    description='Read/write gspread worksheets using pandas DataFrames',
    author='Robin Thomas',
    author_email='rthomas900@gmail.com',
    license='MIT',
    url='https://github.com/robin900/gspread-dataframe',
    keywords=['spreadsheets', 'google-spreadsheets', 'pandas', 'dataframe'],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
        "Topic :: Software Development :: Libraries :: Python Modules"
        ],
    zip_safe=True
)
