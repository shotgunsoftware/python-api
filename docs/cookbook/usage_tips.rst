##############
API Usage Tips
##############

Below is a list of helpful tips when using the Flow Production Tracking API. We have tried to make the API very
simple to use with predictable results while remaining a powerful tool to integrate with your 
pipeline. However, there's always a couple of things that crop up that our users might not be 
aware of. Those are the types of things you'll find below. We'll be adding to this document over 
time as new questions come up from our users that exhibit these types of cases.

*********
Importing
*********

We strongly recommend you import the entire `shotgun_api3` module instead of just importing the
:class:`shotgun_api3.Shotgun` class from the module. There is other important functionality that
is managed at the module level which may not work as expected if you only import the
:class:`shotgun_api3.Shotgun` object.

Do::

    import shotgun_api3

Don't::

    from shotgun_api3 import Shotgun

***************
Multi-threading
***************
The Flow Production Tracking API is not thread-safe. If you want to do threading we strongly suggest that you use
one connection object per thread and not share the connection.

.. _entity-fields:

*************
Entity Fields
*************

When you do a :meth:`~shotgun_api3.Shotgun.find` or a :meth:`~shotgun_api3.Shotgun.create` call
that returns a field of type **entity** or **multi-entity** (for example the 'Assets' column on Shot),
the entities are returned in a standard dictionary::

    {'type': 'Asset', 'name': 'redBall', 'id': 1}

For each entity returned, you will get a ``type``, ``name``, and ``id`` key. This does not mean 
there are fields named ``type`` and ``name`` on the Asset. These are only used to provide a 
consistent way to represent entities returned via the API.

- ``type``: the entity type (CamelCase)
- ``name``: the display name of the entity. For most entity types this is the value of the ``code``
  field but not always. For example, on the Ticket and Delivery entities the ``name`` key would 
  contain the value of the ``title`` field.

.. _custom_entities:

**************
CustomEntities
**************
Entity types are always referenced by their original names. So if you enable CustomEntity01 and
call it **Widget**. When you access it via the API, you'll still use CustomEntity01 as the
``entity_type``.

If you want to be able to remember what all of your CustomEntities represent in a way where you
don't need to go look it up all the time when you're writing a new script, we'd suggest creating
a mapping table or something similar and dumping it in a shared module that your studio uses.
Something like the following::

    # studio_globals.py

    entity_type_map = {
      'Widget': 'CustomEntity01',
      'Foobar': 'CustomEntity02',
      'Baz': 'CustomNonProjectEntity01,
    }

    # or even simpler, you could use a global like this
    ENTITY_WIDGET = 'CustomEntity01'
    ENTITY_FOOBAR = 'CustomEntity02'
    ENTITY_BAZ = 'CustomNonProjectEntity01'

Then when you're writing scripts, you don't need to worry about remembering which Custom Entity
"Foobars" are, you just use your global::

    import shotgun_api3
    import studio_globals

    sg = Shotgun('https://my-site.shotgrid.autodesk.com', 'script_name', '0123456789abcdef0123456789abcdef0123456')
    result = sg.find(studio_globals.ENTITY_WIDGET,
                     filters=[['sg_status_list', 'is', 'ip']],
                     fields=['code', 'sg_shot'])

.. _connection_entities:

******************
ConnectionEntities
******************

Connection entities exist behind the scenes for any many-to-many relationship. Most of the time
you won't need to pay any attention to them. But in some cases, you may need to track information
on the instance of one entity's relationship to another.

For example, when viewing a list of Versions on a Playlist, the Sort Order (``sg_sort_order``) field is an 
example of a field that resides on the connection entity between Playlists and Versions. This
connection entity is appropriately called `PlaylistVersionConnection`. Because any Version can 
exist in multiple Playlists, the sort order isn't specific to the Version, it's specific to 
each _instance_ of the Version in a Playlist. These instances are tracked using connection 
entities in Shtogun and are accessible just like any other entity type in Flow Production Tracking.

To find information about your Versions in the Playlist "Director Review" (let's say it has an 
``id`` of 4). We'd run a query like so::

    filters = [['playlist', 'is', {'type':'Playlist', 'id':4}]]
    fields = ['playlist.Playlist.code', 'sg_sort_order', 'version.Version.code', 'version.Version.user', 'version.Version.entity']
    order=[{'column':'sg_sort_order','direction':'asc'}]
    result = sg.find('PlaylistVersionConnection', filters, fields, order)


Which returns the following::

    [{'id': 28,
      'playlist.Playlist.code': 'Director Review',
      'sg_sort_order': 1.0,
      'type': 'PlaylistVersionConnection',
      'version.Version.code': 'bunny_020_0010_comp_v003',
      'version.Version.entity': {'id': 880,
                                 'name': 'bunny_020_0010',
                                 'type': 'Shot'},
      'version.Version.user': {'id': 19, 'name': 'Artist 1', 'type': 'HumanUser'}},
     {'id': 29,
      'playlist.Playlist.code': 'Director Review',
      'sg_sort_order': 2.0,
      'type': 'PlaylistVersionConnection',
      'version.Version.code': 'bunny_020_0020_comp_v003',
      'version.Version.entity': {'id': 881,
                                 'name': 'bunny_020_0020',
                                 'type': 'Shot'},
      'version.Version.user': {'id': 12, 'name': 'Artist 8', 'type': 'HumanUser'}},
     {'id': 30,
      'playlist.Playlist.code': 'Director Review',
      'sg_sort_order': 3.0,
      'type': 'PlaylistVersionConnection',
      'version.Version.code': 'bunny_020_0030_comp_v003',
      'version.Version.entity': {'id': 882,
                                 'name': 'bunny_020_0030',
                                 'type': 'Shot'},
      'version.Version.user': {'id': 33, 'name': 'Admin 5', 'type': 'HumanUser'}},
     {'id': 31,
      'playlist.Playlist.code': 'Director Review',
      'sg_sort_order': 4.0,
      'type': 'PlaylistVersionConnection',
      'version.Version.code': 'bunny_020_0040_comp_v003',
      'version.Version.entity': {'id': 883,
                                 'name': 'bunny_020_0040',
                                 'type': 'Shot'},
      'version.Version.user': {'id': 18, 'name': 'Artist 2', 'type': 'HumanUser'}},
     {'id': 32,
      'playlist.Playlist.code': 'Director Review',
      'sg_sort_order': 5.0,
      'type': 'PlaylistVersionConnection',
      'version.Version.code': 'bunny_020_0050_comp_v003',
      'version.Version.entity': {'id': 884,
                                 'name': 'bunny_020_0050',
                                 'type': 'Shot'},
      'version.Version.user': {'id': 15, 'name': 'Artist 5', 'type': 'HumanUser'}}]


- ``version`` is the Version record for this connection instance.
- ``playlist`` is the Playlist record for this connection instance.
- ``sg_sort_order`` is the sort order field on the connection instance.

We can pull in field values from the linked Playlist and Version entities using dot notation like 
``version.Version.code``. The syntax is ``fieldname.EntityType.fieldname``. In this example, 
``PlaylistVersionConnection`` has a field named ``version``. That field contains a ``Version`` 
entity. The field we are interested on the Version is ``code``. Put those together with our f
riend the dot and we have ``version.Version.code``.

************************************************************
Flow Production Tracking UI fields not available via the API
************************************************************

Summary type fields like Query Fields and Pipeline Step summary fields are currently only available 
via the UI. Some other fields may not work as expected through the API because they are "display 
only" fields made available for convenience and are only available in the browser UI.

HumanUser
=========

- ``name``: This is a UI-only field that is a combination of the ``firstname`` + ``' '`` + 
  ``lastname``.

Shot
====

**Smart Cut Fields**: These fields are available only in the browser UI. You can read more about 
smart cut fields and the API in the :ref:`Smart Cut Fields doc <smart_cut_fields>`::

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
========================================

The Pipeline Step summary fields on entities that have Tasks aren't currently available via the API 
and are calculated on the client side in the UI. These fields are like ``step_0``, or ``step_13``. 
Note that the Pipeline Step entity itself is available via the API as the entity type ``Step``.

Query Fields
============

Query fields are also summary fields like Pipeline Steps, the query is run from the client side UI 
and therefore is not currently supported in the API.

************
Audit Fields
************
You can set the ``created_by`` and ``created_at`` fields via the API at creation time. This is 
often useful for when you're importing or migrating data from another source and want to keep the 
history in tact. However, you cannot set the ``updated_by`` and ``updated_at`` fields. These are 
automatically set whenever an entity is created or updated.

.. _logging: 

*****************************
Logging Messages from the API
*****************************

The API uses standard python logging but does not define a handler.

To see the logging output in stdout, define a streamhandler in your script::

    import logging
    import shotgun_api3 as shotgun
    logging.basicConfig(level=logging.DEBUG)

To write logging output from the Flow Production Tracking API to a file, define a file handler in your script::

    import logging
    import shotgun_api3 as shotgun
    logging.basicConfig(level=logging.DEBUG, filename='/path/to/your/log')

To suppress the logging output from the API in a script which uses logging, set the level of the 
Flow Production Tracking logger to a higher level::

    import logging
    import shotgun_api3 as shotgun
    sg_log = logging.getLogger('shotgun_api3')
    sg_log.setLevel(logging.ERROR)

*************
Optimizations
*************

.. _combining-related-queries: 

Combining Related Queries
=========================
Reducing round-trips for data via the API can significantly improve the speed of your application.
Much like "Bubble Fields" / "Field Hopping" in the UI, we can poll Flow Production Tracking for data on the fields
of entities linked to our main query, both as a part of the query parameters as well as in the
data returned.

Starting with a simple and common example, many queries require knowing what project your data is
associated with. Without using "field hopping" in an API call, you would first get the project and
then use that data for your follow up query, like so::

    # Get the project
    project_name = 'Big Buck Bunny'
    sg_project = sg.find("Project", [['name', 'is', project_name]])

    # Use project result to get associated shots
    sg_shots = sg.find("Shot", [['project', 'is', sg_project]], ['code'])

With "field hopping" you can combine these queries into::

    # Get all shots on 'Big Buck Bunny' project
    project_name = 'Big Buck Bunny'
    sg_shots = sg.find("Shot", [['project.Project.name', 'is', project_name]], ['code'])

As you can see above, the syntax is to use "``.``" dot notation, joining field names to entity
types in a chain. In this example we start with the field ``project`` on the ``Shot`` entity, then
specify we're looking for the "name" field on the Project entity by specifying ``Project.name``.

Now that we've demonstrated querying using dot notation, let's take a look at returning linked data
by adding the status of each Sequence entity associated with each Shot in our previous query::

    # Get shot codes and sequence status all in one query
    project_name = 'Big Buck Bunny'
    sg_shots = sg.find("Shot", [['project.Project.name', 'is', project_name]],
                       ['code', 'sg_sequence.Sequence.sg_status_list'])

The previous examples use the :meth:`~shotgun_api3.Shotgun.find` method. However, it's also applicable
to the :meth:`~shotgun_api3.Shotgun.create` method.

.. note::
    Due to performance concerns with deep linking, we only support using dot notation chains for
    single-entity relationships. This means that if you try to pull data through a multi-entity
    field you will not get the desired result.