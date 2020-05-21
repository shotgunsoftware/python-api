############
Installation
############

********************
Minimum Requirements
********************

- Shotgun server v5.4.14 or higher for API v3.0.16+.
- Shotgun server v2.4.12 or higher for API v3.0.8.
- Shotgun server v1.8 or higher for API v3.0.7.
- Python 2.6 - 2.7 or Python 3.7

.. note::
    Some features of the API are only supported by more recent versions of the Shotgun server.
    These features are added to the Python API in a backwards compatible way so that existing
    scripts will continue to function as expected. Accessing a method that is not supported for
    your version of Shotgun will raise an appropriate exception. In general, we attempt to
    document these where possible.


******************************
Installing into ``PYTHONPATH``
******************************
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


``requirements.txt``
~~~~~~~~~~~~~~~~~~~~
If you're using pip with `requirements.txt`, add the following line::

    git+git://github.com/shotgunsoftware/python-api.git


****************************
Installing with ``setup.py``
****************************

From a local copy of the repository, you can run ``python setup.py install`` to copy the package inside your python ``site-packages``. Note that while ``setuptools`` will complain about syntax errors when installing the library, the library is fully functional. However, it ships with both Python 2 and Python 3 copies of ``httplib2``, which will generate syntax errors when byte-compiling the Python modules.
