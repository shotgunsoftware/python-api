# Shotgun Python API

Shotgun provides a simple Python-based API for accessing Shotgun and integrating with other tools. This is the official API that is maintained by Shotgun Software (support@shotgunsoftware.com)

The latest version can always be found at http://github.com/shotgunsoftware/python-api

## Minimum Requirements

* Shotgun server v2.4.12+.
* Python v2.4 - v2.7.

## High Performance Requirements

* For Python 2.4 and 2.5, install [simplejson 2.0.9](http://pypi.python.org/pypi/simplejson/2.0.9)
* For Python 2.6 and higher, install [simplejson 2.1.6](http://pypi.python.org/pypi/simplejson/2.1.6)

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

## Tests 

Integration and unit tests are provided. 

[![Build Status](https://secure.travis-ci.org/shotgunsoftware/python-api.svg?branch=master)](http://travis-ci.org/shotgunsoftware/python-api)


- All tests require the [nose unit testing tools](http://nose.readthedocs.org), and a `tests/config` file (you can copy an example from `tests/example_config`).
- Tests can be run individually like this: `nosetest tests/test_client.py`
- `test_client` and `tests_unit` use mock server interaction and do not require a Shotgun instance to be available (no modifications to `tests/config` are necessary).
- `test_api` and `test_api_long` *do* require a Shotgun instance, with a script key available for the tests. The server and script user values must be supplied in the `tests/config` file. The tests will add test data to your server based on information in your config. This data will be manipulated by the tests, and should not be used for other purposes.
- To run all of the tests, use the shell script `run-tests`.





