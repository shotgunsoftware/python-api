Upload a Thumbnail for a Version
================================

So you've created a new Version of a Shot, and you've updated Shotgun, but now you want to upload a 
beauty frame to display as the thumbnail for your Version. We'll assume you already have the image 
made (located on your machine at ``/v1/gun/s100/010/beauties/anim/100_010_animv1.jpg``) . And since 
you've just created your Version in Shotgun, you know its ``id`` is **214**.

.. note:: If you upload a movie file or image to the ``sg_uploaded_movie`` field and you have 
    transcoding enabled on your server (the default for hosted sites), a thumbnail will be
    generated automatically as well as a filmstrip thumbnail (if possible). But this example is
    provided just to show the basic process of uploading a thumbnail manually where is may be
    necessary.

Upload the Image using :meth:`~shotgun_api3.Shotgun.upload_thumbnail`
---------------------------------------------------------------------
::

    sg.upload_thumbnail("Version", 214, "/v1/gun/s100/010/beauties/anim/100_010_animv1.jpg")


Shotgun will take care of resizing the thumbnail for you. If something does go wrong, an exception 
will be thrown and you'll see the error details.

.. note:: The result returned by :meth:`~shotgun_api3.Shotgun.upload_thumbnail` is an integer 
    representing the id of a special ``Attachment`` entity in Shotgun. Working with Attachments
    is beyond the scope of this example. :)

.. _example_upload_version_thumbnail_pending:

When requesting a thumbnail, you may be returned the following URL:

``/images/status/transient/thumbnail_pending.png``

If you see the above URL, that means there is a placeholder thumbnail that will eventually be
replaced by the final thumbnail. You can adapt your code to `always retry on failure`__, or you can 
use the `Event Log Entries to track thumbnails that have finished processing`__.

 __ https://developer.shotgunsoftware.com/python-api/reference.html#shotgun_api3.shotgun.Shotgun.share_thumbnail
 __ https://github.com/shotgunsoftware/shotgunEvents/wiki/Technical_Overview#event-log-entries-for-thumbnails

.. note:: Shotgun may require transient thumbnails in future features. For this reason, we highly
	  recommend using the prefix part of the placeholder URL (``/images/status/transient``) to
	  detect any transient thumbnails, rather than using the full URL.
