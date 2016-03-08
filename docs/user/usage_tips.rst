**************
API Usage Tips
**************

Below is a list of helpful tips when using the Shotgun API. We have tried to make the API very 
simple to use with predictable results while remaining a powerful tool to integrate with your 
pipeline. However, there's always a couple of things that crop up that our users might not be 
aware of. Those are the types of things you'll find below. We'll be adding to this document over 
time as new questions come up from our users that exhibit these types of cases.

Entity Fields
=============

When you do a :meth:`~shotgun_api3.Shotgun.find` call that returns a field of type entity or 
multi-entity (for example the 'assets' column on Shot), the entities are returned in a standard 
dictionary::

    {'type': 'Asset', 'name': 'redBall', 'id': 1}

For each entity returned, you will get a ``type``, ``name``, and ``id`` key. This does not mean 
there are fields named ``type`` and ``name`` on the Asset. These are only used to provide a 
consistent way to represent entities returned via the API.

- ``type``: the entity type (CamelCase)
- ``name``: the display name of the entity. For most entity types this is the value of the ``code``
  field but not always. For example, on the Ticket and Delivery entities the ``name`` key would 
  contain the value of the ``title`` field.

Shotgun UI fields not available via the API
===========================================

Summary type fields like Query Fields and Pipeline Step summary fields are currently only available 
via the UI. Some other fields may not work as expected through the API because they are "display 
only" fields made available for convenience and are only available in the browser UI.

HumanUser
---------

- ``name``: This is a UI-only field that is a combination of the ``firstname`` + ``' '`` + 
  ``lastname``.

Shot
----

**Smart Cut Fields**: These fields are available only in the browser UI. You can read more about 
smart cut fields and the API in the Smart Cut Fields doc (link TK)::

    smart_cut_in
    smart_cut_out
    smart_cut_duration
    smart_cut_summary_display
    smart_duration_summary_display
    smart_head_in
    smart_head_out
    smart_head_duration
    smart_tail_in
    smart_tail_out
    smart_tail_duration
    smart_working_duration


Pipeline Step summary fields on entities
----------------------------------------

The Pipeline Step summary fields on entities that have Tasks aren't currently available via the API 
and are calculated on the client side in the UI. These fields are like ``step_0``, or ``step_13``. 
Note that the Pipeline Step entity itself is available via the API as the entity type ``Step``.

Query Fields
------------

Query fields are also summary fields like Pipeline Steps, the query is run from the client side UI 
and therefore is not currently supported in the API.


Audit Fields
============
You can set the ``created_by`` and ``created_at`` fields via the API at creation time. This is 
often useful for when you're importing or migrating data from another source and want to keep the 
history in tact. However, you cannot set the ``updated_by`` and ``updated_at`` fields. These are 
automatically set whenever an entity is created or updated.

.. _logging: 

Logging Messages from the API
=============================

The API uses standard python logging but does not define a handler.

To see the logging output in stdout, define a streamhandler in your script::

    import logging
    import shotgun_api3 as shotgun
    logging.basicConfig(level=logging.DEBUG)

To write logging output from the shotgun API to a file, define a file handler in your script::

    import logging
    import shotgun_api3 as shotgun
    logging.basicConfig(level=logging.DEBUG, filename='/path/to/your/log')

To suppress the logging output from the API in a script which uses logging, set the level of the 
Shotgun logger to a higher level::

    import logging
    import shotgun_api3 as shotgun
    sg_log = logging.getLogger('shotgun_api3')
    sg_log.setLevel(logging.ERROR)

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