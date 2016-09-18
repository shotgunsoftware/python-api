.. _event_types:

###########
Event Types
###########

Shotgun generates read-only EventLogEntries for every destructive action performed by a user. And 
by "destructive", we simply mean an action that updates the database somehow, not some tantrum 
that a user has (hopefully). Shotgun also logs some additional useful events that to help keep 
track of activity on your Shotgun instance.
   
************************
Structure of Event Types
************************

The basic structure of event types is broken into 3 parts:

``Application_EntityType_Action``

- ``Application``: Is always "Shotgun" for events automatically created by the Shotgun server. 
  Other Shotgun products may use their name in here, for example, Toolkit has its own events
  that it logs and the application portion is identified by "Toolkit". If you decide to use the 
  EventLogEntry entity to log events for your scripts or tools, you would use your tool name here.
- ``EntityType``: This is the entity type in Shotgun that was acted upon (eg. Shot, Asset, etc.)
- ``Action``: The general action that was taken. (eg. New, Change, Retirement, Revival)   
   

********************
Standard Event Types
********************

Each entity type has a standard set of events associated with it when it's created, updated, 
deleted, and revived. They follow this pattern:

- ``Shotgun_EntityType_New``: a new entity was created. Example: ``Shotgun_Task_New``
- ``Shotgun_EntityType_Change``: an entity was modified. Example: ``Shotgun_HumanUser_Change``
- ``Shotgun_EntityType_Retirement``: an entity was deleted. Example: ``Shotgun_Ticket_Retirement``
- ``Shotgun_EntityType_Revival``: an entity was revived. Example: ``Shotgun_CustomEntity03_Revival``   

**********************
Additional Event Types
**********************

These are _some_ of the additional event types that are logged by Shotgun:
 
- ``Shotgun_Attachment_View``: an Attachment (file) was viewed by a user.
- ``Shotgun_Reading_Change``: a threaded entity has been marked read or unread. For example, a 
  Note was read by a user. The readings are unique to the entity<->user connection so when a 
  Note is read by user "joe" it may still be unread by user "jane".
- ``Shotgun_User_Login``: a user logged in to Shotgun.
- ``Shotgun_User_Logout``: a user logged out of Shotgun. 
   

******************
Custom Event Types
******************

Since ``EventLogEntries`` are entities themselves, you can create them using the API just like any 
other entity type. As mentioned previously, if you'd like to have your scripts or tools log to 
the Shotgun event log, simply devise a thoughtful naming structure for your event types and 
create the EventLogEntry as needed following the usual methods for creating entities via the API.

Again, other Shotgun products like Toolkit use event logs this way.

.. note:: 
    EventLogEntries cannot be updated or deleted (that would defeat the purpose of course).   
   
***********
Performance
***********

Event log database tables can get large very quickly. While Shotgun does very well with event logs 
that get into the millions of records, there's an inevitable degradation of performance for pages 
that display them in the web application as well as any API queries for events when they get too 
big. This volume of events is not the norm, but can be reached if your server expereinces high 
usage. 

This **does not** mean your Shotgun server performance will suffer in general, just any pages that 
are specifically displaying EventLogEntries in the web application, or API queries on the event
log that are run. We are always looking for ways to improve this in the future. If you have any
immediate concerns, please `reach out to our support team <https://support.shotgunsoftware.com>`_
