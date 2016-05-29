.. _installation:

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

IronPython
==========

We do not test against IronPython and cannot be sure that we won't introduce breaking changes or
that we will be compatible with future releases of IronPython. While we don't officially support
IronPython, we certainly will do our best to figure out any issues that come up while using it and
how to avoid them.

As of July 9, 2015 you can look at this fork of the repo to see what changes were needed as of that
date to make things work. The original fork was as of v3.0.20 of the API. Big thanks to our awesome
clients Pixomondo for making their work public and letting us refer to it:

https://github.com/Pixomondo/python-api/tree/v3.0.20.ipy

v3.0.20 can be used with IronPython with a little bit of added work:

- The Python API uses the zlib module to handle decompressing the gzipped response from the server.
  There's no built-in zlib module in IronPython, but there's a potential solution from Jeff Hardy at
  https://bitbucket.org/jdhardy/ironpythonzlib/src/. And the blog post about it here
  http://blog.jdhardy.ca/2008/12/solving-zlib-problem-ironpythonzlib.html

- If you encounter any SSL errors like
  ``unknown field: SERIALNUMBER=0123456789`` or ``:SSL3_GET_SERVER_CERTIFICATE:certificate verify failed``.
  For now you can workaround this problem by disabling ssl certificate validation which we've
  encountered some intermittent issues with. Set ``NO_SSL_VALIDATION = True`` for either case.
  See :const:`shotgun_api3.shotgun.NO_SSL_VALIDATION`

- If you encounter ``LookupError: unknown encoding: idna``, you can force utf-8 by changing
  iri2uri.py ~ln 71 from ``authority = authority.encode('idna')`` to
  ``authority = authority.encode('utf-8')``

- If you encounter an SSL error such as ``SSL3_READ_BYTES:sslv3 alert handshake failure``, then the
  lower level SSL library backing python's network infrastructure is attempting to connect to our
  servers via SSLv3, which is no longer supported. You can use the code from this gist to force the
  SSL connections to use a specific protocol. The forked repo linked above has an example of how to
  do that to force the use of TLSv1.

***********************
Installing with ``pip``
***********************

PyPI
====
The Shotgun API is available in the Python Package Index as ``shotgun-api`` (note the dash instead
of underscore) starting with version 3.0.31::

    pip install shotgun-api


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


*******************
Installing manually
*******************
You can also `download the latest release from Github <https://github.com/shotgunsoftware/python-api/releases>`_
or `clone the repo <https://github.com/shotgunsoftware/python-api>`_ to your local filesystem.
You'll need to save it somewhere your local Python installation can find it.

.. seealso:: For more information on ``PYTHONPATH`` and using modules in Python, see
    http://docs.python.org/tutorial/modules.html
