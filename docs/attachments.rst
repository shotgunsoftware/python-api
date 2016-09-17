.. _attachments:

##################
Working With Files
##################

The Shotgun web application stores Files as Attachment entities. You can see these on a Files page,
or a Files tab on a detail page, for example. You can access Attachments via the API to create and
modify uploaded files, url links, and local files, and link them to other entities (Shots,
Versions, etc). This entity works a lot like other entity types within Shotgun with a few
exceptions which are detailed below.

.. note::
    If you are simply looking for information about how to upload and link things in Shotgun, this
    doc is not for you. Instead look at the :meth:`~shotgun_api3.Shotgun.upload` and
    :meth:`~shotgun_api3.Shotgun.upload_thumbnail` methods.

    This doc describes the detailed structure of the Attachment entities that represent files
    in Shotgun and how to interact with them. If that sounds cool too, then read on!

.. versionadded:: 3.0.3
    Requires Shotgun Server v2.2.0+

*****************
Default structure
*****************
The following is a list of the default fields that Shotgun creates for Attachments. Your server
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
    The internal Shotgun id for this Attachment entity.

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
    The url location of the thumbnail image assigned to this Attachment. For uploads, Shotgun
    automatically tries to create a thumbnail from the file. Alternatively, you can assign your
    own thumbnail to an Attachment using the :meth:`~shotgun_api3.Shotgun.upload_thumbnail` method.

- **sg_type** (:obj:`str`):
    An optional field for designating different types of Attachments


File type structures (``this_file``)
====================================

Depending on the type of file the Attachment entity is representing, the value of ``this_file``
will vary.

- **Uploads**
    Designated by ``link_type: 'upload'``, this represents a file that was uploaded to Shotgun.
    Uploading files to Shotgun can be done using the :meth:`~shotgun_api3.Shotgun.upload` method.
    You cannot create an Attachment with an uploaded file directly.

    ::

      {'content_type': 'image/jpeg',
       'link_type': 'upload',
       'name': 'western1FULL.jpg',
       'url': 'https://superdeathcarracer.shotgunstudio.com/file_serve/attachment/538'}

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

Local Files
===========
See :ref:`creating_local_files`.

********************
Updating Attachments
********************
You cannot modify the ``this_file`` field after you create an Attachment. If you need to provide a
different file, you will have to create a new Attachment entity. Otherwise, the process for
updating Attachments is exactly like updating other entity types in Shotgun and is the same for all
Attachment types. See :meth:`~shotgun_api3.Shotgun.update` for more info.


********************
Deleting Attachments
********************
The process of deleting an Attachment is just like other entities in Shotgun. See
:meth:`~shotgun_api3.Shotgun.delete` for more info.
