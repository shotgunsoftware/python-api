.. currentmodule:: shotgun_api3

.. _apireference:

#############
API Reference
#############


*****************************
``shotgun`` Module Attributes
*****************************

The :mod:`~shotgun_api3.shotgun` module is a container for the :class:`~shotgun.Shotgun`
class. There are a couple of useful attributes to note.

.. automodule:: shotgun_api3.shotgun
    :members: NO_SSL_VALIDATION, LOG
    :private-members:
    :special-members:

***************
Shotgun()
***************

.. autoclass:: Shotgun
    :show-inheritance:

***************
Shotgun Methods
***************

The majority of functionality is contained within the :class:`~shotgun_api3.Shotgun` class. 
The documentation for all of the methods you'll need in your scripts lives in here.

.. rubric:: Connection & Authentication

.. autosummary:: 
    :nosignatures:

    Shotgun.connect
    Shotgun.close
    Shotgun.authenticate_human_user
    Shotgun.get_session_token
    Shotgun.set_up_auth_cookie
    Shotgun.add_user_agent
    Shotgun.reset_user_agent
    Shotgun.set_session_uuid
    Shotgun.info  

.. rubric:: CRUD Methods

.. autosummary:: 
    :nosignatures:

    Shotgun.create
    Shotgun.find
    Shotgun.find_one
    Shotgun.update
    Shotgun.delete
    Shotgun.revive
    Shotgun.batch
    Shotgun.summarize
    Shotgun.note_thread_read
    Shotgun.text_search
    Shotgun.update_project_last_accessed
    Shotgun.work_schedule_read
    Shotgun.work_schedule_update
    Shotgun.preferences_read    

.. rubric:: Working With Files

.. autosummary:: 
    :nosignatures:

    Shotgun.upload
    Shotgun.upload_thumbnail
    Shotgun.upload_filmstrip_thumbnail
    Shotgun.download_attachment
    Shotgun.get_attachment_download_url
    Shotgun.share_thumbnail

.. rubric:: Activity Stream

.. autosummary:: 
    :nosignatures:

    Shotgun.activity_stream_read
    Shotgun.follow
    Shotgun.unfollow
    Shotgun.followers
    Shotgun.following

.. rubric:: Working with the Shotgun Schema and Preferences

.. autosummary:: 
    :nosignatures:

    Shotgun.schema_entity_read
    Shotgun.schema_field_read
    Shotgun.schema_field_create
    Shotgun.schema_field_update
    Shotgun.schema_field_delete
    Shotgun.schema_read
    Shotgun.schema
    Shotgun.entity_types


Connection & Authentication
===========================

These methods are used for connecting and authenticating with your Flow Production Tracking server. Most of
this is done automatically when you instantiate your instance. But if you need finer-grain
control, these methods are available.

.. automethod:: Shotgun.connect
.. automethod:: Shotgun.close
.. automethod:: Shotgun.authenticate_human_user
.. automethod:: Shotgun.get_session_token
.. automethod:: Shotgun.set_up_auth_cookie
.. automethod:: Shotgun.add_user_agent
.. automethod:: Shotgun.reset_user_agent
.. automethod:: Shotgun.set_session_uuid
.. automethod:: Shotgun.info

Subscription Management
=======================

These methods are used for reading and assigning user subscriptions.

.. automethod:: Shotgun.user_subscriptions_read
.. automethod:: Shotgun.user_subscriptions_create

CRUD Methods
============

These are the main methods for creating, reading, updating, and deleting information. There are
also some specialized convenience methods for accessing particular types of information.

.. automethod:: Shotgun.create
.. automethod:: Shotgun.find
.. automethod:: Shotgun.find_one
.. automethod:: Shotgun.update
.. automethod:: Shotgun.delete
.. automethod:: Shotgun.revive
.. automethod:: Shotgun.batch
.. automethod:: Shotgun.summarize
.. automethod:: Shotgun.note_thread_read
.. automethod:: Shotgun.text_search
.. automethod:: Shotgun.update_project_last_accessed
.. automethod:: Shotgun.work_schedule_read
.. automethod:: Shotgun.work_schedule_update
.. automethod:: Shotgun.preferences_read

Working With Files
==================

Methods that handle uploading and downloading files including thumbnails.

.. seealso:: :ref:`attachments`

.. automethod:: Shotgun.upload
.. automethod:: Shotgun.upload_thumbnail
.. automethod:: Shotgun.upload_filmstrip_thumbnail
.. automethod:: Shotgun.download_attachment
.. automethod:: Shotgun.get_attachment_download_url
.. automethod:: Shotgun.share_thumbnail

Activity Stream
===============

Methods that relate to the activity stream and following of entities in Flow Production Tracking.

.. automethod:: Shotgun.activity_stream_read
.. automethod:: Shotgun.follow
.. automethod:: Shotgun.unfollow
.. automethod:: Shotgun.followers
.. automethod:: Shotgun.following

Working with the Shotgun Schema
===============================

Methods allow you to introspect and modify the Shotgun schema.

.. automethod:: Shotgun.schema_entity_read
.. automethod:: Shotgun.schema_field_read
.. automethod:: Shotgun.schema_field_create
.. automethod:: Shotgun.schema_field_update
.. automethod:: Shotgun.schema_field_delete
.. automethod:: Shotgun.schema_read
.. automethod:: Shotgun.schema
.. automethod:: Shotgun.entity_types

**********
Exceptions
**********

These are the various exceptions that the Flow Production Tracking API will raise.

.. autoclass:: shotgun_api3.ShotgunError
    :show-inheritance:
    :inherited-members:
    :members:

.. autoclass:: shotgun_api3.ShotgunFileDownloadError
    :show-inheritance:
    :inherited-members:
    :members:

.. autoclass:: shotgun_api3.Fault
    :show-inheritance:
    :inherited-members:
    :members:

.. autoclass:: shotgun_api3.AuthenticationFault
    :show-inheritance:
    :inherited-members:
    :members:

.. autoclass:: shotgun_api3.MissingTwoFactorAuthenticationFault
    :show-inheritance:
    :inherited-members:
    :members:


.. _filter_syntax:

*************
Filter Syntax
*************

Basic Filters
=============

Filters are represented as a list of conditions that will be combined using the supplied
filter_operator (``any`` or ``all``). Each condition follows the basic simple form::

    [<field>, <relation>, <value(s)>]

Basic Example
-------------
Using the default filter_operator ``"all"``, the following filters will return all Shots whose status
is "ip" AND is linked to Asset #9::

    filters = [
        ["sg_status_list", "is", "ip"],
        ["assets", "is", {"type": "Asset", "id": 9}]
    ]
    result = sg.find("Shot", filters)


Complex Filters
===============

.. versionadded::3.0.11

Complex filters can be a dictionary that represents a complex sub-condition of the form::

    {"filter_operator": "any", "filters": [<list of conditions>]}

Complex Example
---------------
Using the default filter_operator ``"all"``, the following filters will return all Shots whose status
is "ip" AND is linked to either Asset #9 OR Asset #23::

    filters = [
        ["sg_status_list", "is", "ip"],
        {
            "filter_operator": "any",
            "filters": [
                ["assets", "is", {"type": "Asset", "id": 9}],
                ["assets", "is", {"type": "Asset", "id": 23}]
            ]
        }
    ]
    result = sg.find("Shot", filters)


Operators and Arguments
=======================

::

    Operator                    Arguments
    --------                    ---------
    'is'                        [field_value] | None
    'is_not'                    [field_value] | None
    'less_than'                 [field_value] | None
    'greater_than'              [field_value] | None
    'contains'                  [field_value] | None
    'not_contains'              [field_value] | None
    'starts_with'               [string]
    'ends_with'                 [string]
    'between'                   [[field_value] | None, [field_value] | None]
    'not_between'               [[field_value] | None, [field_value] | None]
    'in_last'                   [[int], 'HOUR' | 'DAY' | 'WEEK' | 'MONTH' | 'YEAR']
                                       # note that brackets are not literal (eg. ['start_date', 'in_last', 1, 'DAY'])
    'in_next'                   [[int], 'HOUR' | 'DAY' | 'WEEK' | 'MONTH' | 'YEAR']
                                       # note that brackets are not literal (eg. ['start_date', 'in_next', 1, 'DAY'])
    'in'                        [[field_value], ...]        # Array of field values
    'type_is'                   [string] | None             # Shotgun entity type
    'type_is_not'               [string] | None             # Shotgun entity type
    'in_calendar_day'           [int]                       # Offset (e.g. 0 = today, 1 = tomorrow,
                                                            # -1 = yesterday)
    'in_calendar_week'          [int]                       # Offset (e.g. 0 = this week, 1 = next week,
                                                            # -1 = last week)
    'in_calendar_month'         [int]                       # Offset (e.g. 0 = this month, 1 = next month,
                                                            # -1 = last month)
    'name_contains'             [string]
    'name_not_contains'         [string]
    'name_starts_with'          [string]
    'name_ends_with'            [string]


Valid Operators By Data Type
============================

::

    addressing                  'is'
                                'is_not'
                                'contains'
                                'not_contains'
                                'in'
                                'type_is'
                                'type_is_not'
                                'name_contains'
                                'name_not_contains'
                                'name_starts_with'
                                'name_ends_with'

    checkbox                    'is'
                                'is_not'

    currency                    'is'
                                'is_not'
                                'less_than'
                                'greater_than'
                                'between'
                                'not_between'
                                'in'
                                'not_in'

    date                        'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'in_last'
                                'not_in_last'
                                'in_next'
                                'not_in_next'
                                'in_calendar_day'
                                'in_calendar_week'
                                'in_calendar_month'
                                'in_calendar_year'
                                'between'
                                'in'
                                'not_in'

    date_time                   'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'in_last'
                                'not_in_last'
                                'in_next'
                                'not_in_next'
                                'in_calendar_day'
                                'in_calendar_week'
                                'in_calendar_month'
                                'in_calendar_year'
                                'between'
                                'in'
                                'not_in'

    duration                    'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'between'
                                'in'
                                'not_in'

    entity                      'is'
                                'is_not'
                                'type_is'
                                'type_is_not'
                                'name_contains'
                                'name_not_contains'
                                'name_is'
                                'in'
                                'not_in'

    float                       'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'between'
                                'in'
                                'not_in'

    image                       'is' ** Note: For both 'is' and 'is_not', the only supported value is None,
                                'is_not' **  which supports detecting the presence or lack of a thumbnail.

    list                        'is'
                                'is_not'
                                'in'
                                'not_in'

    multi_entity                'is' ** Note:  when used on multi_entity, this functions as
                                                you would expect 'contains' to function
                                'is_not'
                                'type_is'
                                'type_is_not'
                                'name_contains'
                                'name_not_contains'
                                'in'
                                'not_in'

    number                      'is'
                                'is_not'
                                'less_than'
                                'greater_than'
                                'between'
                                'not_between'
                                'in'
                                'not_in'

    password                    ** Filtering by this data type field not supported

    percent                     'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'between'
                                'in'
                                'not_in'

    serializable                ** Filtering by this data type field not supported

    status_list                 'is'
                                'is_not'
                                'in'
                                'not_in'

    summary                     ** Filtering by this data type field not supported


    tag_list                    'is'  ** Note:  when used on tag_list, this functions as
                                                you would expect 'contains' to function
                                'is_not'
                                'name_contains'
                                'name_not_contains'
                                'name_id'

    text                        'is'
                                'is_not'
                                'contains'
                                'not_contains'
                                'starts_with'
                                'ends_with'
                                'in'
                                'not_in'


    timecode                    'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'between'
                                'in'
                                'not_in'

    url                         ** Filtering by this data type field is not supported


.. _additional_filter_presets:

Additional Filter Presets
=========================

As of Flow Production Tracking version 7.0 it is possible to also use filter presets. These presets provide a simple
way to specify powerful query filters that would otherwise be costly and difficult to craft using 
traditional filters.

Multiple presets can be specified in cases where it makes sense.

Also, these presets can be used alongside normal filters. The result returned is an AND operation 
between the specified filters.

Example Uses
------------

The following query will return the Version with the name 'ABC' that is linked to the latest entity 
created::

    additional_filter_presets = [
        {
            "preset_name": "LATEST",
            "latest_by":   "ENTITIES_CREATED_AT"
        }
    ]

    filters = [['code', 'is', 'ABC']]

    result = sg.find('Version', filters = filters, additional_filter_presets = additional_filter_presets)


The following query will find all CutItems associated to Cut #1 and return all Versions associated 
to the Shot linked to each of these CutItems::

    additional_filter_presets = [
        {
            "preset_name": "CUT_SHOT_VERSIONS",
            "cut_id":       1
        }
    ]

    result = sg.find('Version', additional_filter_presets = additional_filter_presets)

Available Filter Presets by Entity Type
---------------------------------------

Allowed filter presets (and preset parameter values) depend on the entity type being searched.

The table bellow gives the details about which filter preset can be used on each entity type and 
with which parameters.

::

    Entity Type Preset Name       Preset Parameters   Allowed Preset Parameter Values
    ----------- -----------       -----------------   -------------------------------
    Cut         LATEST            [string] latest_by  'REVISION_NUMBER':
                                                        Returns the cuts that have the
                                                        highest revision number.
                                                        This is typically used with a query
                                                        filter that returns cuts with the
                                                        same value for a given field
                                                        (e.g. code field). This preset
                                                        therefore allows to get
                                                        the Cut of that set that has
                                                        the highest revision_number value.

    Version     CUT_SHOT_VERSIONS [int] cut_id        Valid Cut entity id.
                                                        Returns all Version entities
                                                        associated to the Shot entity
                                                        associated to the CutItems
                                                        of the given Cut.
                                                        This basically allows to find all
                                                        Versions associated to the given
                                                        Cut, via its CutItems.

                LATEST            [string] latest_by  'ENTITIES_CREATED_AT':
                                                        When dealing with multiple
                                                        Versions associated to a group
                                                        of entities, this will return
                                                        only the last Version created
                                                        for each entity.
                                                        For example, when dealing with a
                                                        set of Shots, this preset allows
                                                        to find the latest Version created
                                                        for each of these Shots.

                                                      'BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT':
                                                        When dealing with multiple versions
                                                        associated to the same entity *and*
                                                        to Tasks, returns the Version
                                                        associated to the Task with highest
                                                        step.list_order.
                                                        If multiple Versions are found for
                                                        that step.list_order, only the
                                                        latest Version is returned.
                                                        This allows to isolate the Version
                                                        entity that is the farthest along
                                                        in the pipeline for a given entity.
                                                        For example, when dealing with a Shot
                                                        with multiple Versions, this preset
                                                        will return the Version associated
                                                        to the Task with the highest
                                                        step.list_order value.
    Published   LATEST            [string] latest_by  'ENTITIES_CREATED_AT':
    Files                                               When dealing with multiple
                                                        PublishedFiles associated to a
                                                        group of entities, this will return
                                                        only the last PublishedFiles created
                                                        for each entity.
                                                        For example, when dealing with a
                                                        set of Versions, this preset allows
                                                        you to find the latest PublishedFile
                                                        created for each of these Versions.

                                                      'VERSION_NUMBER':
                                                        When dealing with multiple
                                                        PublishedFiles associated with a
                                                        group of entities, this returns only
                                                        the PublishedFile with the highest
                                                        version_number.

.. _data_types:

**********
Data Types
**********

addressing
==========

:value: :obj:`list`

List of dicts::

    [
      {
        'type': 'HumanUser' | 'Group',
        'id': int,
        ...
      },
      ...
    ]

checkbox
========

:value: :obj:`bool` (``True`` | ``False``)

color
=====

:value: :obj:`str`
:example: ``255,0,0`` | ``pipeline_step``

``pipeline_step`` indicates the Task color inherits from the Pipeline Step color.

currency
========

:value: :obj:`float` | :obj:`None`
:range: ``-9999999999999.99``, ``9999999999999.99``

date
====

:value: :obj:`str` | :obj:`None`
:range: Year must be >= 1970
:example: ``YYYY-MM-DD``

date_time
=========

:value: :mod:`datetime` | :obj:`None`
:range: Year must be >= 1970

    .. note::
        Datetimes are stored as UTC on the server. The Flow Production Tracking API is configured to automatically
        convert between client local time and UTC. This can be overridden.

duration
========

:value: :obj:`int` | :obj:`None`
:range: ``-2147483648``, ``2147483647``

Length of time, in minutes

entity
======

:value: :obj:`dict` | :obj:`None`

::

    {
      'type': "string",
      'id': int,
      ...
    }

float
=====

:value: :obj:`float` | :obj:`None`
:range: ``-999999999.999999``, ``999999999.999999``

footage
=======

:value: :obj:`str` | :obj:`None` ``FF-ff``
:range: Frames must be < Preferences value for "Advanced > Number of frames per foot of film"

    .. note::
        Format matches Preference value for "Formatting > Display of footage fields".
        Example above is default.F=Feet f=Frames.

image (read-only)
=================

:value: :obj:`str` | :obj:`None`

    .. note::
	   Refer to :ref:`interpreting_image_field_strings`.

list
====

:value: :obj:`str` | :obj:`None`

multi_entity
============

:value: :obj:`list`

List of dicts

::

    [
      {
        'type': "string",
        'id': int,
        ...
      },
      ...
    ]

number
======

:value: :obj:`int` | ``None``
:range: ``-2147483648``, ``2147483647``

password
========

:value: :obj:`string` | ``None``

Returned values of password fields are replaced with ``*******`` for security

percent
=======

:value: :obj:`int` | ``None``
:range: ``-2147483648``, ``2147483647``

serializable
============

:value: :obj:`dict` | ``None``

status_list
===========

:value: :obj:`str` | ``None``

system_task_type (deprecated)
=============================

:value: :obj:`str` | ``None``

tag_list
========

:value: :obj:`list`

text
====

:value: :obj:`str` | ``None``

timecode
========

:value: :obj:`int` | ``None``
:range: ``-2147483648``, ``2147483647``

Length of time, in milliseconds (1000 = 1 second)

url (file/link field)
=====================

:value: :obj:`dict` | ``None``

::

    {
      'content_type': "string",
      'link_type': "local" | "url" | "upload",
      'name': "string",
      'url': "string"
    }

Local File Links
----------------

Additional keys exist for local file links

:value: :obj:`dict` | ``None``

::

    {
      'content_type': "string",
      'link_type': "local",
      'local_path': "string" | None,
      'local_path_linux': "string" | None,
      'local_path_mac': "string" | None,
      'local_path_windows': "string" | None,
      'local_storage': {dictionary},
      'name': "string",
      'url': "string",
    }
    API versions < v3.0.3:

    {
      'url': "string",
      'name': "string",
      'content_type': "string"
    }

.. _interpreting_image_field_strings:

********************************
Interpreting Image Field Strings
********************************

There are three possible states for values returned by an ``image`` field:

.. list-table::
   :header-rows: 1

   * - Type
     - Value - Description
   * - :obj:`None`
     - No thumbnail image uploaded, or thumbnail generation failed.
   * - :obj:`str`
     - | ``<protocol>://<domain>/images/status/transient/thumbnail_pending.png`` -
       | URLs of this form indicate a transient placeholder icon.
       | Returned if image requested between upload & availability from media storage.
       | Constant string per site.
   * - :obj:`str`
     - | ``<signed URL for S3 object>`` -
       | Access to final thumbnail.

.. note::
    Other upcoming features are likely to require the use of other transient thumbnails.
    For this reason, it is highly recommended to use the prefix part of the placeholder path
    (e.g. https://my-site.shotgrid.autodesk.com/images/status/transient/)
    to detect any transient URLs rather than use the full path of the thumbnail.

.. _event_types:

***********
Event Types
***********

Whenever a user makes a change to any data in Flow Production Tracking, an event log entry record is created,
capturing the value before and after. Flow Production Tracking also logs some additional useful events that help keep
track of various activity on your Flow Production Tracking instance.

Event-based Triggers
====================

Events are particularlly useful when used in conjunction with a trigger framework like the
`Flow Production Tracking Event Daemon <https://github.com/shotgunsoftware/shotgunEvents>`_. This allows you to
write plug-ins that watch for certain types of events and then run code when they occur.
   
Structure of Event Types
========================

The basic structure of event types is broken into 3 parts:

``Application_EntityType_Action``

- ``Application``: Is always "Shotgun" for events automatically created by the Flow Production Tracking server.
  Other Flow Production Tracking products may use their name in here, for example, Toolkit has its own events
  that it logs and the application portion is identified by "Toolkit". If you decide to use the 
  EventLogEntry entity to log events for your scripts or tools, you would use your tool name here.
- ``EntityType``: This is the entity type in Flow Production Tracking that was acted upon (eg. Shot, Asset, etc.)
- ``Action``: The general action that was taken. (eg. New, Change, Retirement, Revival)   
   

Standard Event Types
====================

Each entity type has a standard set of events associated with it when it's created, updated, 
deleted, and revived. They follow this pattern:

- ``Shotgun_EntityType_New``: a new entity was created. Example: ``Shotgun_Task_New``
- ``Shotgun_EntityType_Change``: an entity was modified. Example: ``Shotgun_HumanUser_Change``
- ``Shotgun_EntityType_Retirement``: an entity was deleted. Example: ``Shotgun_Ticket_Retirement``
- ``Shotgun_EntityType_Revival``: an entity was revived. Example: ``Shotgun_CustomEntity03_Revival``   

Additional Event Types
======================

These are _some_ of the additional event types that are logged by Flow Production Tracking:
 
- ``Shotgun_Attachment_View``: an Attachment (file) was viewed by a user.
- ``Shotgun_Reading_Change``: a threaded entity has been marked read or unread. For example, a 
  Note was read by a user. The readings are unique to the entity<->user connection so when a 
  Note is read by user "joe" it may still be unread by user "jane".
- ``Shotgun_User_Login``: a user logged in to Flow Production Tracking.
- ``Shotgun_User_Logout``: a user logged out of Flow Production Tracking.
   

Custom Event Types
==================

Since ``EventLogEntries`` are entities themselves, you can create them using the API just like any 
other entity type. As mentioned previously, if you'd like to have your scripts or tools log to 
the Flow Production Tracking event log, simply devise a thoughtful naming structure for your event types and
create the EventLogEntry as needed following the usual methods for creating entities via the API.

Again, other Flow Production Tracking products like Toolkit use event logs this way.

.. note:: 
    EventLogEntries cannot be updated or deleted (that would defeat the purpose of course).   
   
Performance
===========

Event log database tables can get large very quickly. While Flow Production Tracking does very well with event logs
that get into the millions of records, there's an inevitable degradation of performance for pages 
that display them in the web application as well as any API queries for events when they get too 
big. This volume of events is not the norm, but can be reached if your server expereinces high 
usage. 

This **does not** mean your Flow Production Tracking server performance will suffer in general, just any pages that
are specifically displaying EventLogEntries in the web application, or API queries on the event
log that are run. We are always looking for ways to improve this in the future. If you have any
immediate concerns, please `reach out to our support team <https://www.autodesk.com/support/contact-support>`_

*********************
Environment Variables
*********************

SHOTGUN_API_CACERTS
===================

Used to specify a path to an external SSL certificates file.  This environment variable can be used in place of the ``ca_certs`` keyword argument to the :class:`~shotgun.Shotgun` constructor.  In the case that both this environment variable is set and the keyword argument is provided, the value from the keyword argument will be used.


SHOTGUN_API_RETRY_INTERVAL
==========================

Stores the number of milliseconds to wait between request retries.  By default, a value of 3000 milliseconds is used. You can override the default either by setting this environment variable, or by setting the ``rpc_attempt_interval`` property on the config like so: ::

    sg = Shotgun(site_name, script_name, script_key)
    sg.config.rpc_attempt_interval = 1000 # adjusting default interval

In the case that both this environment variable and the config's ``rpc_attempt_interval`` property are set, the value in ``rpc_attempt_interal`` will be used.

************
Localization
************

The Flow Production Tracking API offers the ability to return localized display names in the current user's language.
Requests made from script/API users are localized in the site settings.

This functionality is currently supported by the methods ``Shotgun.schema_entity_read``, ``Shotgun.schema_field_read``, and ``Shotgun.schema_read``.

Localization is disabled by default. To enable localization, set the ``localized`` property to ``True``.

Example for a user whose language preference is set to Japanese:

.. code-block:: python
   :emphasize-lines: 9,20

    >>> sg = Shotgun(site_name, script_name, script_key)
    >>> sg.config.localized # checking that localization is disabled
    False
    >>> sg.schema_field_read('Shot')
    {
    'sg_vendor_groups': {
        'mandatory': {'editable': False, 'value': False},
        # the value field (display name) is not localized
        'name': {'editable': True, 'value': 'Vendor Groups'},
        ...
    },
    ...
    }
    >>> sg.config.localized = True # enabling the localization
    >>> sg.schema_field_read('Shot')
    {
    'sg_vendor_groups': {
        'mandatory': {'editable': False, 'value': False},
        # the value field (display name) is localized
        'name': {'editable': True, 'value': '\xe3\x83\x99\xe3\x83\xb3\xe3\x83\x80\xe3\x83\xbc \xe3\x82\xb0\xe3\x83\xab\xe3\x83\xbc\xe3\x83\x97'},
        ...
    },
    ...
    }

.. note::
    If needed, the encoding of the returned localized string can be ensured regardless the Python version using shotgun_api3.lib.six.ensure_text().
