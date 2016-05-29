###################
Shotgun Python API3
###################
Release |version|. (:ref:`Installation <installation>`)

.. image:: https://img.shields.io/badge/shotgun-api-blue.svg?style=flat-square
.. image:: https://img.shields.io/travis/shotgunsoftware/python-api.svg?style=flat-square



Shotgun provides a simple Python-based API for accessing Shotgun and integrating with other tools.
The Shotgun API allows users to integrate their tools with Shotgun very easily. Using this simple
but powerful python module , you can quickly get your scripts integrated with Shotgun's CRUD-based
API.

Because the needs of every studio can prove to be very different, we don't include a lot of
"automation" or "smarts" in our API. We have kept it pretty low-level and leave most of those
decisions to you. The API is powerful enough you can write your own "smarts" in a wrapper on top
of the Shotgun API.

In addition to basic metadata, the API contains methods for managing media including thumbnails,
filmstrip thumbnails, images, uploaded, and both locally and remotely linked media like
Quicktimes, etc.

**Example**::

    sg = shotgun_api3.Shotgun("https://piedpiper.shotgunstudio.com",
                              login="rhendriks",
                              password="c0mPre$Hi0n")
    sg.find("Shot", filters=[["sg_status_list", "is", "ip"]], fields=["code", "sg_status_list])

**Output**::

    [{'code': 'bunny_020_0170',
      'id': 896,
      'sg_sequence': {'id': 5, 'name': 'bunny_020', 'type': 'Sequence'},
      'sg_status_list': 'ip',
      'type': 'Shot'},
     {'code': 'bunny_020_0200',
      'id': 899,
      'sg_sequence': {'id': 5, 'name': 'bunny_020', 'type': 'Sequence'},
      'sg_status_list': 'ip',
      'type': 'Shot'},
     {'code': 'bunny_030_0080',
      'id': 907,
      'sg_sequence': {'id': 6, 'name': 'bunny_030', 'type': 'Sequence'},
      'sg_status_list': 'ip',
      'type': 'Shot'}]


**********
User Guide
**********
.. toctree::
    :maxdepth: 2

    installation
    authentication
    usage_tips
    tutorials

*******************
Developer Reference
*******************
.. toctree::
    :maxdepth: 2

    reference
    filter_syntax
    data_types
    attachments
    local_files
    packaging
    server_changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

