Changelog
=========


v3.2.1 (2021-02-03)
-------------------
- Bump to v3.2.1. [Robin Thomas]
- Fixes #37. [Robin Thomas]

  Fixes #37. Discovered that Sheets API applies rowCount first, and THEN (#38) checks cell limits, so that if new rowCount * existing colCount > 5000000, then worksheet exceeds limit of 5000000 cells and the whole resize operation is aborted. Solution is to determine if such a condition would occur and then issue the smaller columnCount first as a separate call to reduce
  cell count. Full test coverage added.


v3.2.0 (2020-12-21)
-------------------
- Bump to v3.2.0. [Robin Thomas]
- Fixes #35. Use `to_numpy('object')` to perform needed type conversions
  (#36) [Robin Thomas]

  Fixes #35. Use `to_numpy('object')` to perform needed type conversions (#36) on frame and index values before attempting to update cell values in the worksheet. Now requires Pandas>=0.24.0 instead of >=0.14.0.


v3.1.3 (2020-12-06)
-------------------
- Bump to v3.1.3. [Robin Thomas]
- Fixes #34 by correctly escaping formula expressions =XXX when
  allow_formulas=False. [Robin Thomas]
- Add 3.9 to travis build. [Robin Thomas]
- Pin six to >=1.12.0 to avoid weird environmental dependency problem.
  [Robin Thomas]
- Move to travis-ci.com. [Robin Thomas]


v3.1.2 (2020-11-30)
-------------------
- Bump to v3.1.2. [Robin Thomas]
- Allow for DataFrame cell input values to be unicode objects in Python
  2. [Robin Thomas]
- Black/flake8 all the things. [Robin Thomas]


v3.1.1 (2020-10-14)
-------------------
- Bump to v3.1.1. [Robin Thomas]
- Send numeric values in DataFrames as JSON numeric values to avoid
  locale-specific misinterpretation  (#30) [Robin Thomas]

  * Fixes #29. Ensures that numeric values in DataFrames are sent to Sheets API as JSON numeric
  values, so that locale-specific parsing of decimal separators cannot misinterpret
  the stringified decimal values. Test coverage included.
- 3.9-dev pandas not ready for travis-ci use. [Robin Thomas]
- And let's try 3.9-dev for travis too. [Robin Thomas]
- Add pypy (not yet pypy3) to Travis build. [Robin Thomas]


v3.1.0 (2020-09-15)
-------------------
- Bump to 3.1.0. [Robin Thomas]
- String_escaping now a parameter to set_with_dataframe (#27) [Robin
  Thomas]

  Fixes #26 .

  A new parameter, string_escaping, is added to set_with_dataframe: values are 'default', 'off', 'full', or <any callable>.


v3.0.8 (2020-08-20)
-------------------
- Bump to 3.0.8. [Robin Thomas]
- Update README.rst. [Robin Thomas]

  whitespace tweak
- Rst fix. [Robin Thomas]
- Add dataframe formatting doc section, with link to formatting package.
  [Robin Thomas]
- Argh no 3.9-dev yet. [Robin Thomas]
- Corrected version reference in sphinx docs. [Robin Thomas]
- Removed 3.6, added 3.9-dev to travis build. [Robin Thomas]
- Make collections.abc imports 3.9-compatible. [Robin Thomas]
- Use full version string in sphnix docs. [Robin Thomas]
- Add docs badge to README. [Robin Thomas]
- Add downloads badge. [Robin Thomas]
- Accept nrows only as keyword parameter just as for all other pandas
  parser-related arguments; remove nrows parameter documentation since
  pandas, not this package, owns the parameter and its meaning. [Robin
  Thomas]


v3.0.7 (2020-05-29)
-------------------
- Bump to 3.0.7. [Robin Thomas]
- Support nrows (pandas) parameter properly in get_as_dataframe. [Robin
  Thomas]
- Added to MANIFEST.in using check-manifest tool. [Robin Thomas]


v3.0.6 (2020-04-19)
-------------------
- Bump to 3.0.6. [Robin Thomas]
- Add MANIFEST.in to include VERSION file in sdist. [Robin Thomas]
- Try link again. [Robin Thomas]
- Add pandas doc link. [Robin Thomas]


v3.0.5 (2020-04-02)
-------------------
- Bump to v3.0.5. [Robin Thomas]
- Multiindex column headers (#21) [Robin Thomas]

  * Fixes #20. support for MultiIndex object used as the columns for a DataFrame, and also MultiIndex object used as the index of a DataFrame.
- Support for MultiIndex (hierarchical) indexes for set_with_dataframe.
  [Robin Thomas]
- Fewer py builds. [Robin Thomas]
- 2.7 compatible config reading. [Robin Thomas]
- Try pip cache for travis. [Robin Thomas]
- Bundle up travis secrets for CI build. [Robin Thomas]


v3.0.4 (2020-02-09)
-------------------
- Bump to 3.0.4. [Robin Thomas]
- Fix deprecation warnings due to invalid escape sequences. [Karthikeyan
  Singaravelan]


v3.0.3 (2019-08-06)
-------------------
- Changelog updated for v3.0.3. [Robin Thomas]
- Fixup setup.py for tests_require, bump to 3.0.3. [Robin Thomas]
- Fixes robin900/gspread-dataframe#16. [Robin Thomas]

  Adds integration test coverage (for #16 fix and for future testing).
- Added fury badge. [Robin Thomas]
- Tweak docstring. [Robin Thomas]


v3.0.2 (2018-07-24)
-------------------
- Bump to 3.0.2. [Robin Thomas]
- Rbt fix 13 (#14) [Robin Thomas]

  * Fixes #13. Test coverage added to ensure that include_index=True
  and include_index=False result in the proper cell list sent to gspread.
- Tightened up README intro. [Robin Thomas]


v3.0.1 (2018-04-20)
-------------------
- Bump to 3.0.1. [Robin Thomas]
- Use https for sphinx upload. [Robin Thomas]
- Add long_description for package; indicate that code is
  production/stable. [Robin Thomas]


v3.0.0 (2018-04-19)
-------------------
- Bump VERSION to 3.0.0. [Robin Thomas]
- Changelog for 3.0.0. [Robin Thomas]
- Support for gspread 3.0.0; entire suite of tests refactored to (#12)
  [Robin Thomas]

  use gspread 3.0.0 and its v4 sheets API.

  Fixes #11.
- Updated CHANGES. [Robin Thomas]


v2.1.1 (2018-04-19)
-------------------
- Bump to 2.1.1. [Robin Thomas]
- Update README. [Robin Thomas]
- Prepare for bugfix release by requiring gspread<3.0.0. [Robin Thomas]


v2.1.0 (2017-07-27)
-------------------
- CHANGELOG for 2.1.0. [Robin Thomas]
- Bump version to 2.1.0. [Robin Thomas]
- Safely perform _cellrepr on list objects, since list objects can be
  cell values (#7) [Robin Thomas]

  in a DataFrame. Deal with regression where float precision is mangled
  during round-trip testing, by using repr() on float values and str()
  on other values.

  Fixes #6.
- Complete basic write test. [Robin Thomas]
- Remove stray print stmt. [Robin Thomas]


v2.0.1 (2017-03-31)
-------------------
- CHANGELOG for 2.0.1. [Robin Thomas]
- Bump version to 2.0.1. [Robin Thomas]
- Fixing #4: Respecting the minimum number of cols (#5) [Thorbjørn Wolf]
- Overcome bad default repository url for upload_sphinx. [Robin Thomas]
- Switch to upload3 package. [Robin Thomas]


v2.0.0 (2017-03-29)
-------------------
- Changelog for v2.0.0. [Robin Thomas]
- Get_as_dataframe uses pandas TextParser (#3) [Robin Thomas]

  * pretty easy to hook up TextParser; let's see how all of the option
  handling works in later commits.

  * support evaluate_formulas

  * added basics of unit test suite, with accurate mock worksheet cell feed.

  * strip google sheet ID just to make mock XML smaller

  * fixed docs; added dev requirements in prep to use gitchangelog

  * gitchangelog.rc

  * gitchangelog config file in proper location

  * added latest generated CHANGELOG

  * externalized VERSION file; nearly complete test suite

  * completed test suite

  * updated CHANGELOG

  * back to 2.6-friendly %-based string formatting

  * dispensed with the now-silly-looking lazy ImportError for pandas import.

  * mention pandas.read_csv keyword argument support in README

  * avoid misinterpretation of ** in docstring by sphinx.

  * tighten up all the sphinx stuff

  * show |version| in docs index. parse version properly.

  * remove duplicate sphnix req

  * unworking attempt; need ws entry from worksheets feed to make
  a fully-functioning mock worksheet for writes.

  * write test works now

  * fix bytes/str problem in tests


v1.1.0 (2017-03-28)
-------------------
- LICENSE file via metadata, and correct upload-dir for docs. [Robin
  Thomas]
- Change default include_index=False since that's the common case. Bump
  version to 1.1.0. Complete documentation index.rst. [Robin Thomas]


v1.0.0 (2017-03-28)
-------------------
- List Pandas as dep. [Robin Thomas]
- Aded some sphinx support for steup cfg. [Robin Thomas]
- Initial pre-release commit. [Robin Thomas]
- Initial commit. [Robin Thomas]


