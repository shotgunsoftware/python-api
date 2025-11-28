[![Supported VFX Platform: 2022 - 2025](https://img.shields.io/badge/VFX_Platform-2022_|_2023_|_2024_|_2025-blue)](http://www.vfxplatform.com/ "Supported VFX Platform")
[![Supported Python versions: 3.9 - 3.11](https://img.shields.io/badge/Python-3.9_|_3.10_|_3.11-blue?logo=python&logoColor=f5f5f5)](https://www.python.org/ "Supported Python versions")
[![Reference Documentation](http://img.shields.io/badge/Reference-documentation-blue.svg?logo=wikibooks&logoColor=f5f5f5)](http://developer.shotgridsoftware.com/python-api)

[![Build Status](https://dev.azure.com/shotgun-ecosystem/Python%20API/_apis/build/status/shotgunsoftware.python-api?branchName=master)](https://dev.azure.com/shotgun-ecosystem/Python%20API/_build/latest?definitionId=108&branchName=master)
[![Coverage Status](https://coveralls.io/repos/github/shotgunsoftware/python-api/badge.svg?branch=master)](https://coveralls.io/github/shotgunsoftware/python-api?branch=master)

# Flow Production Tracking Python API

Autodesk provides a simple Python-based API for accessing Flow Production Tracking and integrating with other tools. This is the official API that is maintained by Autodesk (https://www.autodesk.com/support)

The latest version can always be found at http://github.com/shotgunsoftware/python-api

## Documentation
Tutorials and detailed documentation about the Python API are available at http://developer.shotgridsoftware.com/python-api).

Some useful direct links:

* [Installing](http://developer.shotgridsoftware.com/python-api/installation.html)
* [Tutorials](http://developer.shotgridsoftware.com/python-api/cookbook/tutorials.html)
* [API Reference](http://developer.shotgridsoftware.com/python-api/reference.html)
* [Data Types](http://developer.shotgridsoftware.com/python-api/reference.html#data-types)
* [Filter Syntax](http://developer.shotgridsoftware.com/python-api/reference.html#filter-syntax)

## Changelog

You can see the [full history of the Python API on the documentation site](http://developer.shotgridsoftware.com/python-api/changelog.html).


## Tests

Integration and unit tests are provided.

- All tests require:
    - The [nose unit testing tools](http://nose.readthedocs.org),
    - The [nose-exclude nose plugin](https://pypi.org/project/nose-exclude/)
    - (Note: Running `pip install -r tests/ci_requirements.txt` will install this package)
- A `tests/config` file (you can copy an example from `tests/example_config`).
- Tests can be run individually like this: `nosetests --config="nose.cfg" tests/test_client.py`
    - Make sure to not forget the `--config="nose.cfg"` option. This option tells nose to use our config file.
- `test_client` and `tests_unit` use mock server interaction and do not require a Flow Production Tracking instance to be available (no modifications to `tests/config` are necessary).
- `test_api` and `test_api_long` *do* require a Flow Production Tracking instance, with a script key available for the tests. The server and script user values must be supplied in the `tests/config` file. The tests will add test data to your server based on information in your config. This data will be manipulated by the tests, and should not be used for other purposes.
- To run all of the tests, use the shell script `run-tests`.
