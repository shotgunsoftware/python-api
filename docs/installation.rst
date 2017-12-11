############
Installation
############

********************
Minimum Requirements
********************

- Shotgun server v5.4.14 or higher for API v3.0.16+.
- Shotgun server v2.4.12 or higher for API v3.0.8.
- Shotgun server v1.8 or higher for API v3.0.7.
- Python v2.4 - v2.7. (We do not currently support Python 3)

.. note::
    Some features of the API are only supported by more recent versions of the Shotgun server.
    These features are added to the Python API in a backwards compatible way so that existing
    scripts will continue to function as expected. Accessing a method that is not supported for
    your version of Shotgun will raise an appropriate exception. In general, we attempt to
    document these where possible.


*******************
Installing manually
*******************
You can  `download the latest release from Github <https://github.com/shotgunsoftware/python-api/releases>`_
or `clone the repo <https://github.com/shotgunsoftware/python-api>`_ to your local filesystem.
You'll need to save it somewhere your local Python installation can find it.

.. seealso:: For more information on ``PYTHONPATH`` and using modules in Python, see
    http://docs.python.org/tutorial/modules.html

***********************
Installing with ``pip``
***********************

Installing the Master Branch From Github
========================================
If you wish to install the current master, use the following command::

    pip install git+git://github.com/shotgunsoftware/python-api.git

.. note:: The master branch contains the latest revisions and while largely considered "stable"  it
    is not an official packaged release.

Installing A specific Version From Github
=========================================
To install a specific version of the package from Github, run the following command. This example
installs the v3.0.26 tag, replace the version tag with the one you want::

    pip install git+git://github.com/shotgunsoftware/python-api.git@v3.0.26


requirements.txt
~~~~~~~~~~~~~~~~
If you're using pip with `requirements.txt`, add the following line::

    git+git://github.com/shotgunsoftware/python-api.git
