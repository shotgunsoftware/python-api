# Lib Submodules

## Third Party Modules

Some third-party modules are bundled with `python-api` inside lib.

### httplib2

`httplib2` is used to make http connections to the shotgun server.  We bundle both python2 and python3 compatible versions since httplib2 chose to maintain parallel versions of the module for python 2 and 3 compatibility.

The version of `httplib2` bundled should be updated manually, however its version is included in the unused `shotgun_api3/lib/requirements.txt` to allow Github's automated CVE notifications to work.

### mimetypes

The `mimetypes` module is broken on Windows only for Python 2.7.0 to 2.7.9 inclusively.
We bundle the version from 2.7.10

See bugs:

 * [9291](http://bugs.python.org/issue9291) (Fixed in 2.7.7)
 * [21652](http://bugs.python.org/issue21652) (Fixed in 2.7.8)
 * [22028](http://bugs.python.org/issue22028) (Fixed in 2.7.10)

The version of `mimetypes` bundled should be updated manually if necessary, however it is unlikely this will be needed, as it is only used for Python versions 2.7.0 - 2.7.9, and newer Python versions simply use the native `mimetypes` module.

### six

Six is a Python 2/3 compatibility library.  In python-api, it's used to make simultaneous support for Python on 2 and 3 easier to maintain and more readable, but allowing the use of common helper functions, unified interfaces for modules that changed, and variables to ease type comparisons.  For more on six, see the [documentation](https://six.readthedocs.io/).

The version of `six` bundled should be updated manually, however its version is included in the unused `shotgun_api3/lib/requirements.txt` to allow Github's automated CVE notifications to work.

## Shotgun Modules

### sgsix

`sgsix` is a module that contains extensions to `six`.  These might be additional helper functions, variables, etc. that supplement six's functionality.  It is intended that `sgsix` can be used within other packages that include or depend on the `python-api` package as well.

### sgtimezone

`sgtimezone` contains classes for easing the conversion between the server (UTC) timezone and client timezone.

### mockgun

Mockgun is a ShotGrid API mocker. It's a class that has got *most* of the same
methods and parameters that the ShotGrid API has got. Mockgun is essentially a
ShotGrid *emulator* that (for basic operations) looks and feels like ShotGrid.

The primary purpose of Mockgun is to drive unit test rigs where it becomes
too slow, cumbersome or non-practical to connect to a real ShotGrid. Using a
Mockgun for unit tests means that a test can be rerun over and over again
from exactly the same database state. This can be hard to do if you connect
to a live ShotGrid instance.

## Lib `requirements.txt`

The file `shotgun_api3/lib/requirements.txt` is not used to install any packages, however exists so that automated checks for CVEs in dependencies will know about bundled packages.

For this reason, it's important to add any newly bundled packages to this file, and to keep the file up to date if the bundled version of a module changes.