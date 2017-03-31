Changelog
=========



v2.0.1 (2017-03-31)
-------------------
- Bump version to 2.0.1. [Robin Thomas]
- Fixing #4: Respecting the minimum number of cols (#5) [Thorbjørn Wolf]

v2.0.0 (2017-03-29)
-------------------
- Get_as_dataframe uses pandas TextParser (#3) [Robin Thomas]

  * Old keyword arguments to get_as_dataframe removed, except for
    evaluate_formulas. get_as_dataframe now accepts all pandas
    text parsing keyword arguments.
  * Unit test suite completed.

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


