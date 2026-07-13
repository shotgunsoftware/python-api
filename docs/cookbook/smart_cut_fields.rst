.. _smart_cut_fields:

################
Smart Cut Fields
################

.. warning::
    Smart Cut Fields should be considered deprecated. ShotGrid v7.0, introduced a new version of
    cut support. `Read the Cut Support Documentation here <https://knowledge.autodesk.com/support/shotgrid/learn-explore/caas/CloudHelp/cloudhelp/ENU/SG-Editorial/files/SG-Editorial-ed-cut-schema-html-html.html>`_.

If you want to work with 'smart' cut fields through the API, your script should use a corresponding
'raw' fields for all updates. The 'smart_cut_fields' are primarily for display in the UI, the real
data is stored in a set of 'raw' fields that have different names.

************
Smart Fields
************

In the UI these fields attempt to calculate values based on data entered into the various fields.
These fields can be queried via the API using the find() method, but not updated. Note that we are
deprecating this feature and recommend creating your own cut fields from scratch, which will not
contain any calculations which have proven to be too magical at times.

- ``smart_cut_duration``
- ``smart_cut_in``
- ``smart_cut_out``
- ``smart_cut_summary_display`` *
- ``smart_cut_duration_display`` *
- ``smart_head_duration``
- ``smart_head_in``
- ``smart_head_out``
- ``smart_tail_duration``
- ``smart_tail_in``
- ``smart_tail_out``
- ``smart_working_duration`` *

.. note:: \* these are special summary fields that have no corresponding "raw" field.

**********
Raw Fields
**********

These are the "raw" fields that can be queried and updated through the API:

- ``cut_duration``
- ``cut_in``
- ``cut_out``
- ``head_duration``
- ``head_in``
- ``head_out``
- ``tail_duration``
- ``tail_in``
- ``tail_out``
