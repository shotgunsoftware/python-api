*********************************************
Flow Production Tracking Python API Changelog
*********************************************

Here you can see the full list of changes between each Python API release.

v3.8.4 (2025 Jun 11)
====================

- Replace ``utcfromtimestamp`` to prevent breaking changes in Python 3.12.

v3.8.3 (2025 May 22)
====================

- Add improvements to Mockgun.
  Ensure string comparison are case insensitive.
  Ignore duplicate entities when ``multi_entity_update_mode`` is added.
  Support for ``None`` in mockgun when using ordering.
  Thank you rlessardrodeofx, slingshotsys, and MHendricks for your contributions.
- Minor fixes on unit tests and documentation.


v3.8.2 (2025 Mar 11)
====================

- Prevent flaky disconnection when uploading thumbnails on publish.
  There's a flaky disconnection when the publisher uploads the thumbnail to the server.
  The most common errors were: ``Connection closed by peer`` and ``URLopen error EOF occurred in violation of protocol ssl.c:1006``.

v3.8.1 (2025 Feb 25)
====================

- Upgrade certifi to 2024.12.14.
- Apply black 25.1.0 formatting to the source code.
- Update Software Credits

v3.8.0 (2025 Feb 7)
===================

- Extend the payload optimizations to the ``in`` and ``not_in`` filters and
  the ``update`` method.
- The payload optimization is now enabled by default.
  It can be disabled with the ``SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION``
  environment variable.

v3.7.0 (2024 Dec 9)
===================
- Remove unnecessary data in the payload when combining related queries before sending it to the server.
  This would improve overall performance decreasing network latency and server processing.
  See documentation for more information.


v3.6.2 (2024 Aug 13)
====================
- Remove Ticket entity reference and prepare this to run in CI.
- Condition auth for Jenkins environment.
- Update certifi to 2024.7.4.
- FIRST PHASE Python2 removing.

v3.6.1 (2024 Jun 6)
===================
- Adds multi_entity_update_modes support to mockgun ``update()`` and ``batch()`` methods.
- Implements a retry strategy only when encountering an URLError or SSLEOFError.
- Fixes the issue with deleting prefix and suffix for ``display_name`` variable at the moment of upload for a local install.
- Clarifies the use of ``_build_opener`` in ``download_attachment()``.

v3.6.0 (2024 May 1)
===================
- Drop support for Python 2.7
- certifi version changed to 2024.2.2
- Documentation update

v3.5.1 (2024 Apr 3)
===================
- Documentation: Revert to Shotgun in the API Reference headers to keep consistency with the API methods
- Mockgun: fix entity data type
- Mockgun: add support for ``add_user_agent`` and ``set_session_uuid`` methods

v3.5.0 (2024 Mar 26)
====================
- Rebranding component for Flow Production Tracking

v3.4.2 (2024 Feb 6)
===================
- Add support for Python 3.11

v3.4.1 (2024 Jan 29)
====================
- Flaky Tests
- Documentation: Fix issue regarding "in" filter prototype
- Documentation: Travis badge image is no working anymore
- Documentation: Add ``user_subscription_read`` and ``user_subscription_create`` methods
- Update Python Certifi license block
- Add methods for the user_subscriptions API end points
- Retry ShotGrid request also on error 504
- Retry S3 uploads on error 500
- Comment typing annotation breaks Python 2 compatibility
- Add field type ``entity_type`` to mockgun


v3.4.0 (2023 Sep 22)
====================
- Started support for Python 3.10 for CI.
- Add documentation for PublishedFiles preset filters.
- Upgrade httplib2 to 0.22.0.
- Update licensing.
- Updates Autodesk URLs.
- Fix flaky tests.

v3.3.6 (2023 Aug 29)
====================
- Update docs for entity fields.
- Fix typo.
- Fix incorrect hint.
- Reformat code examples to prevent text overflow.
- Bump certifi from 2020.06.20 to 2022.12.7 in /shotgun_api3/lib.
- Skip SG-MIM entities.
- Replace shotgunsoftware references.
- Deprecation of Python 2.
- Security upgrade certifi to latest version 2023.07.22.

v3.3.5 (2023 Jan 5)
====================
- Add "Setting Up Your Environment with the Python API" to Python Docs (python-api docs).
- [Python API Documentation] Update Python version requirements.
- Rename Shotgun to Shotgrid in every about text like tk-multi-demo git repository.
- Rename Shotgun servers to ShotGrid servers in the documentation.

v3.3.4 (2022 June 9)
====================
- Adds Retries on 503 Errors when uploading to S3.
- Updates AMI Documentation to Support Python 3.
- Adds Python 3.9 coverage in Azure Pipeline CI tests.
- Fixes git protocol for the installation.

v3.3.3 (2021 December 1)
==========================
- Replaces shotgunsoftware urls with Autodesk Knowledge Network and ShotGrid Developer Documentation pages.

v3.3.2 (2021 September 27)
==========================
- Updates version of httplib2.

v3.3.1 (2021 July 12)
=====================
- Implements retries with incremental backoff on 502 errors.

v3.3.0 (2021 Jun 7)
===================
- Updates documentation and error messages to mention ShotGrid.

v3.2.6 (2020 Nov 24)
=====================
- Now includes ``certifi`` and defaults to using the certificates provided with that module.

v3.2.4 (2020 May 25)
=====================
- Updates httplib2 to v0.18.0.

v3.2.3 (2020 Apr 21)
=====================
- Fixes an import bug in httplib2 by using the `forked repository <https://github.com/shotgunsoftware/httplib2>`_.

v3.2.2 (2019 Dec 11)
=====================
- Upgrades packaged six module to 1.13.0
- Adds ``platform`` and ``normalize_platform`` to sgsix module to provide unified platform value across Python 2/3
- Changes httplib import procedure to emulate direct import of the module
- Adds test to ensure httplib2 is importable as expected

v3.2.1 (2019 Oct 29)
=====================
- Returns a specific error from ``share_thumbnail`` when the source thumbnail is a 'transient' thumbnail.

v3.2.0 (2019 Sept 23)
=====================
- Adds a new ``project_entity`` parameter to  ``schema_field_update`` that allows to modify field visibility for a given project.

v3.1.2 (2019 Sept 17)
=====================
- Adds an optional `localized` property on the Shotgun object which allows to retrieve localized display names on
  methods ``schema_entity_read()``, ``schema_field_read()``, and ``schema_read()``.

v3.1.1 (2019 August 29)
=======================
- Fixes a regression on Python 2.7.0-2.7.9 on Windows with the mimetypes module.

v3.1.0 (2019 July 29)
=====================
- Adds support for Python 3.7

v3.0.41 (2019 June 28)
======================
- Adds an optional sleep between retries specified via the `SHOTGUN_API_RETRY_INTERVAL` environment variable, or by setting `sg.config.rpc_attempt_interval`.

v3.0.40 (2019 March 13)
=======================
- Updates encoding method to use shutil when uploading, to avoid memory and overflow errors when reading large files. (contributed by @eestrada)

v3.0.39 (2019 February 20)
==========================
- Ensures the certificates packaged with the API and those specified via the `SHOTGUN_API_CACERTS` environment variable
  are used when uploading a file.

v3.0.38 (2019 February 7)
=========================
- Upgrades the version of ``httplib2`` to ``0.12.0``, which fixes SNI issues. Note this
  version contains a more recent list of certificate authorities. If you are running Shotgun locally and have
  signed your https certificate with an outdated certificate authority, the Shotgun connection will be rejected.

v3.0.37 (2018 July 19)
======================

- Proper support added for unicode and utf-8 string paths given to upload methods, and a sane error is raised when an unusable string encoding is used.
- Adds support for querying preferences from Shotgun via the new preferences_read method.
- Under-the-hood changes to add support for direct to s3 uploads to Shotgun. This change should be transparent to users.

v3.0.36 (2018 April 3)
======================

- Fixes an error where ``connect=False`` during ``__init__`` would still connect to Shotgun.
- Adds support for ``SHOTGUN_API_CACERTS`` when uploading and downloading files.
- Properly handles failed downloads due to malware scanning.

v3.0.35 (2017 December 8)
=========================

- Add exception UserCredentialsNotAllowedForSSOAuthenticationFault.
  Triggered when attempting to initiate a connection with a username/password
  pair on an SSO-enabled Shotgun site.

v3.0.34 (2017 September 18)
===========================

- Optimized pagination strategy for Shotgun 7.4+
- Switched from a hard-coded value of 500 for "records_per_page" to a server-defined value. We will be experimenting with higher values with the goal of increasing performance for large result sets.

v3.0.33 (2017 July 18)
======================

- Raise an exception when uploading an empty file using :meth:`upload`, :meth:`upload_thumbnail`
  or :meth:`upload_filmstrip_thumbnail` before calling out to the server.
- Multiple enhancements and bugfixes to Mockgun
- Added ``nav_search_string()`` and ``nav_search_entity()`` methods as experimental, internal methods for querying SG hierarchy.
- Introduces a :meth:`following` query method, that accepts a user entity and optionally an entity type and/or project.

v3.0.32 (2016 Sep 22)
=====================

- Optimized import speed of the API on Python 2.7.
- Integrated the latest fixes to the ``mimetypes`` module.
- Added ``nav_expand()`` method as an experimental, internal method for querying SG hierarchy.
- Ported all documentation to sphinx. See http://developer.shotgridsoftware.com/python-api.
- Moved Changelog to dedicated HISTORY file.

v3.0.31 (2016 May 18)
=====================

- Add optional ``additional_filter_presets`` argument to :meth:`find` and :meth:`find_one`

v3.0.30 (2016 Apr 25)
=====================

- Add option to use add/remove/set modes when updating multi-entity fields.
- Add explicit file handler close to download_attachment.
- Add basic :meth:`find` ordering support to mockgun.
- Allow for product specific authorization parameters.

v3.0.29 (2016 Mar 7)
====================

- Reverted the change to the default field names for image uploading.

v3.0.28 (2016 Mar 3)
====================

- Refactored nested classing of ``sgtimezone`` library to allow for serializable timestamps.

v3.0.27 (2016 Feb 18)
=====================

- Make sure HTTP proxy authentication works with the ``@`` character in a password.
- Make sure sudo authentication test works with Shotgun versions after v6.3.10.
- Smarter uploading of thumbnails and filmstrips with the :meth:`upload` method.
- Improve Travis build integration of the Python-API to run the full suite of
  API tests instead of just the unit and client tests.

v3.0.26 (2016 Feb 1)
====================

- Updating testing framework to use environment variables inconjunction with existing
  ``example_config`` file so that commits and pull requests are automatically run on travis-ci.
- Fix to prevent stripping out case-sensitivity of a URL if the user passes their credentials to
  ``config.server`` as an authorization header.

v3.0.25 (2016 Jan 12)
=====================

- Add handling for Python versions incompatible with SHA-2 (see `this blog post
  <https://www.shotgridsoftware.com/blog/important-ssl-certificate-renewal-and-sha-2/>`_).
- Add ``SHOTGUN_FORCE_CERTIFICATE_VALIDATION`` environment variable to prevent disabling certficate
  validation when SHA-2 validation is not available.
- Add SSL info to user-agent header.

v3.0.24 (2016 Jan 08)
=====================

- Not released.

v3.0.23 (2015 Oct 26)
=====================

- Fix for `python bug #23371 <http://bugs.python.org/issue23371>`_ on Windows loading mimetypes
  module (thanks `@patrickwolf <http://github.com/patrickwolf>`_).
- Fix for tests on older versions of python.
- Sanitize authentication values before raising error.

v3.0.22 (2015 Sept 9)
=====================

- Added method :meth:`text_search` which allows an API client to access the Shotgun global search
  and auto completer.
- Added method :meth:`activity_stream_read` which allows an API client to access the activity
  stream for a given Shotgun entity.
- Added method :meth:`note_thread_read` which allows an API client to download an entire Note
  conversation, including Replies and Attachments, using a single API call.
- Added an experimental ``mockgun`` module which can be used to emulate the Shotgun API, for
  example inside unit test rigs.
- [minor] Improved docstrings.

v3.0.21 (2015 Aug 13)
=====================

- Update bundled ``httplib2`` module to latest v0.9.1 - fixes some bugs

v3.0.20 (2015 Jun 10)
=====================

- Add authentication support for Shotgun servers with two-factor authentication turned on.

v3.0.19 (2015 Mar 25)
=====================

- Add ability to authenticate with Shotgun using ``session_token``.
- Add  :meth:`get_session_token` method for obtaining token to authenticate with.
- Add new ``AuthenticationFault`` exception type to indicate when server communication has failed
  due to authentication reasons.
- Add support for ``SHOTGUN_API_CACERTS`` environment variable to provide location of external
  SSL certificates file.
- Fixes and updates to various tests.

v3.0.18 (2015 Mar 13)
=====================

- Add ability to query the per-project visibility status for entities, fields and statuses.
  (requires Shotgun server >= v5.4.4)

v3.0.17 (2014 Jul 10)
=====================

- Add ability to update ``last_accessed_by_current_user`` on Project.
- Add workaround for `bug #9291 in Python 2.7 <http://bugs.python.org/issue9291>`_ affecting
  mimetypes library on Windows.
- Add platform and Python version to user-agent (eg. ``shotgun-json (3.0.17); Python 2.7 (Mac)``)

v3.0.16 (2014 May 23)
=====================

- Add flag to ignore entities from archived Projects.
- Add support for differentiating between zero and ``None`` for number fields.
- Add ability to act as a different user.

v3.0.15 (2014 Mar 6)
====================

- Fixed bug which allowed a value of ``None`` for password parameter in
  :meth:`authenticate_human_user`
- Add :meth:`follow`, :meth:`unfollow` and :meth:`followers` methods.
- Add ability to login as HumanUser.
- Ensure that webm/mp4 mime types are always available.
- Updated link to video tour in README.
- Fixes and updates to various tests.

v3.0.14 (2013 Jun 26)
=====================

- added: additional tests for thumbnails.
- added: support for downloading from s3 in :meth:`download_attachment`. Accepts an Attachment
  entity dict as a parameter (is still backwards compatible with passing in an Attachment id).
- added: optional ``file_path`` parameter to :meth:`download_attachment` to write data directly to
  disk instead of loading into memory. (thanks to Adam Goforth `@aag <https://github.com/aag>`_)

v3.0.13 (2013 Apr 11)
=====================

- fixed: #20856 :meth:`authenticate_human_user` login was sticky and would be used for permissions
  and logging.

v3.0.12 (2013 Feb 22)
=====================
*no tag*

- added: #18171 New ``ca_certs`` argument to the :class:`Shotgun` constructor to specify the
  certificates to use in SSL validation.
- added: ``setup.py`` doesn't compress the installed ``.egg`` file which makes the
  ``cacerts.txt`` file accessible.

v3.0.11 (2013 Jan 31)
=====================

- added: nested filter syntax (see :ref:`filter_syntax`)

v3.0.10 (2013 Jan 25)
=====================

- added: :meth:`add_user_agent()` and :meth:`reset_user_agent` methods to allow client code to add
  strings to track.
- added: Changed default ``user-agent`` to include API version.
- updated: advanced summarize filter support.
- fixed: #19830 :meth:`share_thumbnail` errors when source has no thumbnail.

v3.0.9 (2012 Dec 05)
====================

- added: :meth:`share_thumbnail` method to share the same thumbnail record and media between
  entities.
- added: proxy handling to methods that transfer binary data (ie. :meth:`upload`,
  :meth:`upload_thumbnail`, etc.).
- updated: default logging level to WARN.
- updated: documentation for :meth:`summarize()` method, previously released but without
  documentation.
- fixed: unicode strings not always being encoded correctly.
- fixed: :meth:`create()` generates error when ``return_fields`` is None.
- fixed: clearing thumbnail by setting ``image`` value to ``None`` not working as expected.
- fixed: some html entities being returned sanitized via API.
- improved: ``simplejson`` fallback now uses relative imports to match other bundled packages.
- improved: various error messages are now clearer and more informative.
- installation is now ``pip`` compatible.

v3.0.9.beta2 (2012 Mar 19)
==========================

- use relative imports for included libraries when using Python v2.5 or later.
- replace sideband request for ``image`` (thumbnail) field with native support (requires Shotgun
  server >= v3.3.0. Request will still work on older versions but fallback to slow sideband
  method).
- allow setting ``image`` and ``filmstrip_thumbnail`` in data dict on :meth:`create` and
  :meth:`update` (thanks `@hughmacdonald <https://github.com/HughMacdonald>`_).
- fixed bug causing ``Attachment.tag_list`` to be set to ``"None"`` (str) for uploads.

v3.0.9.beta1 (2012 Feb 23)
==========================

- added support for access to WorkDayRules (requires Shotgun server >= v3.2.0).
- added support for filmstrip thumbnails (requires Shotgun server >= v3.1.0).
- fixed :meth:`download_attachment` pointing to incorrect url.
- fixed some issues with module import paths.

v3.0.8 (2011 Oct 7)
===================

- now uses JSON as a transport rather than XML-RPC. This provides as much as a 40% speed boost.
- added the :meth:`summarize` method.
- refactored single file into package.
- tests added (Thanks to Aaron Morton `@amorton <https://github.com/amorton>`_).
- return all strings as ascii for backwards compatibility, added ``ensure_ascii`` parameter to
  enable returning unicode.

v3.0.7 (2011 Apr 04)
====================

- fix: :meth:`update()` method should return a ``dict`` object not a ``list``.

v3.0.6 (2010 Jan 25)
====================

- optimization: don't request ``paging_info`` unless required (and server support is available).

v3.0.5 (2010 Dec 20)
====================

- officially remove support for old ``api3_preview`` controller.
- :meth:`find`: allow requesting a specific page of results instead of returning them all at once.
- add support for ``session_uuid`` parameter for communicating with a web browser session.

v3.0.4 (2010 Nov 22)
====================

- fix for issue where :meth:`create` method was returning list type instead of dictionary.
- support new style classes (thanks to Alex Schworer `@schworer <https://github.com/schworer>`_).

v3.0.3 (2010 Nov 12)
====================

- add support for local files. Injects convenience info into returned hash for local file links.
- add support for authentication through http proxy server.

v3.0.2 (2010 Aug 27)
====================

- add :meth:`revive` method to revive deleted entities.

v3.0.1 (2010 May 10)
====================

- :meth:`find`: default sorting to ascending, if not set (instead of requiring
  ascending/descending).
- :meth:`upload` and :meth:`upload_thumbnail`: pass auth info through.

v3.0 (2010 May 5)
=================

- non-beta!
- add :meth:`batch` method to do multiple :meth:`create`, :meth:`update`, and :meth:`delete`
  operations in one request to the server (requires Shotgun server to be v1.13.0 or higher).

v3.0b8 (2010 Feb 19)
====================

- fix python gotcha about using lists / dictionaries as defaults (`see this page for more info <http://www.ferg.org/projects/python_gotchas.html#contents_item_6>`_).
- add :meth:`schema_read` method.

v3.0b7 (2009 Nov 30)
====================

- add additional retries for connection errors and a catch for broken pipe exceptions.

v3.0b6 (2009 Oct 20)
====================

- add support for ``HTTP/1.1 keepalive``, which greatly improves performance for multiple
  requests.
- add more helpful error if server entered is not ``http`` or ``https``
- add support assigning tags to file uploads (for Shotgun version >= 1.10.6).

v3.0b5 (2009 Sept 29)
=====================

- fixed deprecation warnings to raise ``Exception`` class for python 2.5.

v3.0b4 (2009 July 3)
====================

- made :meth:`upload` and :meth:`upload_thumbnail` methods more backwards compatible.
- changes to :meth:`find_one`: now defaults to no ``filter_operator``.

v3.0b3 (2009 June 24)
=====================

- fixed :meth:`upload` and :meth:`upload_thumbnail` methods.
- added :meth:`download_attachment` method.
- added ``schema_*`` methods for accessing entities and fields.
- added support for http proxy servers.
- added ``__version__`` string.
- removed ``RECORDS_PER_PAGE`` global (can just set ``records_per_page`` on the Shotgun object
  after initializing it).
- removed ``api_ver`` from the constructor, as this class is only designed to work with API v3.
