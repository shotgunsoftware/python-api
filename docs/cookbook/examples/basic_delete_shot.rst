Delete A Shot
=============

Calling :meth:`~shotgun_api3.Shotgun.delete`
--------------------------------------------
Deleting an entity in Shotgun is pretty straight-forward. No extraneous steps required.::

    result = sg.delete("Shot", 40435) 

Result
------
If the Shot was deleted successfully ``result`` will contain::

    True

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
    # make sure to change this to match your Shotgun server and auth credentials.
    SERVER_PATH = "https://mystudio.shotgunstudio.com"
    SCRIPT_NAME = 'my_script'     
    SCRIPT_KEY = '27b65d7063f46b82e670fe807bd2b6f3fd1676c1'

    # --------------------------------------
    # Main 
    # --------------------------------------
    if __name__ == '__main__':    

        sg = shotgun_api3.Shotgun(SERVER_PATH, SCRIPT_NAME, SCRIPT_KEY)

        # --------------------------------------
        # Delete a Shot by id
        # --------------------------------------
        result = sg.delete("Shot", 40435)    
        pprint(result)

And here is the output::

    True

