###################
Shotgun Python API3
###################
Release v\ |version|. (:ref:`Installation <installation>`)

Shotgun provides a simple Python-based API for accessing Shotgun and integrating with other tools.

User Guide
==========
.. toctree::
    :maxdepth: 2

    user/intro
    user/usage_tips
    user/tutorials
   
Developer API
=============
.. toctree::
    :maxdepth: 3
    
    api/reference
    server_changelog

Minimum Requirements
====================

- Shotgun server v5.4.14 or higher for API v3.0.16.
- Shotgun server v2.4.12 or higher for API v3.0.8.
- Shotgun server v1.8 or higher for API v3.0.7.
- Python v2.4 - v2.7. (We do not currently support Python 3)

Installation
============

Installing with `pip`
---------------------
PyPI
~~~~
The Shotgun API is available in the Python Package Index as ``shotgun-api`` (note the dash instead 
of underscore) starting with version 3.0.27.::

    pip install shotgun-api


Master 
~~~~~~
If you wish to install the current master, use the following command::

    pip install git+git://github.com/shotgunsoftware/python-api.git

.. note:: that master contains the latest revisions and while largely considered "stable"  it is 
    not an official packaged release.

Specific Versions from Github
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To install a specific version of the package from Github, run the following command 
(This example installs the v3.0.26 tag. Replace the version tag with the one you want).::

    pip install git+git://github.com/shotgunsoftware/python-api.git@v3.0.26


requirements.txt
~~~~~~~~~~~~~~~~
If you're using pip with `requirements.txt`, add the following line::

    git+git://github.com/shotgunsoftware/python-api.git

Installing manually
-------------------
If you're not using ``pip`` to install the Shotgun Python API (eg. you've forked it or downloaded
it directly from Github), you'll need to save it somewhere your python installation can find it.


.. seealso:: For more information on ``PYTHONPATH`` and using modules in Python, see 
    http://docs.python.org/tutorial/modules.html




