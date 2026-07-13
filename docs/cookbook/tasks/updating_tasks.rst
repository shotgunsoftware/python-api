.. _updating_tasks:

########################################################
Updating Task Dates: How Flow Production Tracking Thinks
########################################################

When updating Task dates in an API update() request, there is no specified order to the values that
are passed in. Flow Production Tracking also does automatic calculation of the``start_date``,``due_date``, and ``duration`` fields for convenience. In order to clarify how updates are handled by Flow Production Tracking we are
providing some general rules below and examples of what will happen when you make updates to your
Tasks.

**************
General Rules
**************

- Updating the ``start_date`` automatically updates the ``due_date`` (``duration`` remains constant)
- Updating the ``due_date`` automatically updates the ``duration`` (``start_date`` remains constant)
- Updating the ``duration`` automatically updates the ``due_date`` (``start_date`` remains constant)
- When updating Task values, Flow Production Tracking sets schedule fields (``milestone``, ``duration``,
  ``start_date``, ``due_date``) after all other fields, because the Project and Task Assignees
  affect schedule calculations.
- If ``start_date`` and ``due_date`` are both set, ``duration`` is ignored (``duration`` can often
  be wrong since it's easy to calculate scheduling incorrectly).
- If both ``start_date`` and ``due_date`` are provided, Flow Production Tracking sets ``start_date`` before
  ``due_date``.
- Set ``milestone`` before other schedule fields (because ``start_date``, ``due_date``, and
  ``duration`` get lost if ``milestone`` is not set to ``False`` first)
- If ``milestone`` is being set to ``True``, ``duration`` is ignored.
- If ``milestone`` is set to ``True`` and ``start_date`` and ``due_date`` are also being set to
  conflicting values, an Exception is raised.
- If ``due_date`` and ``duration`` are set together (without ``start_date``), ``duration`` is set
  first, then ``due_date`` (otherwise setting ``duration`` will change ``due_date`` after it is
  set).

***************************
Examples for updating Tasks
***************************

The following examples show what the resulting Task object will look like after being run on the
initial Task object listed under the header of each section.

The ``duration`` values in the following examples assume your Flow Production Tracking instance is set to
10-hour work days. If your server is configured with a different setting, the ``duration`` values
will vary.

.. note:: The ``duration`` field stores ``duration`` values in minutes


----

.. rubric:: Universal

Regardless of current values on the Task, this behavior rules::

    Task = {'start_date': '2011-05-20', 'due_date': '2011-05-25', 'duration': 2400, 'id':123}

**Update start_date and due_date**

``duration`` is ignored if also provided. It is instead set automatically as (``due_date`` -
``start_date``)

::

    sg.update ('Task', 123, {'start_date':'2011-05-25', 'due_date':'2011-05-30', 'duration':1200})
    # Task = {'start_date': '2011-05-25', 'due_date': '2011-05-30', 'duration': 2400, 'id':123}

- ``start_date`` is updated.
- ``due_date`` is updated.
- ``duration`` is calculated as (``due_date`` - ``start_date``)

.. note:: The value provided in the update() is ignored (and in this case was also incorrect).

**Update start_date and duration**

::

    sg.update ('Task', 123, {'start_date':'2011-05-25', 'duration':3600})
    # Task = {'start_date': '2011-05-25', 'due_date': '2011-06-01', 'duration': 3600, 'id':123}

- ``start_date`` is updated.
- ``duration`` is updated.
- ``due_date`` is updated to (``start_date`` + ``duration``).

**Update due_date and duration**

::

    sg.update ('Task', 123, {'due_date': '2011-05-20', 'duration':3600})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-20', 'duration': 600, 'id':123}

- ``duration`` is updated.
- ``due_date`` is updated.
- ``duration`` is calculated as (``due_date`` - ``start_date``)

.. note:: This means the ``duration`` provided is overwritten.


----

.. rubric:: Task has start_date only

If the Task only has a ``start_date`` value and has no other date values, this is how updates
will behave.

::

    Task = {'start_date': '2011-05-20', 'due_date': None, 'duration': None, 'id':123}

**Update start_date**

::

    sg.update ('Task', 123, {'start_date':'2011-05-25'})
    # Task = {'start_date': '2011-05-25', 'due_date': None, 'duration': None, 'id':123}

- Only ``start_date`` is updated.

**Update due_date**

::

    sg.update ('Task', 123, {'due_date':'2011-05-25'})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-25', 'duration': 2400, 'id':123}

- ``due_date`` is updated.
- ``duration`` is updated to (``due_date`` - ``start_date``).

**Update duration**

::

    sg.update ('Task', 123, {'duration':2400})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-25', 'duration': 2400, 'id':123}

- ``duration`` is updated.
- ``due_date`` is set to (``start_date`` + ``duration``)


----

.. rubric:: Task has due_date only

If the Task only has a ``due_date`` value and has no other date values, this is how updates
will behave.

::

    # Task = {'start_date': None, 'due_date': '2011-05-25', 'duration': None, 'id':123}

**Update start_date**

::

    sg.update ('Task', 123, {'start_date':'2011-05-20'})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-25', 'duration': 2400, 'id':123}

- ``start_date`` is updated.
- ``duration`` is updated to (``due_date`` - ``start_date``).

**Update due_date**

::

    sg.update ('Task', 123, {'due_date':'2011-05-20'})
    # Task = {'start_date': None, 'due_date': '2011-05-20', 'duration': None, 'id':123}

- only ``due_date`` is updated.

**Update duration**

::

    sg.update ('Task', 123, {'duration':2400})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-25', 'duration': 2400, 'id':123}

- ``duration`` is updated.
- ``start_date`` is set to (``due_date`` - ``duration``)


----

.. rubric:: Task has duration only

If the Task only has a ``duration`` value and has no other date values, this is how updates
will behave.

::

    # Task = {'start_date': None, 'due_date': None, 'duration': 2400, 'id':123}

**Update start_date**

::

    sg.update ('Task', 123, {'start_date':'2011-05-20'})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-25', 'duration': 2400, 'id':123}

- ``start_date`` is updated.
- ``due_date`` is updated to (``start_date`` + ``duration``).

**Update due_date**

::

    sg.update ('Task', 123, {'due_date':'2011-05-25'})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-25', 'duration': 2400, 'id':123}

- ``due_date`` is updated.
- ``start_date`` is updated to (``due_date`` - ``duration``)

**Update duration**

::

    sg.update ('Task', 123, {'duration':3600})
    # Task = {'start_date': None, 'due_date': None, 'duration': 3600, 'id':123}

- only ``duration`` is updated.


----

.. rubric:: Task has start_date and due_date

If the Task has ``start_date`` and ``due_date`` values but has no ``duration``, this is how updates
will behave.

::

    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-25', 'duration': None, 'id':123}

**Update start_date**

::

    sg.update ('Task', 123, {'start_date':'2011-05-25'})
    # Task = {'start_date': '2011-05-25', 'due_date': '2011-05-25', 'duration': 600, 'id':123}

- ``start_date`` is updated.
- ``duration`` is updated to (``due_date`` - ``start_date``).

**Update due_date**

::

    sg.update ('Task', 123, {'due_date':'2011-05-30'})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-30', 'duration': 4200, 'id':123}

- ``due_date`` is updated.
- ``duration`` is updated to (``due_date`` - ``start_date``)

**Update duration**

::

    sg.update ('Task', 123, {'duration':3600})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-27', 'duration': 3600, 'id':123}

- ``duration`` is updated.
- ``due_date`` is updated to (``start_date`` + ``duration``)


----

.. rubric:: Task has start_date and duration

If the Task has ``start_date`` and ``duration`` values but has no ``due_date``, this is how updates
will behave.

::

    # Task = {'start_date': '2011-05-20', 'due_date': None, 'duration': 2400, 'id':123}

**Update start_date**

::

    sg.update ('Task', 123, {'start_date':'2011-05-25'})
    # Task = {'start_date': '2011-05-25', 'due_date': '2011-05-30', 'duration': 2400, 'id':123}

- ``start_date`` is updated.
- ``due_date`` is updated to (``start_date`` +``duration``).

**Update due_date**

::

    sg.update ('Task', 123, {'due_date':'2011-05-30'})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-30', 'duration': 4200, 'id':123}

- ``due_date`` is updated.
- ``duration`` is updated to (``due_date`` - ``start_date``).

**Update duration**

::

    sg.update ('Task', 123, {'duration':3600})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-27', 'duration': 3600, 'id':123}

- ``duration`` is updated.
- ``due_date`` is updated to (``start_date`` + ``duration``)


----

.. rubric:: Task has due_date and duration

If the Task has ``due_date`` and ``duration`` values but has no ``start_date``, this is how updates
will behave.

::

    # Task = {'start_date': None, 'due_date': '2011-05-25', 'duration': 2400, 'id':123}

**Update start_date**

::

    sg.update ('Task', 123, {'start_date':'2011-05-25'})
    # Task = {'start_date': '2011-05-25', 'due_date': '2011-05-30', 'duration': 2400, 'id':123}

- ``start_date`` is updated.
- ``due_date`` is updated to (``start_date`` + ``duration``).

**Update due_date**

::

    sg.update ('Task', 123, {'due_date':'2011-05-30'})
    # Task = {'start_date': '2011-05-25', 'due_date': '2011-05-30', 'duration': 2400, 'id':123}

- ``due_date`` is updated.
- ``start_date`` is updated to (``due_date`` - ``duration``).

**Update duration**

::

    sg.update ('Task', 123, {'duration':3600})
    # Task = {'start_date': '2011-05-18', 'due_date': '2011-05-25', 'duration': 3600, 'id':123}

- ``duration`` is updated.
- ``start_date`` is updated to (``due_date`` - ``duration``)


----

.. rubric:: Task has start_date ,due_date, and duration

If the Task has ``start_date``, ``due_date``, and ``duration``, this is how updates
will behave.

::

    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-25', 'duration': 2400, 'id':123}

**Update start_date**

::

    sg.update ('Task', 123, {'start_date':'2011-05-25'})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-30', 'duration': 2400, 'id':123}

- ``start_date`` is updated.
- ``due_date`` is updated to (``start_date`` + ``duration``).

**Update due_date**

::

    sg.update ('Task', 123, {'due_date':'2011-05-30'})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-30', 'duration': 4200, 'id':123}

- ``due_date`` is updated.
- ``duration`` is updated to (``due_date`` - ``start_date``)

**Update duration**

::

    sg.update ('Task', 123, {'duration':3600})
    # Task = {'start_date': '2011-05-20', 'due_date': '2011-05-27', 'duration': 3600, 'id':123}

- ``duration`` is updated.
- ``due_date`` is updated to (``start_date`` + ``duration``)
