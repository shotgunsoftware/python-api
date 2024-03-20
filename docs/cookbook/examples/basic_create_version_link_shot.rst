Create a Version Linked to a Shot
=================================
You've just created a sweet new Version of your shot. Now you want to update Flow Production Tracking and create a
new ``Version`` entity linked to the Shot.

Find the Shot
-------------
First we need to find the Shot since we'll need to know know its ``id`` in order to link our Version 
to it.
::

    filters = [ ['project', 'is', {'type': 'Project', 'id': 4}],
                ['code', 'is', '100_010'] ]
    shot = sg.find_one('Shot', filters)


Find the Task
-------------
Now we find the Task that the Version relates to, again so we can use the ``id`` to link it to the 
Version we're creating. For this search we'll use the Shot ``id`` (which we have now in the ``shot`` 
variable from the previous search) and the Task Name, which maps to the ``content`` field.
::

    filters = [ ['project', 'is', {'type': 'Project', 'id': 4}],
                ['entity', 'is',{'type':'Shot', 'id': shot['id']}],
                ['content', 'is', 'Animation'] ]
    task = sg.find_one('Task', filters)

.. note:: Linking a Task to the Version is good practice. By doing so it is easy for users to see
    at what stage a particular Version was created, and opens up other possibilities for tracking 
    in Flow Production Tracking. We highly recommend doing this whenever possible.

Create the Version
------------------
Now we can create the Version with the link to the Shot and the Task::

    data = { 'project': {'type': 'Project','id': 4},
             'code': '100_010_anim_v1',
             'description': 'first pass at opening shot with bunnies',
             'sg_path_to_frames': '/v1/gun/s100/010/frames/anim/100_010_animv1_jack.#.jpg',
             'sg_status_list': 'rev',
             'entity': {'type': 'Shot', 'id': shot['id']},
             'sg_task': {'type': 'Task', 'id': task['id']},
             'user': {'type': 'HumanUser', 'id': 165} }
    result = sg.create('Version', data)

This will create a new Version named '100_010_anim_v1' linked to the 'Animation' Task for Shot 
'100_010' in the Project 'Gunslinger'.

- ``data`` is a list of key/value pairs where the key is the column name to update and the value is 
  the value to set.
- ``project`` and ``code`` are required
- ``description`` and ``sg_path_to_frames`` are just text fields that you might want to update as 
  well
- ``sg_status_list`` is the status column for the Version. Here we are setting it to "rev" (Pending 
  Review) so that it will get reviewed in the next dailies session and people will "ooh" and "aaah".
- ``entity`` is where we link this version to the Shot. Entity columns are always handled with this 
  format. You must provide the entity ``type`` and its ``id``.
- ``sg_task`` is another entity link field specifically for the Version's Task link.  This uses the 
  same entity format as the Shot link, but pointing to the Task entity this time.
- ``user`` is another entity column where we set the artist responsible for this masterpiece. In 
  this example, I know the 'id' that corresponds to this user, but if you don't know the id you can 
  look it up by searching on any of the fields, similar to what we did for the Shot above, like::

    filters = [['login', 'is', 'jschmoe']]
    user = sg.find('HumanUser', filters)

The ``result`` variable now contains the ``id`` of the new Version that was created::

    214


Upload a movie for review in Screening Room
-------------------------------------------
If Screening Room's transcoding feature is enabled on your site (hosted sites have this by 
default), then you can use the :meth:`~shotgun_api3.Shotgun.upload` method to upload a QuickTime 
movie, PDF, still image, etc. to the ``sg_uploaded_movie`` field on a Version.  Once the movie is 
uploaded, it will automatically be queued for transcoding.  When transcoding is complete, the 
Version will be playable in the Screening Room app, or in the Overlay player by clicking on the 
Play button that will appear on the Version's thumbnail.

.. note:: Transcoding also generates a thumbnail and filmstrip thumbnail automatically.