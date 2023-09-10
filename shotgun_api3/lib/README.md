# Lib Submodules

## Third Party Modules

Some third-party modules are bundled with `python-api` inside lib.

## ShotGrid Modules

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