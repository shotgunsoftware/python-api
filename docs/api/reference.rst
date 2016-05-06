.. _apireference:

#############
API Reference
#############

*************************
shotgun Module attributes
*************************

The :mod:`shotgun_api3.shotgun` module is a container for the :class:`~shotgun_api3.Shotgun` 
class. There are a couple of useful attributes to note.

.. automodule:: shotgun_api3.shotgun
    :members: NO_SSL_VALIDATION, LOG, __version__

*********
Shotgun()
*********

The majority of functionality is contained within the :class:`~shotgun_api3.Shotgun` class. 
The documentation for all of the methods you'll need in your scripts lives in here.

.. autoclass:: shotgun_api3.Shotgun
    :show-inheritance:
    :inherited-members:
    :members:


**********
Exceptions
**********

These are the various exceptions that the Shotgun API will raise. 

.. autoclass:: shotgun_api3.ShotgunError
    :show-inheritance:
    :inherited-members:
    :members:

.. autoclass:: shotgun_api3.ShotgunFileDownloadError
    :show-inheritance:
    :inherited-members:
    :members:

.. autoclass:: shotgun_api3.Fault
    :show-inheritance:
    :inherited-members:
    :members:

.. autoclass:: shotgun_api3.AuthenticationFault
    :show-inheritance:
    :inherited-members:
    :members:

.. autoclass:: shotgun_api3.MissingTwoFactorAuthenticationFault
    :show-inheritance:
    :inherited-members:
    :members:


******************
ServerCapabilities
******************

This is a container for the server's capabilities, such as version and paging. Used internally to 
determine whether there is support on the server-side for certain features.

.. autoclass:: shotgun_api3.shotgun.ServerCapabilities
    :inherited-members:
    :members:
    :special-members: [__str__]


******************
ClientCapabilities
******************

This is a container for the client capabilities. It detects the current client platform and works 
out the SG field used for local data paths.

.. autoclass:: shotgun_api3.shotgun.ClientCapabilities
    :inherited-members:
    :members:
    :special-members: [__str__]

