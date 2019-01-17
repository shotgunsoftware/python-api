[![VFX Platform](https://img.shields.io/badge/vfxplatform-2018-yellow.svg)](http://www.vfxplatform.com/)
[![Reference Documentation](http://img.shields.io/badge/doc-reference-blue.svg)](http://developer.shotgunsoftware.com/python-api)
[![Build Status Linux](https://secure.travis-ci.org/shotgunsoftware/python-api.svg?branch=master)](http://travis-ci.org/shotgunsoftware/python-api)
[![Build status Windows](https://ci.appveyor.com/api/projects/status/slvw7u4jatvdly98/branch/master?svg=true
)](https://ci.appveyor.com/project/jfboismenu/python-api/branch/master)
[![Coverage Status](https://coveralls.io/repos/github/shotgunsoftware/python-api/badge.svg?branch=master)](https://coveralls.io/github/shotgunsoftware/python-api?branch=master)
[![Linting](https://img.shields.io/badge/PEP8%20by-Hound%20CI-a873d1.svg)](https://houndci.com)

# Shotgun Python API

Shotgun provides a simple Python-based API for accessing Shotgun and integrating with other tools. This is the official API that is maintained by Shotgun Software (support@shotgunsoftware.com)

The latest version can always be found at http://github.com/shotgunsoftware/python-api

## Minimum Requirements

* Shotgun server v2.4.12+.
* Python v2.6 - v2.7.

## High Performance Requirements

* Install [simplejson 2.1.6](http://pypi.python.org/pypi/simplejson/2.1.6)

## Documentation
Tutorials and detailed documentation about the Python API are available at http://developer.shotgunsoftware.com/python-api). 

Some useful direct links:

* [Installing](http://developer.shotgunsoftware.com/python-api/installation.html)
* [Tutorials](http://developer.shotgunsoftware.com/python-api/cookbook/tutorials.html)
* [API Reference](http://developer.shotgunsoftware.com/python-api/reference.html)
* [Data Types](http://developer.shotgunsoftware.com/python-api/reference.html#data-types)
* [Filter Syntax](http://developer.shotgunsoftware.com/python-api/reference.html#filter-syntax)

## Changelog

You can see the [full history of the Python API on the documentation site](http://developer.shotgunsoftware.com/python-api/changelog.html).

## Updating HTTPLib2

1. Download the latest version of HTTPLib2 at https://pypi.org/project/httplib2.
2. Extract the python2/httplib2 into shotgun_api3/lib/http2lib without the test folder.
3. Scan the files for any references to importing httplib2 and make sure they import "from ." instead of "from httplib2" because the library isn't in the Python path.

## Tests 

Integration and unit tests are provided. 

- All tests require the [nose unit testing tools](http://nose.readthedocs.org), and a `tests/config` file (you can copy an example from `tests/example_config`).
- Tests can be run individually like this: `nosetest tests/test_client.py`
- `test_client` and `tests_unit` use mock server interaction and do not require a Shotgun instance to be available (no modifications to `tests/config` are necessary).
- `test_api` and `test_api_long` *do* require a Shotgun instance, with a script key available for the tests. The server and script user values must be supplied in the `tests/config` file. The tests will add test data to your server based on information in your config. This data will be manipulated by the tests, and should not be used for other purposes.
- To run all of the tests, use the shell script `run-tests`.





