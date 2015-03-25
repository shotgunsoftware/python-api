# Shotgun Python API

Shotgun provides a simple Python-based API for accessing Shotgun and integrating with other tools. This is the official API that is maintained by Shotgun Software (support@shotgunsoftware.com)

The latest version can always be found at http://github.com/shotgunsoftware/python-api

## Minimum Requirements

* Shotgun server v2.4.12 or higher. (Earlier builds of 2.4 will work, but have buggy support for float field types)
* Python v2.4 - v2.7.

## High Performance Requirements

* For Python 2.4 and 2.5, install simplejson 2.0.9: http://pypi.python.org/pypi/simplejson/2.0.9
* For Python 2.6 and higher, install simplejson 2.1.6: http://pypi.python.org/pypi/simplejson/2.1.6

## Installing
To use Shotgun's Python API module, you need to place the package shotgun_api3 in one of the directories specified by the environment variable PYTHONPATH. For more information on PYTHONPATH and using modules in Python, see http://docs.python.org/tutorial/modules.html

### Installing with `pip`
 
#### Master 
If you wish to install the current master, use the following command (Note that master contains the latest revisions and is largely considered "stable" but it is not an official packaged release. If you want the latest packaged release, use the latest tag number):  
`pip install git+git://github.com/shotgunsoftware/python-api.git`

#### Specific Versions 
To install a specific version of the package with `pip` (recommended), run the following command 
(This example installs the v3.0.9 tag. Replace the version tag with the one you want):  
`pip install git+git://github.com/shotgunsoftware/python-api.git@v3.0.9`

#### requirements.txt
If you're using pip with `requirements.txt`, add the following line:  
`git+git://github.com/shotgunsoftware/python-api.git`

## Documentation
Tutorials and detailed documentation about the Python API are available on the [Python API Wiki](https://github.com/shotgunsoftware/python-api/wiki). There is also some additional related documentation on the [Shotgun Support Website](https://support.shotgunsoftware.com/forums/48807-developer-api-info).
Some useful direct links in each are below:

* [Introduction and Video Tour](https://www.youtube.com/watch?v=QdL5E9XbdJQ)
* [Reference: Methods](https://github.com/shotgunsoftware/python-api/wiki/Reference%3A-Methods)
* [Reference: Data Types](https://github.com/shotgunsoftware/python-api/wiki/Reference%3A-Data-Types)
* [Reference: Filter Syntax](https://github.com/shotgunsoftware/python-api/wiki/Reference%3A-Filter-Syntax)

## Tests 

Integration and unit tests are provided. 

[![Build Status](https://secure.travis-ci.org/shotgunsoftware/python-api.png?branch=master)](http://travis-ci.org/shotgunsoftware/python-api)

- test_client and tests_unit mock server interaction and do not require a shotgun instance to be available.
- test_api and test_api_long do require a shotgun instance, with a script key available for the tests. These tests rely on a tests/config file, which can be created by renaming example_config and supplying the server and script user values. The tests will set up test data on the server based on the data set forth in the config. This data will be manipulated by the tests, and should not be used for other purposes.
- To run all of the tests, use the shell script run-tests. This script require nose to be installed.

## Changelog

**v3.0.19 - 2015 Mar 25**

   + Add ability to authenticate with Shotgun using `session_token`.
   + Add  `get_session_token()` method for obtaining token to authenticate with.
   + Add new `AuthenticationFault` exception type to indicate when server communication has failed due to authentication reasons.
   + Add support for `SHOTGUN_API_CACERTS` environment variable to provide location of external SSL certificates file.
   + Fixes and updates to various tests

**v3.0.18 - 2015 Mar 13**

   + Add ability to query the per-project visibility status for entities, fields and statuses. (requires Shotgun server >= v5.4.4)

**v3.0.17 - 2014 Jul 10**

   + Add ability to update last_accessed_by_current_user on Project.
   + Add workaround for bug in Python 2.7 mimetypes library on Windows (http://bugs.python.org/issue9291)
   + Add platform and Python version to user-agent (eg. "shotgun-json (3.0.17); Python 2.7 (Mac)")

**v3.0.16 - 2014 May 23**

   + Add flag to ignore entities from archived projects.
   + Add support for differentiating between zero and None for number fields.
   + Add ability to act as a different user.

**v3.0.15 - 2014 Mar 6**

   + Fixed bug which allowed a value of None for password parameter in authenticate_human_user
   + Add  follow, unfollow and followers methods
   + Add ability to login as human user
   + Ensure that webm/mp4 mime types are always available
   + Updated link to video tour in README
   + Fixes and updates to various tests

**v3.0.14 - 2013 Jun 26**

  + added: additional tests for thumbnails
  + added: support for downloading from s3 in download_attachment(). Accepts an Attachment entity dict as a parameter (is still backwards compatible with passing in an Attachment id). 
  + added: optional file_path parameter to download_attachment() to write data directly to disk instead of loading into memory. (thanks to Adam Goforth https://github.com/aag)

**v3.0.13 - 2013 Apr 11**

  + fixed: #20856 authenticate_human_user login was sticky and would be used for permissions and logging

**v3.0.12 - 2013 Feb 22** (no tag)

  + added: #18171 New ca_certs argument to the Shotgun() constructor to specify the certificates to use in SSL validation
  + added: setup.py doesn't compress the installed .egg file which makes the cacerts.txt file accessible

**v3.0.11 - 2013 Jan 31**

  + added: nested filter syntax, see https://github.com/shotgunsoftware/python-api/wiki/Reference%3A-Filter-Syntax

**v3.0.10 - 2013 Jan 25**

  + added: add_user_agent() and reset_user_agent methods to allow client code to add strings to track.
  + added: Changed default user-agent to include api version. 
  + updated: advanced summarize filter support.
  + fixed: #19830 share_thumbnail() errors when source has no thumbnail.

**v3.0.9 - 2012 Dec 05**

  + added: share_thumbnail() method to share the same thumbnail record and media between entities
  + added: proxy handling to methods that transfer binary data (ie. upload, upload_thumbnail, etc.)
  + updated: default logging level to WARN
  + updated: documentation for summarize() method, previously released but without documentation
  + fixed: unicode strings not always being encoded correctly
  + fixed: create() generates error when return_fields is None
  + fixed: clearing thumbnail by setting 'image' value to None not working as expected
  + fixed: some html entities being returned sanitized via API.
  + improved: simplejson fallback now uses relative imports to match other bundled packages
  + improved: various error messages are now clearer and more informative
  + installation is now pip compatible

**v3.0.9.beta2 - 2012 Mar 19**

  + use relative imports for included libraries when using Python v2.5 or later
  + replace sideband request for 'image' (thumbnail) field with native support (requires Shotgun server >= v3.3.0. Request will still work on older versions but fallback to slow sideband method)
  + allow setting image and filmstrip_thumbnail in data dict on create() and update() (thanks to Hugh Macdonald https://github.com/HughMacdonald)
  + fixed bug causing Attachment.tag_list to be set to "None" (str) for uploads

**v3.0.9.beta1 - 2012 Feb 23**

  + added support for access to WorkDayRules (requires Shotgun server >= v3.2.0)
  + added support for filmstrip thumbnails (requires Shotgun server >= v3.1.0)
  + fixed download_attachment() pointing to incorrect url
  + fixed some issues with module import paths

**v3.0.8 - 2011 Oct 7**

  + now uses JSON as a transport rather than XML-RPC. This provides as much as a 40% speed boost
  + added the summarize method
  + refactored single file into package
  + tests added (Thanks to Aaron Morton https://github.com/amorton)
  + return all strings as ascii for backwards compatibility, added ensure_ascii parameter to enable returning unicode

**v3.0.7 - 2011 Apr 04**

  + fix: update() method should return a dict object not a list

**v3.0.6 - 2010 Jan 25**

  + optimization: don't request paging_info unless required (and server support is available)

**v3.0.5 - 2010 Dec 20**

  + officially remove support for old api3_preview controller
  + find(): allow requesting a specific page of results instead of returning them all at once
  + add support for "session_uuid" parameter for communicating with a web browser session.

**v3.0.4 - 2010 Nov 22**

  + fix for issue where create() method was returning list type instead of dictionary
  + support new style classes (thanks to Alex Schworer https://github.com/schworer)

**v3.0.3 - 2010 Nov 12**

  + add support for local files. Injects convenience info into returned hash for local file links
  + add support for authentication through http proxy server

**v3.0.2 - 2010 Aug 27**

  + add revive() method to revive deleted entities

**v3.0.1 - 2010 May 10**

  + find(): default sorting to ascending, if not set (instead of requiring ascending/descending)
  + upload() and upload_thumbnail(): pass auth info through

**v3.0 - 2010 May 5**

  + non-beta!
  + add batch() method to do multiple create, update, and delete requests in one
      request to the server (requires Shotgun server to be v1.13.0 or higher)

**v3.0b8 - 2010 February 19**

  + fix python gotcha about using lists / dictionaries as defaults.
      See: http://www.ferg.org/projects/python_gotchas.html#contents_item_6
  + add schema_read method

**v3.0b7 - 2009 November 30**

  + add additional retries for connection errors and a catch for broken pipe exceptions

**v3.0b6 - 2009 October 20**

  + add support for HTTP/1.1 keepalive, which greatly improves performance for multiple requests
  + add more helpful error if server entered is not http or https
  + add support assigning tags to file uploads (for Shotgun version >= 1.10.6)

**v3.0b5 - 2009 Sept 29**

  + fixed deprecation warnings to raise Exception class for python 2.5

**v3.0b4 - 2009 July 3**

  + made upload() and upload_thumbnail() methods more backwards compatible
  + changes to find_one():
    + now defaults to no filter_operator

**v3.0b3 - 2009 June 24**

  + fixed upload() and upload_thumbnail() methods
  + added download_attchment() method
  + added schema_* methods for accessing entities and fields
  + added support for http proxy servers
  + added __version__ string
  + removed RECORDS_PER_PAGE global (can just set records_per_page on the Shotgun object after initializing it)
  + removed api_ver from the constructor, as this class is only designed to work with api v3


