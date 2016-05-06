.. _data_types:

##########
Data Types
##########


**********
addressing
**********

:value: :func:`list`

List of dicts::

    [
      {
        'type': 'HumanUser' | 'Group',
        'id': int,
        ...
      },
      ...
    ]


********
checkbox
********

:value: :func:`bool` (``True`` | ``False``)

*****
color
*****

:value: :func:`str`
:example: ``255,0,0`` | ``pipeline_step``

``pipeline_step`` indicates the Task color inherits from the Pipeline Step color.

********
currency
********

:value: :func:`double` | :func:`None`
:range: ``-9999999999999.99``, ``9999999999999.99``

****
date
****

:value: :func:`str` | :func:`None`
:range: Year must be >= 1970
:example: ``YYYY-MM-DD``

*********
date_time
*********

:value: :mod:`datetime` | :func:`None`
:range: Year must be >= 1970

    .. note::
        Datetimes are stored as UTC on the server. The Shotgun API is configured to automatically
        convert between client local time and UTC. This can be overridden.

********
duration
********

:value: :func:`int` | :func:`None`
:range: ``-2147483648``, ``2147483647``

Length of time, in minutes

******
entity
******

:value: :func:`dict` | :func:`None`

::

    {
      'type': "string",
      'id': int,
      ...
    }

*****
float
*****

:value: :func:`double` | :func:`None`
:range: ``-999999999.999999``, ``999999999.999999``

*******
footage
*******

:value: :func:`str` | :func:`None` ``FF-ff``
:range: Frames must be < Preferences value for "Advanced > Number of frames per foot of film"

    .. note::
        Format matches Preference value for "Formatting > Display of footage fields".
        Example above is default.F=Feet f=Frames.

*****************
image (read-only)
*****************

:value: :func:`str` | :func:`None`

****
list
****

:value: :func:`str` | :func:`None`

************
multi_entity
************

:value: :func:`list`

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

******
number
******

:value: :func:`int` | ``None``
:range: ``-2147483648``, ``2147483647``

********
password
********

:value: :func:`string` | ``None``

Returned values of password fields are replaced with ``*******`` for security

*******
percent
*******

:value: :func:`int` | ``None``
:range: ``-2147483648``, ``2147483647``

************
serializable
************

:value: :func:`dict` | ``None``

***********
status_list
***********

:value: :func:`str` | ``None``

*****************************
system_task_type (deprecated)
*****************************

:value: :func:`str` | ``None``

********
tag_list
********

:value: :func:`list`

********
text
********

:value: :func:`str` | ``None``

********
timecode
********

:value: :func:`int` | ``None``
:range: ``-2147483648``, ``2147483647``

Length of time, in milliseconds (1000 = 1 second)

*********************
url (file/link field)
*********************

:value: :func:`dict` | ``None``

::

    {
      'content_type': "string",
      'link_type': "local" | "url" | "upload",
      'name': "string",
      'url': "string"
    }

Local Files
===========

Additional keys exist for local file links

:value: :func:`dict` | ``None``

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