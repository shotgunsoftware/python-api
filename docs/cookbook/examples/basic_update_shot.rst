Update A Shot
=============

Building the data and calling :meth:`~shotgun_api3.Shotgun.update`
------------------------------------------------------------------
To update a Shot, you need to provide the ``id`` of the Shot and a list of fields you want to
update.::

    data = {
        'description': 'Open on a beautiful field with fuzzy bunnies',
        'sg_status_list': 'ip'
        }
    result = sg.update('Shot', 40435, data)

This will update the ``description`` and the ``sg_status_list`` fields for the Shot with ``id`` of
**40435**.

- ``data`` is a list of key/value pairs where the key is the field name to update and the value to
  update it to.
- ``sg`` is the Flow Production Tracking API instance.
- ``update()`` is the :meth:`shotgun_api3.Shotgun.update` API method we are calling. We provide it
  with the entity type we're updating, the ``id`` of the entity, and the data we're updating it
  with.

Result
------
The variable ``result`` now contains the Shot object that with the updated values.::

    {
        'description': 'Opening establishing shot with titles and fuzzy bunnies',
        'sg_status_list': 'ip',
        'type': 'Shot',
        'id': 40435
    }

In addition, Flow Production Tracking has returned the ``id`` for the Shot, as well as a ``type`` value. ``type``
is provided for convenience simply to help you identify what entity type this dictionary represents.
It does not correspond to any field in Flow Production Tracking.

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
        # Update Shot with data
        # --------------------------------------
        data = {
            'description': 'Open on a beautiful field with fuzzy bunnies',
            'sg_status_list': 'ip'
            }
        result = sg.update('Shot', 40435, data)
        pprint(result)

And here is the output::

    {'description': 'Opening establishing shot with titles and fuzzy bunnies',
     'id': 40435,
     'sg_status_list': 'ip',
     'type': 'Shot'}
