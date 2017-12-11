************
API Cookbook
************

Here we have a collection of useful information you can use for reference when writing your API
scripts. From usage tips and gotchas to deeper examples of working with entities like Tasks and 
Files, there's a lot of example code in here for you to play with.

.. rubric:: Usage Tips

These are some best-practices and good guidelines to follow when developing your scripts.
You'll also find some gotchas you can avoid.

.. toctree::
    :maxdepth: 2

    cookbook/usage_tips

.. rubric:: Examples

Some basic example scripts that we walk you through from beginning to end. Feel free to copy
and paste any of these into your own scripts.

.. toctree::
    :maxdepth: 3

    cookbook/tutorials

.. rubric:: Working With Files

You'll probably be doing some work with files at your studio. This is a deep dive into some of 
the inners of how Shotgun handles files (also called Attachments) and the different ways to link
to them.

.. toctree::
    :maxdepth: 2

    cookbook/attachments

.. rubric:: Working With Tasks

Scheduling is a complex beast. Shotgun can handle lots of different types of functionality around
scheduling like split tasks, dependencies, and more. These docs walk you through the details of
how Shotgun thinks when it's handling Task changes and how you can make your scripts do what you
need to do.

.. toctree::
    :maxdepth: 2

    cookbook/tasks

.. rubric:: Smart Cut Fields

Smart Cut Fields are deprecated in favor of the 
`new cut support added in Shotgun v7.0 <https://support.shotgunsoftware.com/hc/en-us/articles/222840748>`_. 
This documentation remains only to support studios who may not have upgraded to the new cut support
features. 

.. toctree::
    :maxdepth: 2

    cookbook/smart_cut_fields