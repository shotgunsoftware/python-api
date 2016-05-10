.. _local_files:

########################
Working With Local Files
########################

We added support for linking to local files in the UI in Shotgun Server v2.1. This doc covers how
to work with these local file links using the API.

************
Requirements
************

* Python API v3.0.3+
* Shotgun Server v2.1.10+

******************************
Structure of Local File Values
******************************

There is a key in the dictionary that represents file/link fields called ``link_type`` which can be
one of ``local``, ``upload``, ``web``. This is used to determine what type of link the field value
contains. For local files this value is always ``local`` and there are additional keys that
are available:

- **content_type** (:obj:`str`):
    The mime-type of the associated local file. This is assigned
    automatically using a best-guess based on the file extension. You can override this by setting
    this explicitly.

- **link_type** (:obj:`str`) *read-only*:
    Always 'local' for local files.

- **name** (:obj:`str`):
    the display name of the local file. This is set to the filename by
    default but can be overridden by setting this explicitly.

- **local_path** (:obj:`str`):
    The full path to the file on the current platform. The Python API tries to determine the
    platform it is currently running on and then copies the value from the corresponding key above
    to this field for convenience.

- **local_path_linux** (:obj:`str`) *read-only*:
    Full path to file on Linux as defined by the LocalStorage (or ``None`` if no Linux path is set)

- **local_path_mac** (:obj:`str`) *read-only*:
    Full path to file on Mac OS X as defined by the LocalStorage (or ``None`` if no Mac path is set)

- **local_path_windows** (:obj:`str`) *read-only*:
    Full path to file on Windows as defined by the LocalStorage (or ``None`` if no Windows path
    is set)

- **local_storage** (:obj:`dict`) *read-only*:
    A dictionary representing which LocalStorage entity is applied for this local file link.

- **url** (:obj:`str`) *read-only*:
    A file:// link provided for convenience pointing to the value in the ``local_path``

*************************
Reading Local File Fields
*************************

::

    fields = ['sg_uploaded_movie']
    result = sg.find('Version', [['id', 'is', 123]], fields)

Returns::

    {'id':123,
     'sg_uploaded_movie': { 'content_type': None,
                            'link_type': 'local',
                            'name': 'my_test_movie.mov',
                            'local_path': '/Users/kp/Movies/testing/test_movie_001_.mov'
                            'local_path_linux': '/home/users/macusers/kp/Movies/testing/test_movie_001_.mov'
                            'local_path_mac': '/Users/kp/Movies/testing/test_movie_001_.mov'
                            'local_path_windows': 'M:\\macusers\kp\Movies\testing\test_movie_001_.mov'
                            'local_storage': {'id': 1,
                                              'name': 'Dailies Directories',
                                              'type': 'LocalStorage'},
                            'url': 'file:///Users/kp/Movies/testing/test_movie_001_.mov'},
     'type': 'Version'}

.. note::
    When viewing results that include file/link fields with local file link values, all of the
    keys will be returned regardless of whether there are values in them. So in the above example,
    if there was no Windows path set for the local storage, ``local_path_windows`` would be
    ``None``.

.. _creating_local_files:

*************************************
Creating & Updating Local file Fields
*************************************
When setting a file/link field value to a local file, only the ``local_path`` is mandatory. Shotgun
will automatically select the appropriate matching local storage for your file based on the path.
You can optionally specify the ``name`` and ``content_type`` fields if you wish to override their
defaults. Any other keys that are provided will be ignored.

* **content_type** :obj:`str`:
    Optionally set the mime-type of the associated local file. This is assigned automatically
    using a best-guess based on the file extension.


* **name** :obj:`str`:
    Optional display name of the local file. This is set to the filename by default.

* **local_path** :obj:`str`:
    The full local path to the file. Shotgun will find the LocalStorage
    that has the most specific match to this path and automatically assign that LocalStorage to
    the file.

::

    data = {'sg_uploaded_movie': {'local_path': '/Users/kp/Movies/testing/test_movie_002.mov',
                                  'name': 'Better Movie'}
    result = sg.update('Version', 123, data)

Returns::

    {'id':123,
     'sg_uploaded_movie': { 'content_type': 'video/quicktime',
                            'link_type': 'local',
                            'name': 'my_test_movie.mov',
                            'local_path': '/Users/kp/Movies/testing/test_movie_002.mov'
                            'local_path_linux': '/home/users/macusers/kp/Movies/testing/test_movie_002.mov'
                            'local_path_mac': '/Users/kp/Movies/testing/test_movie_002.mov'
                            'local_path_windows': 'M:\\macusers\kp\Movies\testing\test_movie_002.mov'
                            'local_storage': {'id': 1,
                                              'name': 'Dailies Directories',
                                              'type': 'LocalStorage'},
                            'url': 'file:///Users/kp/Movies/testing/test_movie_002.mov'},
     'type': 'Version'}]

The ``content_type`` was assigned a best-guess value based on the file extension. Shotgun selected
the most appropriate specific LocalStorage match and assigned it to local_storage automatically.

**********************************
Un-setting local file field values
**********************************

Removing a a local file field value is simple. Just set the value to ``None``::

    data = {'sg_uploaded_movie': None}
    result = sg.update('Version', 123, data)

Returns::

    {'id':123,
     'sg_uploaded_movie': None,
     'type': 'Version'}]
