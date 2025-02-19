.. _task_dependencies:

#################
Task Dependencies
#################

Task dependencies work the same way in the API as they do in the UI. You can filter and sort on
any of the fields. For information about Task Dependencies in Flow Production Tracking, check out the `main
documentation page on our support site
<https://help.autodesk.com/view/SGSUB/ENU/?guid=SG_Producer_pr_scheduling_tasks_pr_gantt_chart_tasks_html>`_

************
Create Tasks
************

Let's create a couple of Tasks and create dependencies between them. First we'll create a "Layout"
Task for our Shot::

    data = {
        'project': {'type':'Project', 'id':65},
        'content': 'Layout',
        'start_date': '2010-04-28',
        'due_date': '2010-05-05',
        'entity': {'type':'Shot', 'id':860}
        }
    result = sg.create(Task, data)


Returns::

    {'content': 'Layout',
     'due_date': '2010-05-05',
     'entity': {'id': 860, 'name': 'bunny_010_0010', 'type': 'Shot'},
     'id': 556,
     'project': {'id': 65, 'name': 'Demo Animation Project', 'type': 'Project'},
     'start_date': '2010-04-28',
     'type': 'Task'}


Now let's create an "Anm" Task for our Shot::

    data = {
        'project': {'type':'Project', 'id':65},
        'content': 'Anm',
        'start_date': '2010-05-06',
        'due_date': '2010-05-12',
        'entity': {'type':'Shot', 'id':860}
        }
    result = sg.create(Task, data)

Returns::

    {'content': 'Anm',
     'due_date': '2010-05-12',
     'entity': {'id': 860, 'name': 'bunny_010_0010', 'type': 'Shot'},
     'id': 557,
     'project': {'id': 65, 'name': 'Demo Animation Project', 'type': 'Project'},
     'start_date': '2010-05-06,
     'type': 'Task'}


*******************
Create A Dependency
*******************

Tasks each have an ``upstream_tasks`` field and a ``downstream_tasks`` field. Each field is a
list ``[]`` type and can contain zero, one, or multiple Task entity dictionaries representing the
dependent Tasks.
There are four dependency types from which you can choose: ``finish-to-start-next-day``, ``start-to-finish-next-day``, ``start-to-start``, ``finish-to-finish``.
If no dependency type is provided the default ``finish-to-start-next-day`` will be used.
Here is how to create a dependency between our "Layout" and "Anm" Tasks::

    # make 'Layout' an upstream Task to 'Anm'. (aka, make 'Anm' dependent on 'Layout') with finish-to-start-next-day dependency type
    data = {
        'upstream_tasks':[{'type':'Task','id':556, 'dependency_type': 'finish-to-start-next-day'}]
    }
    result = sg.update('Task', 557, data)

Returns::

    [{'id': 557,
      'type': 'Task',
      'upstream_tasks': [{'id': 556, 'name': 'Layout', 'type': 'Task'}]}]

This will also automatically update the `downstream_tasks` field on 'Layout' to include the 'Anm' Task.

***********************
Query Task Dependencies
***********************

Task Dependencies each have a ``dependent_task_id`` and a ``task_id`` fields.
They correspond to ``upstream_task`` and ``downstream_task`` ids of the dependency accordingly.
Here is how to get a TaskDependency using a ``dependent_task_id`` and a ``task_id`` fields::

    filters = [["dependent_task_id", "is", 72], ["task_id", "is", 75]]
    result = sg.find_one('TaskDependency', filters)

Returns::

    {'type': 'TaskDependency', 'id': 128}

****************************
Updating the Dependency type
****************************

When updating the dependency type for the existing dependencies,
update the ``dependency_type`` field of the TaskDependency directly::

    result = sg.update('TaskDependency', 128, {'dependency_type': 'start-to-start'})

Returns::

    {'dependency_type': 'start-to-start', 'type': 'TaskDependency', 'id': 128}

**********************************
Query Tasks with Dependency Fields
**********************************

So now lets look at the Tasks we've created and their dependency-related fields::

    filters = [
        ['entity', 'is', {'type':'Shot', 'id':860}]
    ]
    fields = [
        'content',
        'start_date',
        'due_date',
        'upstream_tasks',
        'downstream_tasks',
        'dependency_violation',
        'pinned'
        ]
    result = sg.find("Task", filters, fields)

Returns::

    [{'content': 'Layout',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'Anm', 'id': 557}],
      'due_date': '2010-05-05',
      'id': 556,
      'pinned': False,
      'start_date': '2010-04-28',
      'type': 'Task',
      'upstream_tasks': []},
     {'content': 'Anm',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'FX', 'id': 558}],
      'due_date': '2010-05-12',
      'id': 557,
      'pinned': False,
      'start_date': '2010-05-06',
      'type': 'Task',
      'upstream_tasks': [{'type': 'Task', 'name': 'Layout', 'id': 556}]},
    ...

*Note that we have also created additional Tasks for this Shot but we're going to focus on these
first two for simplicity.*

*****************************************************************
Updating the End Date on a Task with Downstream Task Dependencies
*****************************************************************

If we update the ``due_date`` field on our "Layout" Task, we'll see that the "Anm" Task dates
will automatically get pushed back to keep the dependency satisfied::

    result = sg.update('Task', 556, {'due_date': '2010-05-07'})

Returns::

    [{'due_date': '2010-05-07', 'type': 'Task', 'id': 556}]

Our Tasks now look like this (notice the new dates on the "Anm" Task)::

    [{'content': 'Layout',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'Anm', 'id': 557}],
      'due_date': '2010-05-07',
      'id': 556,
      'pinned': False,
      'start_date': '2010-04-28',
      'type': 'Task',
      'upstream_tasks': []},
     {'content': 'Anm',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'FX', 'id': 558}],
      'due_date': '2010-05-14',
      'id': 557,
      'pinned': False,
      'start_date': '2010-05-10',
      'type': 'Task',
      'upstream_tasks': [{'type': 'Task', 'name': 'Layout', 'id': 556}]},
    ...


**********************************************************
Creating a Dependency Violation by pushing up a Start Date
**********************************************************

Task Dependencies can work nicely if you are pushing out an end date for a Task as it will just
recalculate the dates for all of the dependent Tasks. But what if we push up the Start Date of our
"Anm" Task to start before our "Layout" Task is scheduled to end?

::

    result = sg.update('Task', 557, {'start_date': '2010-05-06'})

Returns::

    [{'type': 'Task', 'start_date': '2010-05-06', 'id': 557}]

Our Tasks now look like this::

    [{'content': 'Layout',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'Anm', 'id': 557}],
      'due_date': '2010-05-07',
      'id': 556,
      'pinned': False,
      'start_date': '2010-04-28',
      'type': 'Task',
      'upstream_tasks': []},
     {'content': 'Anm',
      'dependency_violation': True,
      'downstream_tasks': [{'type': 'Task', 'name': 'FX', 'id': 558}],
      'due_date': '2010-05-12',
      'id': 557,
      'pinned': True,
      'start_date': '2010-05-06',
      'type': 'Task',
      'upstream_tasks': [{'type': 'Task', 'name': 'Layout', 'id': 556}]},
     ...

Because the "Anm" Task ``start_date`` depends on the ``due_date`` of the "Layout" Task, this
change creates a dependency violation. The update succeeds, but Flow Production Tracking has also set the
``dependency_violation`` field to ``True`` and has also updated the ``pinned`` field to ``True``.

The ``pinned`` field simply means that if the upstream Task(s) are moved, the "Anm" Task will no
longer get moved with it. The dependency is still there (in ``upstream_tasks``) but the Task is
now "pinned" to those dates until the Dependency Violation is resolved.

***********************************************************
Resolving a Dependency Violation by updating the Start Date
***********************************************************

We don't want that violation there. Let's revert that change so the Start Date for "Anm" is after
the End Date of "Layout"::

    result = sg.update('Task', 557, {'start_date': '2010-05-10'})

Returns::

    [{'type': 'Task', 'start_date': '2010-05-10', 'id': 557}]

Our Tasks now look like this::

    [{'content': 'Layout',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'Anm', 'id': 557}],
      'due_date': '2010-05-07',
      'id': 556,
      'pinned': False,
      'start_date': '2010-04-28',
      'type': 'Task',
      'upstream_tasks': []},
     {'content': 'Anm',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'FX', 'id': 558}],
      'due_date': '2010-05-14',
      'id': 557,
      'pinned': True,
      'start_date': '2010-05-10',
      'type': 'Task',
      'upstream_tasks': [{'type': 'Task', 'name': 'Layout', 'id': 556}]},
     ...

The ``dependency_violation`` field has now been set back to ``False`` since there is no longer
a violation. But notice that the ``pinned`` field is still ``True``. We will have to manually
update that if we want the Task to travel with its dependencies again::

    result = sg.update('Task', 557, {'pinned': False})

Returns::

    [{'pinned': False, 'type': 'Task', 'id': 557}]

Our Tasks now look like this::

    [{'content': 'Layout',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'Anm', 'id': 557}],
      'due_date': '2010-05-07',
      'id': 556,
      'pinned': False,
      'start_date': '2010-04-28',
      'type': 'Task',
      'upstream_tasks': []},
     {'content': 'Anm',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'FX', 'id': 558}],
      'due_date': '2010-05-14',
      'id': 557,
      'pinned': False,
      'start_date': '2010-05-10',
      'type': 'Task',
      'upstream_tasks': [{'type': 'Task', 'name': 'Layout', 'id': 556}]},
     ...

Looks great. But that's an annoying manual process. What if we want to just reset a Task so that
it automatically gets updated so that the Start Date is after its dependent Tasks?

*******************************************************************
Updating the ``pinned`` field on a Task with a Dependency Violation
*******************************************************************

Let's go back a couple of steps to where our "Anm" Task had a Dependency Violation because we had
moved the Start Date up before the "Layout" Task End Date. Remember that the ``pinned`` field
was also ``True``. If we simply update the ``pinned`` field to be ``False``, Flow Production Tracking will also
automatically update the Task dates to satisfy the upstream dependencies and reset the
``dependency_violation`` value to ``False``::

    result = sg.update('Task', 557, {'pinned': False})

Returns::

    [{'pinned': False, 'type': 'Task', 'id': 557}]


Our Tasks now look like this::

    [{'content': 'Layout',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'Anm', 'id': 557}],
      'due_date': '2010-05-07',
      'id': 556,
      'pinned': False,
      'start_date': '2010-04-28',
      'type': 'Task',
      'upstream_tasks': []},
     {'content': 'Anm',
      'dependency_violation': False,
      'downstream_tasks': [{'type': 'Task', 'name': 'FX', 'id': 558}],
      'due_date': '2010-05-14',
      'id': 557,
      'pinned': False,
      'start_date': '2010-05-10',
      'type': 'Task',
      'upstream_tasks': [{'type': 'Task', 'name': 'Layout', 'id': 556}]},
    ...


Notice by updating ``pinned`` to ``False``, Flow Production Tracking also updated the ``start_date`` and
``due_date`` fields of our "Anm" Task so it will satisfy the upstream Task dependencies. And since
that succeeded, the ``dependency_violation`` field has also been set to ``False``

*******************************************
``dependency_violation`` field is read-only
*******************************************

The ``dependency_violation`` field is the only dependency-related field that is read-only. Trying
to modify it will generate a Fault::

    result = sg.update('Task', 557, {'dependency_violation': False})

Returns::

    # --------------------------------------------------------------------------------
    # XMLRPC Fault 103:
    # API update() Task.dependency_violation is read only:
    # {"value"=>false, "field_name"=>"dependency_violation"}
    # --------------------------------------------------------------------------------
    # Traceback (most recent call last):
    # ...
