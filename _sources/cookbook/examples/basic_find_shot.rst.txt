.. _example_find_shot:

Find a Shot
===========

Building the Query
------------------
We are going to assume we know the 'id' of the Shot we're looking for in this example.::

    filters = [['id', 'is', 40435]]
    result = sg.find_one('Shot', filters)

Pretty simple right? Well here's a little more insight into what's going on.

- ``filters`` is an list of filter conditions. In this example we are filtering for Shots where
  the ``id`` column is **40435**.
- ``sg`` is the Flow Production Tracking API instance.
- ``find_one()`` is the :meth:`~shotgun_api3.Shotgun.find_one` API method we are calling. We
  provide it with the entity type we're searching for and our filters.


Seeing the Result
-----------------
So what does this return? The variable result now contains::

    {'type': 'Shot','id': 40435}

By default, :meth:`~shotgun_api3.Shotgun.find_one` returns a single dictionary object with
the ``type`` and ``id`` fields. So in this example, we found a Shot matching that id, and Flow Production Tracking
returned it as a dictionary object with ``type`` and ``id`` keys .

How do we know that result contains the Shot dictionary object? You can trust us... but just to be
sure, the :mod:`pprint` (PrettyPrint) module from the Python standard library is a really good tool
to help with debugging. It will print out objects in a nicely formatted way that makes things
easier to read. So we'll add that to the import section of our script.::

    import shotgun_api3
    from pprint import pprint # useful for debugging

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
        # Find a Shot by id
        # --------------------------------------
        filters = [['id', 'is', 40435]]
        result = sg.find_one('Shot', filters)
        pprint(result)

And here is the output::

    {'type': 'Shot','id': 40435}
