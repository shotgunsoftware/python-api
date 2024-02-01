.. _svn_integration:

############################
Subversion (SVN) Integration
############################

Integrating Flow Production Tracking with Subversion consists of two basic parts:

- Setup a post-commit hook in Subversion.
- Create a Flow Production Tracking API script to create the Revision in Flow Production Tracking. This script will be called by
  the post-commit hook.
 
****************
Post-Commit Hook
****************

To setup the post-commit hook:

- Locate the ``post-commit.tmpl`` file, which is found inside the ``hooks`` folder in your 
  repository directory.  This is a template script that has lots of useful comments and can serve 
  as a starting point for the real thing.
- Create your very own executable script, and save it in the same ``hooks`` folder, name it 
  ``post-commit``, and give it executable permission.
- In your ``post-commit`` script, invoke your Flow Production Tracking API script.

If this is entirely new to you, we highly suggest reading up on the topic. O'Reilly has `a free 
online guide for Subversion 1.5 and 1.6 
<http://svnbook.red-bean.com/nightly/en/svn.reposadmin.create.html#svn.reposadmin.create.hooks>`_

Here's an example of a post-commit hook that we've made for Subversion 1.6 using an executable 
Unix shell script.  The last line invokes "shotgun_api_script.py" which is our Python script that 
will do all the heavy lifting.  Lines 4 thru 8 queue up some objects that we'll use later on.

.. code-block:: sh
   :linenos:

    #!/bin/sh
    # POST-COMMIT HOOK

    REPOS="$1"
    REV="$2"

    export AUTHOR="$(svnlook author $REPOS --revision $REV)"
    export COMMENT="$(svnlook log $REPOS --revision $REV)"

    /Absolute/path/to/shotgun_api_script.py

Explanation of selected lines
=============================

- lines ``4-5``: After the commit, Subversion leaves us two string objects in the environment: 
  ``REPOS`` and ``REV``  (the repository path and the revision number, respectively).  
- lines ``7-8``: Here we use the shell command ``export`` to create two more string objects in the 
  environment:  ``AUTHOR`` and ``COMMENT``. To get each value, we use the ``svnlook`` command with 
  our ``REPOS`` and ``REV`` values, first with the ``author``, and then with ``log`` subcommand.  
  These are actually the first two original lines of code - everything else to this point was 
  pre-written already in the ``post-commit.tmpl`` file. nice :)  
- line ``10``: This is the absolute path to our Flow Production Tracking API Script.

***********************************
Flow Production Tracking API Script
***********************************

This script will create the Revision and populate it with some metadata using the Flow Production Tracking Python
API. It will create our Revision in Flow Production Tracking along with the author, comment, and because we use
Trac (a web-based interface for Subversion), it will also populate a URL field with a clickable 
link to the Revision.

.. code-block:: python
   :linenos:


    #!/usr/bin/env python
    # ---------------------------------------------------------------------------------------------

    # ---------------------------------------------------------------------------------------------
    # Imports
    # ---------------------------------------------------------------------------------------------
    import sys
    from shotgun_api3_preview import Shotgun
    import os

    # ---------------------------------------------------------------------------------------------
    # Globals - update all of these values to those of your studio
    # ---------------------------------------------------------------------------------------------
    SERVER_PATH = 'https ://my-site.shotgrid.autodesk.com' # or http:
    SCRIPT_USER = 'script_name'    
    SCRIPT_KEY = '3333333333333333333333333333333333333333'
    REVISIONS_PATH = 'https ://serveraddress/trac/changeset/' # or other web-based UI
    PROJECT = {'type':'Project', 'id':27}
       
    # ---------------------------------------------------------------------------------------------
    # Main
    # ---------------------------------------------------------------------------------------------
    if __name__ == '__main__':

       sg = Shotgun(SERVER_PATH, SCRIPT_USER, SCRIPT_KEY)
       
       # Set Python variables from the environment objects
       revision_code = os.environ['REV']
       repository = os.environ['REPOS']
       description = os.environ['COMMENT']
       author = os.environ['AUTHOR']
       
       # Set the Trac path for this specific revision
       revision_url = REVISIONS_PATH + revision_code
       
       # Validate that author is a valid Flow Production Tracking HumanUser
       result = sg.find_one("HumanUser", [['login', 'is', author]])
       if result:
           # Create Revision
           url = {'content_type':'http_url', 'url':revision_url, 'name':'Trac'}
           parameters = {'project':PROJECT,
                           'code':str(revision_code),
                           'description':description,
                           'attachment':url,
                           'created_by':{"type":"HumanUser", "id":result['id']}
                           }
           revision = sg.create("Revision", parameters)
           print("created Revision #"+str(revision_code))
       
       # Send error message if valid HumanUser is not found
       else:
           print("Unable to find a valid Flow Production Tracking User with login: {}, Revision not created in Flow Production Tracking.".format(author))



Explanation of selected lines:
==============================

- line ``14``: This should be the URL to your instance of Flow Production Tracking.
- lines ``15-16``: Make sure you get these values from the "Scripts" page in the Admin section of
  the Flow Production Tracking web application. If you're not sure how to do this, check out :doc:`authentication`.
- line ``17``: This is the address of Trac, our web-based interface that we use with Subversion. 
  You may use a different interface, or none at all, so feel free to adjust this line or ignore it 
  as your case may be.
- line ``18``: Every Revision in Flow Production Tracking must have a Project, which is passed to the API as a
  dictionary with two keys, the ``type`` and the ``id``.  Of course the ``type`` value will always 
  remain ``Project`` (case sensitive), but the ``id`` will change by Project.  To find out the 
  ``id`` of your Project, go to the Projects page in the Flow Production Tracking web application, locate the
  Project where you want your Revisions created, and then locate its ``id`` field (which you may 
  need to display - if you don't see it, right click on any column header then select 
  "Insert Column" > "Id").  Note that for this example we assume that all Revisions in this 
  Subversion repository will belong to the same Project.
- lines ``28-31``: Grab the values from the objects that were left for us in the environment.
- line ``34``: Add the Revision number to complete the path of our Trac url.
- line ``37``: Make sure that a valid User exists in Flow Production Tracking.  In our example, we assume that our
  Users' Flow Production Tracking logins match their Subversion names.  If the user exists in Flow Production Tracking, that
  user's ``id`` will be returned as ``result['id']``, which we will need later on in line 46.
- lines ``40-48``: Use all the meta data we've gathered to create a Revision in Flow Production Tracking. If none
  of these lines make any sense, check out more on the :meth:`~shotgun_api3.Shotgun.create` method 
  here.   Line 41 deserves special mention: notice that we define a dictionary called ``url`` that 
  has three important keys: ``content_type``, ``url``, and ``name``, and we then pass this in as 
  the value for the ``attachment`` field when we create the Revision.  If you're even in doubt, 
  double check the syntax and requirements for the different field types here.

***************
Troubleshooting
***************

My post-commit script is simply not running. I can run it manually, but commits are not triggering it.
======================================================================================================

Make sure that the script is has explicitly been made executable and that all users who will 
invoke it have appropriate permissions for the script and that folders going back to root. 

My Flow Production Tracking API script is not getting called by the post-commit hook.
=====================================================================================

Make sure that the script is called using its absolute path.
