.. _attachments:

################################
Details About Working With Files
################################

The Flow Production Tracking web application stores Files as Attachment entities. You can see these on a Files page,
or a Files tab on a detail page, for example. You can access Attachments via the API to create and
modify uploaded files, url links, and local files, and link them to other entities (Shots,
Versions, etc). This entity works a lot like other entity types within Flow Production Tracking with a few
exceptions which are detailed below.

.. note::
    If you are simply looking for information about how to upload and link things in Flow Production Tracking, this
    doc is not for you. Instead look at the :meth:`~shotgun_api3.Shotgun.upload` and
    :meth:`~shotgun_api3.Shotgun.upload_thumbnail` methods.

    This doc describes the detailed structure of the Attachment entities that represent files
    in Flow Production Tracking and how to interact with them. If that sounds cool too, then read on!

.. versionadded:: 3.0.3

*****************
Default structure
*****************
The following is a list of the default fields that Flow Production Tracking creates for Attachments. Your server
instance may look slightly different depending on your own customizations. Many of these fields are
optional and some are automatically filled in. These exceptions are listed below in the
descriptions of each field.

- **description** (:obj:`str`):
    Optional field to provide descriptive text about the file.

- **this_file** (:obj:`dict`):
     The actual file reference. Within the dictionary is a ``link_type`` key which designates the
     Attachment as an uploaded file, a url link, or a local file. There are additional keys
     returned for :ref:`local_files`. You cannot modify this field after you have created an
     Attachment. See below for examples of this field.

- **filename** (:obj:`str`):
    For uploaded files only. This is automatically assigned when the file is uploaded and stores
    the filename of the file.

- **file_size** (:obj:`int`):
    For uploaded files only. This is automatically assigned when the file is uploaded and stores
    the size of the file in bytes.

- **id** (:obj:`int`):
    The internal Flow Production Tracking id for this Attachment entity.

- **attachment_links** (:obj:`list`):
    A list of entity dictionaries used for linking Attachments to multiple entities.

- **open_notes** (:obj:`list`):
    A List of Note entities linked to the current Attachment that have a status that does not
    equal 'clsd'. *Read-only*

- **open_notes_count** (:obj:`int`):
    An integer count of the list of Note entities linked to the current Attachment that have a
    status that does not equal 'clsd'. *(Read-only)*

- **project** (:obj:`dict`):
    *(Required)* The Project entity that this Attachment belongs to. This must be assigned when
    creating an Attachment.

- **attachment_reference_links** (:obj:`list`):
    Similar to ``attachment_links`` but used specifically for linking files to multiple entities as
    reference.

- **sg_status_list** (:obj:`str`):
    Status value returned as the short code.

- **tag_list** (:obj:`list`):
    List of tags (as strings) that are currently assigned to the Attachment.

- **image** (:obj:`str`):
    The url location of the thumbnail image assigned to this Attachment. For uploads, Flow Production Tracking
    automatically tries to create a thumbnail from the file.
    See :ref:`interpreting_image_field_strings`. Alternatively, you can assign your
    own thumbnail to an Attachment using the :meth:`~shotgun_api3.Shotgun.upload_thumbnail` method.

- **sg_type** (:obj:`str`):
    An optional field for designating different types of Attachments

- **processing_status** (:obj:`str`):
    Reflects the status of the attachment (File entity).
    When processing the thumbnail, this field is set to ‘Thumbnail Pending’.


File type structures (``this_file``)
====================================

Depending on the type of file the Attachment entity is representing, the value of ``this_file``
will vary.

- **Uploads**
    Designated by ``link_type: 'upload'``, this represents a file that was uploaded to Flow Production Tracking.
    Uploading files to Flow Production Tracking can be done using the :meth:`~shotgun_api3.Shotgun.upload` method.
    You cannot create an Attachment with an uploaded file directly.

    ::

      {'content_type': 'image/jpeg',
       'link_type': 'upload',
       'name': 'western1FULL.jpg',
       'url': 'https://my-site.shotgrid.autodesk.com/file_serve/attachment/538'}

- **Web links**
    Designated by ``link_type: 'web'``, this is represents a url link. Examples include an
    ``http://`` link to another server or a custom protocol used to launch a local application
    like ``rvlink://`` or ``cinesync://``
    ::

      {'content_type': None,
       'link_type': 'web',
       'name': 'Join GUN12158',
       'url': 'cinesync://session/GUN12158'}

- **Local Files**
    Designated by ``link_type: 'local'``, this is represents a local file link. Additional keys
    are provided in order to give access to the relative path information on other platforms.

    .. seealso:: :ref:`local_files`

    ::

      { 'content_type': 'video/quicktime',
        'link_type': 'local',
        'name': 'my_test_movie.mov',
        'local_path': '/Users/kp/Movies/testing/test_movie_002.mov'
        'local_path_linux': '/home/users/macusers/kp/Movies/testing/test_movie_002.mov'
        'local_path_mac': '/Users/kp/Movies/testing/test_movie_002.mov'
        'local_path_windows': 'M:\\macusers\kp\Movies\testing\test_movie_002.mov'
        'local_storage': {'id': 1,
                          'name': 'Dailies Directories',
                          'type': 'LocalStorage'},
        'url': 'file:///Users/kp/Movies/testing/test_movie_002.mov'}


********************
Creating Attachments
********************

Web Links
=========
::

    myurl = {
      'url': 'http://apple.com/itunes',
      'name': 'Apple: iTunes'
    }
    data = {
        'this_file': myurl,
        'project': {'type':'Project','id':64}
    }
    result = sg.create('Attachment', data)


Uploads
=======
Uploads cannot be created directly on Attachments. Instead, you need to use the
:meth:`~shotgun_api3.Shotgun.upload` method.

Make sure to have retries for file uploads. Failures when uploading will occasionally happen. When
it does, immediately retrying to upload usually works.


Local Files
===========
See :ref:`creating_local_files`.

********************
Updating Attachments
********************
You cannot modify the ``this_file`` field after you create an Attachment. If you need to provide a
different file, you will have to create a new Attachment entity. Otherwise, the process for
updating Attachments is exactly like updating other entity types in Flow Production Tracking and is the same for all
Attachment types. See :meth:`~shotgun_api3.Shotgun.update` for more info.


********************
Deleting Attachments
********************
The process of deleting an Attachment is just like other entities in Flow Production Tracking. See
:meth:`~shotgun_api3.Shotgun.delete` for more info.

.. _local_files:

*****************************
Working With Local File Types
*****************************

We added support for linking to local files in the UI in Flow Production Tracking Server v2.1. This doc covers how
to work with these local file links using the API.

Requirements
============

- Python API v3.0.3+
- Flow Production Tracking Server v2.1.10+

Structure of Local File Values
==============================

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

Reading Local File Fields
=========================

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

Creating & Updating Local file Fields
=====================================

When setting a file/link field value to a local file, only the ``local_path`` is mandatory. Flow Production Tracking
will automatically select the appropriate matching local storage for your file based on the path.
You can optionally specify the ``name`` and ``content_type`` fields if you wish to override their
defaults. Any other keys that are provided will be ignored.

* **content_type** :obj:`str`:
    Optionally set the mime-type of the associated local file. This is assigned automatically
    using a best-guess based on the file extension.


* **name** :obj:`str`:
    Optional display name of the local file. This is set to the filename by default.

* **local_path** :obj:`str`:
    The full local path to the file. Flow Production Tracking will find the LocalStorage
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

The ``content_type`` was assigned a best-guess value based on the file extension. Flow Production Tracking selected
the most appropriate specific LocalStorage match and assigned it to local_storage automatically.

Un-setting local file field values
==================================

Removing a a local file field value is simple. Just set the value to ``None``::

    data = {'sg_uploaded_movie': None}
    result = sg.update('Version', 123, data)

Returns::

    {'id':123,
     'sg_uploaded_movie': None,
     'type': 'Version'}]
