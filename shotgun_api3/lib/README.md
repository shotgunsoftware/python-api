# Lib Submodules

## Third Party Modules

Some third-party modules are bundled with `python-api` inside lib.

### httplib2

`httplib2` is used to make http connections to the Flow Production Tracking server.

The version of `httplib2` bundled should be updated manually, however its version is included in the unused `shotgun_api3/lib/requirements.txt` to allow Github's automated CVE notifications to work.

## Flow Production Tracking Modules

### sgtimezone

`sgtimezone` contains classes for easing the conversion between the server (UTC) timezone and client timezone.

### mockgun

Mockgun is a Flow Production Tracking API mocker. It's a class that has got *most* of the same
methods and parameters that the Flow Production Tracking API has got. Mockgun is essentially a
Flow Production Tracking *emulator* that (for basic operations) looks and feels like Flow Production Tracking.

The primary purpose of Mockgun is to drive unit test rigs where it becomes
too slow, cumbersome or non-practical to connect to a real Flow Production Tracking. Using a
Mockgun for unit tests means that a test can be rerun over and over again
from exactly the same database state. This can be hard to do if you connect
to a live Flow Production Tracking instance.

## Lib `requirements.txt`

The file `shotgun_api3/lib/requirements.txt` is not used to install any packages, however exists so that automated checks for CVEs in dependencies will know about bundled packages.

For this reason, it's important to add any newly bundled packages to this file, and to keep the file up to date if the bundled version of a module changes.