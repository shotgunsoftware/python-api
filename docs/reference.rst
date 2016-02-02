Developer Reference
######################################

Shotgun
=======

.. autoclass:: shotgun_api3.Shotgun
    :show-inheritance:
    :inherited-members:
    :members:

Exceptions
==========

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


ServerCapabilities
==================

This is a container for the server's capabilities, such as version and paging. Used internally to determine whether there is support on the server-side for certain features.

.. autoclass:: shotgun_api3.shotgun.ServerCapabilities
    :inherited-members:
    :members:
    :special-members: __str__


ClientCapabilities
==================

This is a container for the client capabilities. It detects the current client platform and works out the SG field used for local data paths.

.. autoclass:: shotgun_api3.shotgun.ClientCapabilities
    :inherited-members:
    :members:
    :special-members: [__str__]

