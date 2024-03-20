Upload a Thumbnail for a Version
================================

So you've created a new Version of a Shot, and you've updated Flow Production Tracking, but now you want to upload a
beauty frame to display as the thumbnail for your Version. We'll assume you already have the image 
made (located on your machine at ``/v1/gun/s100/010/beauties/anim/100_010_animv1.jpg``) . And since 
you've just created your Version in Flow Production Tracking, you know its ``id`` is **214**.

.. note:: If you upload a movie file or image to the ``sg_uploaded_movie`` field and you have 
    transcoding enabled on your server (the default for hosted sites), a thumbnail will be
    generated automatically as well as a filmstrip thumbnail (if possible).
    This is a basic example of how to manually provide or replace a thumbnail image.

Upload the Image using :meth:`~shotgun_api3.Shotgun.upload_thumbnail`
---------------------------------------------------------------------
::

    sg.upload_thumbnail("Version", 214, "/v1/gun/s100/010/beauties/anim/100_010_animv1.jpg")


Flow Production Tracking will take care of resizing the thumbnail for you. If something does go wrong, an exception
will be thrown and you'll see the error details.

.. note:: The result returned by :meth:`~shotgun_api3.Shotgun.upload_thumbnail` is an integer 
    representing the id of a special ``Attachment`` entity in Flow Production Tracking. Working with Attachments
    is beyond the scope of this example. :)