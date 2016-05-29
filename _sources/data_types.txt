.. _data_types:

##########
Data Types
##########


**********
addressing
**********

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


********
checkbox
********

:value: :obj:`bool` (``True`` | ``False``)

*****
color
*****

:value: :obj:`str`
:example: ``255,0,0`` | ``pipeline_step``

``pipeline_step`` indicates the Task color inherits from the Pipeline Step color.

********
currency
********

:value: :obj:`float` | :obj:`None`
:range: ``-9999999999999.99``, ``9999999999999.99``

****
date
****

:value: :obj:`str` | :obj:`None`
:range: Year must be >= 1970
:example: ``YYYY-MM-DD``

*********
date_time
*********

:value: :mod:`datetime` | :obj:`None`
:range: Year must be >= 1970

    .. note::
        Datetimes are stored as UTC on the server. The Shotgun API is configured to automatically
        convert between client local time and UTC. This can be overridden.

********
duration
********

:value: :obj:`int` | :obj:`None`
:range: ``-2147483648``, ``2147483647``

Length of time, in minutes

******
entity
******

:value: :obj:`dict` | :obj:`None`

::

    {
      'type': "string",
      'id': int,
      ...
    }

*****
float
*****

:value: :obj:`float` | :obj:`None`
:range: ``-999999999.999999``, ``999999999.999999``

*******
footage
*******

:value: :obj:`str` | :obj:`None` ``FF-ff``
:range: Frames must be < Preferences value for "Advanced > Number of frames per foot of film"

    .. note::
        Format matches Preference value for "Formatting > Display of footage fields".
        Example above is default.F=Feet f=Frames.

*****************
image (read-only)
*****************

:value: :obj:`str` | :obj:`None`

****
list
****

:value: :obj:`str` | :obj:`None`

************
multi_entity
************

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

******
number
******

:value: :obj:`int` | ``None``
:range: ``-2147483648``, ``2147483647``

********
password
********

:value: :obj:`string` | ``None``

Returned values of password fields are replaced with ``*******`` for security

*******
percent
*******

:value: :obj:`int` | ``None``
:range: ``-2147483648``, ``2147483647``

************
serializable
************

:value: :obj:`dict` | ``None``

***********
status_list
***********

:value: :obj:`str` | ``None``

*****************************
system_task_type (deprecated)
*****************************

:value: :obj:`str` | ``None``

********
tag_list
********

:value: :obj:`list`

********
text
********

:value: :obj:`str` | ``None``

********
timecode
********

:value: :obj:`int` | ``None``
:range: ``-2147483648``, ``2147483647``

Length of time, in milliseconds (1000 = 1 second)

*********************
url (file/link field)
*********************

:value: :obj:`dict` | ``None``

::

    {
      'content_type': "string",
      'link_type': "local" | "url" | "upload",
      'name': "string",
      'url': "string"
    }

Local File Links
================

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