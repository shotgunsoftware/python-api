# pylint: disable=invalid-name
"""Shotgun_api3"""
name = "shotgun_api3"

_shotgunSoftwareVersion = "3.10.2"
_rdoVersion = "1.0.0"
version = "{0}-rdo-{1}".format(_shotgunSoftwareVersion, _rdoVersion)

authors = ["shotgundev@rodeofx.com"]

description = "Fork of the python api of shotgun."

requires = ["python-3.9+"]

private_build_requires = ["rdo_package_utils"]

build_command = "python {root}/build.py {install}"

uuid = "9E411E66-9F35-49BC-AC2E-E9DC6D50D109"


def commands():
    """Commands"""
    env.PYTHONPATH.append("{root}/")
