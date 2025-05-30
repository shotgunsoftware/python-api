Create a Shot with a Task Template
==================================
Creating a new Shot with a Task Template is just like linking it to another entity, but Flow Production Tracking will apply the Task Template in the background and create the appropriate Tasks on the Shot for you.

Find the Task Template
----------------------
First we need to find the Task Template we're going to apply. We'll assume you know the name of the Task Template you want to use.
::

    filters = [['code','is', '3D Shot Template' ]]
    template = sg.find_one('TaskTemplate', filters)


The Resulting Task Template
---------------------------

Assuming the task template was found, we will now have something like this in our ``template``
variable::

    {'type': 'TaskTemplate', 'id': 12}

Create the Shot
---------------
Now we can create the Shot with the link to the ``TaskTemplate`` to apply.
::

    data = {'project': {'type': 'Project','id': 4},
            'code': '100_010',
            'description': 'dark shot with wicked cool ninjas',
            'task_template': template }
    result = sg.create('Shot', data)

This will create a new Shot named "100_010" linked to the TaskTemplate "3D Shot Template" and
Flow Production Tracking will then create the Tasks defined in the template and link them to the Shot you just
created.

- ``data`` is a list of key/value pairs where the key is the column name to update and the value is
  the value.
- ``project`` and `code` are required
- ``description`` is just a text field that you might want to update as well
- ``task_template`` is another entity column where we set the Task Template which has the Tasks we
  wish to create by default on this Shot. We found the specific template we wanted to assign in the
  previous block by searching

Create Shot Result
------------------
The variable ``result`` now contains the dictionary of the new Shot that was created.
::

    {
        'code': '010_010',
        'description': 'dark shot with wicked cool ninjas',
        'id': 2345,
        'project': {'id': 4, 'name': 'Gunslinger', 'type': 'Project'},
        'task_template': {'id': 12,
                       'name': '3D Shot Template',
                       'type': 'TaskTemplate'},
        'type': 'Shot'
    }


If we now search for the Tasks linked to the Shot, we'll find the Tasks that match our
``TaskTemplate``::

    tasks = sg.find('Task', filters=[['entity', 'is', result]])

.. note:: You can use an entity dictionary that was returned from the API in a filter as we have
    done above. Flow Production Tracking will only look at the ``id`` and ``type`` keys and will ignore the rest.
    This is a handy way to pass around entity dictionaries without having to reformat them.

Now the ``tasks`` variable contains the following::

    [{'id': 3253, 'type': 'Task'},
     {'id': 3254, 'type': 'Task'},
     {'id': 3255, 'type': 'Task'},
     {'id': 3256, 'type': 'Task'},
     {'id': 3257, 'type': 'Task'}]
