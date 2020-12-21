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

with open(os.path.join(os.path.dirname(__file__), 'README.rst'), 'rb') as f:
    long_description = f.read()
    if PY3:
        long_description = long_description.decode('utf8')

setup(
    name='gspread-dataframe',
    version=VERSION,
    py_modules=['gspread_dataframe'],
    test_suite='tests',
    install_requires=[
        'gspread>=3.0.0', 
        'pandas>=0.24.0',
        'six>=1.12.0'
        ],
    tests_require=['oauth2client'] + ([] if PY3 else ['mock']),
    description='Read/write gspread worksheets using pandas DataFrames',
    long_description=long_description,
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
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
        "Topic :: Software Development :: Libraries :: Python Modules"
        ],
    zip_safe=True
)
