try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

VERSION = '1.0.0'

setup(
    name='gspread-dataframe',
    version=VERSION,
    py_modules=['gspread_dataframe'],
    install_requires=['gspread'],
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
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
        "Topic :: Software Development :: Libraries :: Python Modules"
        ],
    zip_safe=True
)
