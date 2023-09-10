.. _packaging:

################################################
Packaging an application with py2app (or py2exe)
################################################

You can create standalone applications with Python scripts by using
`py2app <https://pythonhosted.org/py2app/>`_ on OS X or `py2exe <http://www.py2exe.org/>`_ on
Windows. This is often done to more easily distribute applications that have a GUI based on 
toolkits like Tk, Qt or others.

There are caveats you need to be aware of when creating such an app.

********************************
HTTPS Validation and cacerts.txt
********************************
When creating the connection to ShotGrid a file is used to validate the ShotGrid certificate. This
file can be located with ``httplib2.BUILTIN_CA_CERTS``. Because this file is not a Python
file imported by your application, py2app will not know to include it in your package, it will
need to be explicitly specified in your ``setup.py`` file (edit the path based on the location
where your ``shotgun_api3`` package is located)::

    DATA_FILES = [
        ('shotgun_api3', [httplib2.BUILTIN_CA_CERTS])
    ]

Once you create your py2app package its contents should include two files (among others) in the
following structure::

    ./Contents/Resources/shotgun_api3/cacerts.txt
    ./Contents/Resources/my_script.py

Where in ``my_script.py`` you can access the ``cacerts.txt`` file using a relative path to pass it
into the ShotGrid connection's constructor::

    ca_certs = os.path.join(os.path.dirname(__file__), 'shotgun_api3', 'cacerts.txt')
    sg = shotgun_api3.Shotgun('https://my-site.shotgrid.autodesk.com', 'script_name', 'script_key',
                              ca_certs=ca_certs)

The process for py2exe should be similar.