[![VFX Platform](https://img.shields.io/badge/vfxplatform-2020-blue.svg)](http://www.vfxplatform.com/)
[![Python 2.7 3.7](https://img.shields.io/badge/python-2.7%20%7C%203.7-blue.svg)](https://www.python.org/)
[![Reference Documentation](http://img.shields.io/badge/doc-reference-blue.svg)](http://developer.shotgridsoftware.com/python-api)
[![Build Status Linux](https://secure.travis-ci.org/shotgunsoftware/python-api.svg?branch=master)](http://travis-ci.org/shotgunsoftware/python-api)
[![Build status Windows](https://ci.appveyor.com/api/projects/status/slvw7u4jatvdly98/branch/master?svg=true
)](https://ci.appveyor.com/project/jfboismenu/python-api/branch/master)
[![Coverage Status](https://coveralls.io/repos/github/shotgunsoftware/python-api/badge.svg?branch=master)](https://coveralls.io/github/shotgunsoftware/python-api?branch=master)

# Shotgun Python API

ShotGrid provides a simple Python-based API for accessing ShotGrid and integrating with other tools. This is the official API that is maintained by ShotGrid Software (support@shotgunsoftware.com)

The latest version can always be found at http://github.com/shotgunsoftware/python-api

## Minimum Requirements

* ShotGrid server v2.4.12+.
* Python v2.6 - v2.7 or v3.7

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

## Updating HTTPLib2

The API comes with a copy of the `httplib2` inside the `shotgun_api3/lib` folder. To update the copy to a more recent version of the API, you can run the `update_httplib2.py` script at the root of this repository like this:

    python update_httplib2.py vX.Y.Z

where `vX.Y.Z` is a release found on `httplib2`'s [release page](https://github.com/httplib2/httplib2/releases).

## Maintaining Python 2 and 3 compatibility

python-api should remain compatible with both Python 2, and 3.  To make this easier, we use [six](https://six.readthedocs.io/).  When adding code that works with types that have changed between Python 2 and 3, notably strings and files, it's advisable to use the `six` types for casting and comparisons. Be sure to follow Python 2 and 3 compatible conventions in code, especially when raising or capturing exceptions and printing. While we don't use `future`, [this page](https://python-future.org/compatible_idioms.html) contains a fairly comprehensive list of Python 2/3 compatibility sticking points to look out for.

Additionally, the [python-modernize](https://python-modernize.readthedocs.io/en/latest/) tool can be helpful when updating Python 2 code for Python 3 compatibility.

### Examples:

#### Comparisons against changed types:

Python 2:

```
if isinstance(my_variable, str):
```

Python 2/3:

```
if isinstance(my_variable, six.string_types):
```

#### Catching exceptions

Python 2:

```
except SomeExceptionType, e:
    print "I like to swallow exceptions!"
```

Python 2/3:

```
from __future__ import print_function
except SomeExceptionType as e:
    print("I like to swallow exceptions!")
```

#### Print statements

Python 2:

```
print "My spoon is too big!"
```

Python 2/3:

```
from __future__ import print_function
print("My spoon is too big!")
```


Additionally, when testing locally, tests should be run for both python 2 and python 3 to ensure changes won't break cross-compatibility.

## Tests

Integration and unit tests are provided.

- All tests require:
    - The [nose unit testing tools](http://nose.readthedocs.org),
    - The [nose-exclude nose plugin](https://pypi.org/project/nose-exclude/)
    - (Note: Running `pip install -r tests/ci_requirements.txt` will install this package)
- A `tests/config` file (you can copy an example from `tests/example_config`).
- Tests can be run individually like this: `nosetests --config="nose.cfg" tests/test_client.py`
    - Make sure to not forget the `--config="nose.cfg"` option. This option tells nose to use our config file.  This will exclude python 2- and 3-specific files in the `/lib` directory, preventing a failure from being reported by nose for compilation due to incompatible syntax in those files.
- `test_client` and `tests_unit` use mock server interaction and do not require a ShotGrid instance to be available (no modifications to `tests/config` are necessary).
- `test_api` and `test_api_long` *do* require a ShotGrid instance, with a script key available for the tests. The server and script user values must be supplied in the `tests/config` file. The tests will add test data to your server based on information in your config. This data will be manipulated by the tests, and should not be used for other purposes.
- To run all of the tests, use the shell script `run-tests`.

## Release process

### Packaging up new release

1) Update the Changelog in the `HISTORY.rst` file
    - Add bullet points for any changes that have happened since the previous release. This may include changes you did not make so look at the commit history and make sure we don't miss anything. If you notice something was done that wasn't added to the changelog, hunt down that engineer and make them feel guilty for not doing so. This is a required step in making changes to the API.
    - Try and match the language of previous change log messages. We want to keep a consistent voice.
    - Make sure the date of the release matches today. We try and keep this TBD until we're ready to do a release so it's easy to catch that it needs to be updated.
    - Make sure the version number is filled out and correct. We follow semantic versioning.
2) Ensure any changes or additions to public methods are documented
    - Ensure that doc strings are updated in the code itself to work with Sphinx and are correctly formatted.
    - Examples are always good especially if this a new feature or method.
    - Think about a new user to the API trying to figure out how to use the features you're documenting.
3) Update the version value in `python-api/setup.py`  to match the version you are packaging. This controls what version users will get when installing via pip.
4) Update the `__version__` value in `shotgun_api3/shotgun.py` to the version you're releasing. This identified the current version within the API itself.
5) Commit these changes in master with a commit message like `packaging for the vx.x.x release`.
6) Create a tag based off of the master branch called `vx.x.x` to match the version number you're releasing.
7) Push master and your tag to Github.
8) Update the Releases page with your new release.
    - The release should already be there from your tag but if not, create a new one.
    - Add more detailed information regarding the changes in this release. This is a great place to add examples, and reasons for the change!

### Letting the world know
Post a message in the [Pipeline Community channel](https://community.shotgunsoftware.com/c/pipeline) and send an email to [shotgun-dev](https://groups.google.com/a/shotgunsoftware.com/forum/#!forum/shotgun-dev) with a link to the community post.

### Prepare for the Next Dev Cycle
1) Update the `__version__` value in `shotgun_api3/shotgun.py` to the next version number with `.dev` appended to it. For example, `v3.0.24.dev`
2) Add a new section to the Changelog in the `HISTORY.rst` file with the next version number and a TBD date
```
    **v3.0.24 - TBD**
       + TBD
```
3) Commit the changes to master with a commit message like `Bump version to v3.0.24.dev`
4) Push master to Github
