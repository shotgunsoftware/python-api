.. _example_create_shot:

Create A Shot
=============

Building the data and calling :meth:`~shotgun_api3.Shotgun.create`
------------------------------------------------------------------
To create a Shot, you need to provide the following values:

- ``project`` is a link to the Project the Shot belongs to. It should be a dictionary like
  ``{"type": "Project", "id": 123}`` where ``id`` is the ``id`` of the Project.
- ``code`` (this is the field that stores the name Shot)
- optionally any other info you want to provide

Example::

    data = {
        'project': {"type":"Project","id": 4},
        'code': '100_010',
        'description': 'Open on a beautiful field with fuzzy bunnies',
        'sg_status_list': 'ip'
    }
    result = sg.create('Shot', data)


This will create a new Shot named "100_010" in the Project "Gunslinger" (which has an ``id`` of 4).

- ``data`` is a list of key/value pairs where the key is the column name to update and the value
  is the the value to set.
- ``sg`` is the Flow Production Tracking API instance you created in :ref:`example_sg_instance`.
- ``create()`` is the :meth:`shotgun_api3.Shotgun.create` API method we are calling. We pass in the
  entity type we're searching for and the data we're setting.

.. rubric:: Result

The variable ``result`` now contains a dictionary hash with the Shot information you created.::

    {
        'code': '100_010',
        'description': 'Open on a beautiful field with fuzzy bunnies',
        'id': 40435,
        'project': {'id': 4, 'name': 'Demo Project', 'type': 'Project'},
        'sg_status_list': 'ip',
        'type': 'Shot'
    }

In addition, Flow Production Tracking has returned the ``id`` that it has assigned to the Shot, as well as a
``type`` value. ``type`` is provided for convenience simply to help you identify what entity type
this dictionary represents. It does not correspond to any field in Flow Production Tracking.

Flow Production Tracking will *always* return the ``id`` and ``type`` keys in the dictionary when there are results
representing an entity.

The Complete Example
--------------------
::

    #!/usr/bin/env python

    # --------------------------------------
    # Imports
    # --------------------------------------
    import shotgun_api3
    from pprint import pprint # useful for debugging

    # --------------------------------------
    # Globals
    # --------------------------------------
    # make sure to change this to match your Flow Production Tracking server and auth credentials.
    SERVER_PATH = "https://my-site.shotgrid.autodesk.com"
    SCRIPT_NAME = 'my_script'
    SCRIPT_KEY = '27b65d7063f46b82e670fe807bd2b6f3fd1676c1'

    # --------------------------------------
    # Main
    # --------------------------------------
    if __name__ == '__main__':

        sg = shotgun_api3.Shotgun(SERVER_PATH, SCRIPT_NAME, SCRIPT_KEY)

        # --------------------------------------
        # Create a Shot with data
        # --------------------------------------
        data = {
            'project': {"type":"Project","id": 4},
            'code': '100_010',
            'description': 'Open on a beautiful field with fuzzy bunnies',
            'sg_status_list': 'ip'
        }
        result = sg.create('Shot', data)
        pprint(result)
        print("The id of the {} is {}.".format(result['type'], result['id']))

And here is the output::

    {'code': '100_010',
     'description': 'Open on a beautiful field with fuzzy bunnies',
     'id': 40435,
     'project': {'id': 4, 'name': 'Demo Project', 'type': 'Project'},
     'sg_status_list': 'ip',
     'type': 'Shot'}
    The id of the Shot is 40435.
