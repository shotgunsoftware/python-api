############
Installation
############

********************
Minimum Requirements
********************

.. note::
    Some features of the API are only supported by more recent versions of the Flow Production Tracking server.
    These features are added to the Python API in a backwards compatible way so that existing
    scripts will continue to function as expected. Accessing a method that is not supported for
    your version of Flow Production Tracking will raise an appropriate exception. In general, we attempt to
    document these where possible.

Python versions
===============

The Python API library supports the following Python versions: `3.9`, `3.10`,
`3.11`, and `3.13`.
We recommend using Python 3.13.

.. important::
    Python versions older than 3.9 are no longer supported as of March 2025 and compatibility will be discontinued after
    March 2026.


******************************
Installing into ``PYTHONPATH``
******************************
You can  `download the latest release from Github <https://github.com/shotgunsoftware/python-api/releases>`_
or `clone the repo <https://github.com/shotgunsoftware/python-api>`_ to your local filesystem.
You'll need to save it somewhere your local Python installation can find it.

.. seealso:: For more information on ``PYTHONPATH`` and using modules in Python, see
    http://docs.python.org/tutorial/modules.html

.. note::
    :ref:`Visit the introduction to the Python API <pythonoverviewvideo>` to see an overview video of Setting Up Your Environment with the Python API.

***********************
Installing with ``pip``
***********************

Installing the Master Branch From Github
========================================
If you wish to install the current master, use the following command::

    pip install git+https://github.com/shotgunsoftware/python-api.git

.. note:: The master branch contains the latest revisions and while largely considered "stable"  it
    is not an official packaged release.

Installing A specific Version From Github
=========================================
To install a specific version of the package from Github, run the following command. This example
installs the v3.0.26 tag, replace the version tag with the one you want::

    pip install git+https://github.com/shotgunsoftware/python-api.git@v3.0.26


``requirements.txt``
~~~~~~~~~~~~~~~~~~~~
If you're using pip with `requirements.txt`, add the following line::

    git+https://github.com/shotgunsoftware/python-api.git


****************************
Installing with ``setup.py``
****************************

From a local copy of the repository, you can run ``python setup.py install`` to copy the package inside your python ``site-packages``. Note that while ``setuptools`` will complain about syntax errors when installing the library, the library is fully functional.
