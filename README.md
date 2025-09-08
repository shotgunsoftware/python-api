[![VFX Platform](https://img.shields.io/badge/vfxplatform-2025%20%7C%202024%20%7C%202023%20%7C%202022-blue.svg)](http://www.vfxplatform.com/)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.10%20%7C%203.9-blue.svg)](https://www.python.org/)
[![Reference Documentation](http://img.shields.io/badge/doc-reference-blue.svg)](http://developer.shotgridsoftware.com/python-api)
[![Build Status](https://dev.azure.com/shotgun-ecosystem/Python%20API/_apis/build/status/shotgunsoftware.python-api?branchName=master)](https://dev.azure.com/shotgun-ecosystem/Python%20API/_build/latest?definitionId=108&branchName=master)
[![Coverage Status](https://coveralls.io/repos/github/shotgunsoftware/python-api/badge.svg?branch=master)](https://coveralls.io/github/shotgunsoftware/python-api?branch=master)

# Flow Production Tracking Python API

Autodesk provides a simple Python-based API for accessing Flow Production Tracking and integrating with other tools. This is the official API that is maintained by Autodesk (https://knowledge.autodesk.com/contact-support)

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
    - Make sure to not forget the `--config="nose.cfg"` option. This option tells nose to use our config file.  This will exclude python 2- and 3-specific files in the `/lib` directory, preventing a failure from being reported by nose for compilation due to incompatible syntax in those files.
- `test_client` and `tests_unit` use mock server interaction and do not require a Flow Production Tracking instance to be available (no modifications to `tests/config` are necessary).
- `test_api` and `test_api_long` *do* require a Flow Production Tracking instance, with a script key available for the tests. The server and script user values must be supplied in the `tests/config` file. The tests will add test data to your server based on information in your config. This data will be manipulated by the tests, and should not be used for other purposes.
- To run all of the tests, use the shell script `run-tests`.
