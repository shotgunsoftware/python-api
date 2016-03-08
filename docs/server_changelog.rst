****************************
Shotgun Server API Changelog
****************************

.. warning:: This list is out of date and has not been updated since 5/2014

The following is a list of changes in the Shotgun server code that affect the API. These are not changes in the Python API code, rather fixes/changes to the Shotgun server's API interface that may affect behavior. Generally changes to the Shotgun server API code are ensured to be non-breaking and backwards compatible bug fixes and feature enhancements. This is to ensure your scripts will not unexpectedly break when updating.

These updates should also appear on the general Release Notes pages but are provided here for convenience.

Format: **[Shotgun server version]**: Description of change made. [internal ticket #]

- **[5.3.15]**: Added filtering out Archived projects. [25082]
- **[5.3.12]**: Added support for API ``sudo_as_user``. [19989]
- **[5.1.22]**: Added ``followers()``, ``follow()``, and ``unfollow()`` methods to code handling API requests. [20562]
- **[3.3.1]**: Modified CRUD code so that if a request reads, sorts, or summarizes a join (ConnectionEntity) field, and the parent entity has not been passed in the request, the code will try to infer it from the filter conditions. Prior to this fix on 3.3 - the API was returning an error when trying to sort Versions on ``playlists.PlaylistVersionConnection.sg_sort_order``. Note that if the parent entity cannot be inferred automatically, this error will still occur. [17107]
- **[3.3.0]**: Added support for returning the full paths of thumbnail fields in regular API calls. This works for thumbnail fields on the entity, linked thumbnails, and filmstrip thumbnails. [10693]
- **[3.0.0]**: We've released v3.0.8 of the Python API which now includes a JSON backend. The JSON transport is up to 40% faster than the XML-RPC based transport. The XML-RPC interface will continue to be supported but may not include new features, so previous versions of the API will still be supported as-is.
- **[3.0.0]**: Added support for ``name_is`` filter operator on single and multi-entity fields, both in the API and the UI.
- **[2.4.8]**: Added support for ``id`` inquiry filters in the API. The syntax is slightly different than similar filters, in that the filter value is not an array. [14261]
- **[2.4.6]**: Fixed issue with multi-entity field filters where Python ``None`` was passed in. Prior to this fix, one could not use the API to create filters such as ``['task_assignees', 'is', None]`` or ``['task_assignees', 'is_not', None]``, without generating an API error. These filters are now allowed, and work as expected. [14111]
- **[2.4.0]**: Added query builder and API support for next/previous modifiers for the ``in calendar period`` filter operators for date and datetime fields. For example, "find tasks that were created in the last 7 months..."
- **[2.4.0]**: Ensured that the UI and the API disallow configuring Note Links field to allow the Task or Note entity type.
- **[2.4.0]**: Date fields now require ``YYYY-MM-DD`` format. Previously they were documented as requiring that format, but would actually allow other date formats if the server was able to parse them into a valid date.
- **[2.3.9]**: Ensured that creating a task (via the API) with ONLY the duration set - if that task is created with an upstream task that has an end date - results in the created task having both its Start and Due date set by the task dependency logic. [13407]
- **[2.3.7]**: Ensured API parity with UI in terms of passing in filters on linked fields more than 1 link away. [12867]
- **[2.3.7]**: Ensured that API errors are not thrown when creating/updating a task with ``milestone=True``, and ``start_date=end_date``. This behavior is true when using ``create()``, ``update()``, or either method with ``batch()``. Also, added a unit test to cover this. [13318]
- **[2.3.5]**: Added API support for getting Shotgun's version and build number. Usage requires Shotgun Python API v3.0.6 or higher.
- **[2.3.3]**: Fixed bug with API where local file paths for windows mount points were being double-escaped, resulting in ``\`` character sequences. [13119]
- **[2.2.5]**: Ensured that API calls requesting summary fields do not result in silent logging on errors to production.log. This fix results in no change for API programmers, but does ensure that such API calls can occur without the possibility of killing apache due to unwieldy and unnecessary logging. [12850]
- **[2.2.4]**: Ensured that creating a Task Template Task through the API doesn't require a project id - unlike creating a non template task. [11283]
- **[2.2.4]**: Fixed error generated when trying to revive a Script (``ApiUser``) via the API [12794]
- **[2.0.0]**: Added the ability to link to local files via the API.
- **[2.1.2]**: Enforced uniqueness on Script names (``ApiUser``) so that when creating scripts, the naming conflicts will no longer be allowed. [11479]
- **[2.1.0]**: added a ``revive()`` method in the API. Syntax follows that of ``delete()``
- **[2.0.8]**: Disallowed retired scripts from authenticating via the API. The main Shotgun method will still return a valid Shotgun instance, but any other method calls will return the following error... ``shotgun.Fault: [11480]``
- **[2.0.0]**: Provided API support for ``layout_project`` for Project creation. Functionality mirrors the web interface: omitting ``layout_project`` creates the Project based on Template Project. Supplying ``layout_project`` ensures that the new project is based on the supplied project. This fixes the problem of script-created projects having no pages - since they lacked a template, implicit or explicit.
- **[2.0.0]**: Improved API error message resulting when trying to set the ``default_value`` property on non status list fields, using ``schema_field_create()``.
- **[2.0.0]**: Removed legacy support for ``sg_system_task_type``. Now, all API methods should use Pipeline Steps instead.
- **[2.0.0]**: ended support for API v2 (API2)