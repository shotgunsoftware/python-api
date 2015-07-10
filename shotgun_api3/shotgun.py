#!/usr/bin/env python
'''
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2015, Shotgun Software Inc

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

  - Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

  - Neither the name of the Shotgun Software Inc nor the names of its
    contributors may be used to endorse or promote products derived from this
    software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


import base64
import cookielib    # used for attachment upload
import cStringIO    # used for attachment upload
import datetime
import logging
import mimetools    # used for attachment upload
import os
import re
import copy
import stat         # used for attachment upload
import sys
import time
import types
import urllib
import urllib2      # used for image upload
import urlparse
import shutil       # used for attachment download

# use relative import for versions >=2.5 and package import for python versions <2.5
if (sys.version_info[0] > 2) or (sys.version_info[0] == 2 and sys.version_info[1] >= 6):
    from sg_26 import *
elif (sys.version_info[0] > 2) or (sys.version_info[0] == 2 and sys.version_info[1] >= 5):
    from sg_25 import *
else:
    from sg_24 import *

# mimetypes imported in version specific imports
mimetypes.add_type('video/webm','.webm') # webm and mp4 seem to be missing
mimetypes.add_type('video/mp4', '.mp4')  # from some OS/distros

LOG = logging.getLogger("shotgun_api3")
LOG.setLevel(logging.WARN)


SG_TIMEZONE = SgTimezone()


try:
    import ssl
    NO_SSL_VALIDATION = False
except ImportError:
    LOG.debug("ssl not found, disabling certificate validation")
    NO_SSL_VALIDATION = True

# ----------------------------------------------------------------------------
# Version
__version__ = "3.0.21.dev"

# ----------------------------------------------------------------------------
# Errors

class ShotgunError(Exception):
    """Base for all Shotgun API Errors"""
    pass

class ShotgunFileDownloadError(ShotgunError):
    """Exception for file download-related errors"""
    pass

class Fault(ShotgunError):
    """Exception when server side exception detected."""
    pass

class AuthenticationFault(Fault):
    """Exception when the server side reports an error related to authentication"""
    pass

class MissingTwoFactorAuthenticationFault(Fault):
    """Exception when the server side reports an error related to missing
    two factor authentication credentials
    """
    pass

# ----------------------------------------------------------------------------
# API

class ServerCapabilities(object):
    """Container for the servers capabilities, such as version and paging.
    """

    def __init__(self, host, meta):
        """ServerCapabilities.__init__

        :param host: Host name for the server excluding protocol.

        :param meta: dict of meta data for the server returned from the
        info api method.
        """
        #Server host name
        self.host = host
        self.server_info = meta

        #Version from server is major.minor.rev or major.minor.rev."Dev"
        #Store version as triple and check dev flag
        try:
            self.version = meta.get("version", None)
        except AttributeError:
            self.version = None
        if not self.version:
            raise ShotgunError("The Shotgun Server didn't respond with a version number. "
                               "This may be because you are running an older version of "
                               "Shotgun against a more recent version of the Shotgun API. "
                               "For more information, please contact Shotgun Support.")

        if len(self.version) > 3 and self.version[3] == "Dev":
            self.is_dev = True
        else:
            self.is_dev = False

        self.version = tuple(self.version[:3])
        self._ensure_json_supported()


    def _ensure_support(self, feature, raise_hell=True):
        """Checks the server version supports a given feature, raises an
        exception if it does not.

        :param feature: dict supported version and human label { 'version': (int, int, int), 'label': str }

        :raises ShotgunError: The current server version does not [feature]
        """

        if not self.version or self.version < feature['version']:
            if raise_hell:
                raise ShotgunError(
                    "%s requires server version %s or higher, "\
                    "server is %s" % (feature['label'], _version_str(feature['version']), _version_str(self.version))
                )
            return False
        else:
            return True


    def _ensure_json_supported(self):
        """Wrapper for ensure_support"""
        self._ensure_support({
            'version': (2, 4, 0),
            'label': 'JSON API'
        })

    def ensure_include_archived_projects(self):
        """Wrapper for ensure_support"""
        self._ensure_support({
            'version': (5, 3, 14),
            'label': 'include_archived_projects parameter'
        })

    def ensure_per_project_customization(self):
        """Wrapper for ensure_support"""
        return self._ensure_support({
            'version': (5, 4, 4),
            'label': 'project parameter'
        }, True)


    def __str__(self):
        return "ServerCapabilities: host %s, version %s, is_dev %s"\
                 % (self.host, self.version, self.is_dev)

class ClientCapabilities(object):
    """Container for the client capabilities.

    Detects the current client platform and works out the SG field
    used for local data paths.
    """

    def __init__(self):
        system = sys.platform.lower()

        if system == 'darwin':
            self.platform = "mac"
        elif system.startswith('linux'):
            self.platform = 'linux'
        elif system == 'win32':
            self.platform = 'windows'
        else:
            self.platform = None

        if self.platform:
            self.local_path_field = "local_path_%s" % (self.platform)
        else:
            self.local_path_field = None

        self.py_version = ".".join(str(x) for x in sys.version_info[:2])

    def __str__(self):
        return "ClientCapabilities: platform %s, local_path_field %s, "\
            "py_verison %s" % (self.platform, self.local_path_field,
            self.py_version)

class _Config(object):
    """Container for the client configuration."""

    def __init__(self):
        self.max_rpc_attempts = 3
        # From http://docs.python.org/2.6/library/httplib.html:
        # If the optional timeout parameter is given, blocking operations 
        # (like connection attempts) will timeout after that many seconds 
        # (if it is not given, the global default timeout setting is used)
        self.timeout_secs = None
        self.api_ver = 'api3'
        self.convert_datetimes_to_utc = True
        self.records_per_page = 500
        self.api_key = None
        self.script_name = None
        self.user_login = None
        self.user_password = None
        self.auth_token = None
        self.sudo_as_login = None
        # uuid as a string
        self.session_uuid = None
        self.scheme = None
        self.server = None
        self.api_path = None
        # The raw_http_proxy reflects the exact string passed in 
        # to the Shotgun constructor. This can be useful if you 
        # need to construct a Shotgun API instance based on 
        # another Shotgun API instance.
        self.raw_http_proxy = None
        # if a proxy server is being used, the proxy_handler
        # below will contain a urllib2.ProxyHandler instance
        # which can be used whenever a request needs to be made.
        self.proxy_handler = None
        self.proxy_server = None
        self.proxy_port = 8080
        self.proxy_user = None
        self.proxy_pass = None
        self.session_token = None
        self.authorization = None
        self.no_ssl_validation = False


class Shotgun(object):
    """Shotgun Client Connection"""

    # reg ex from
    # http://underground.infovark.com/2008/07/22/iso-date-validation-regex/
    # Note a length check is done before checking the reg ex
    _DATE_PATTERN = re.compile(
        "^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])$")
    _DATE_TIME_PATTERN = re.compile(
        "^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])"\
        "(\D?([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?)?$")

    def __init__(self,
                 base_url,
                 script_name=None,
                 api_key=None,
                 convert_datetimes_to_utc=True,
                 http_proxy=None,
                 ensure_ascii=True,
                 connect=True,
                 ca_certs=None,
                 login=None,
                 password=None,
                 sudo_as_login=None,
                 session_token=None,
                 auth_token=None):
        """Initialises a new instance of the Shotgun client.

        :param base_url: http or https url to the shotgun server.

        :param script_name: name of the client script, used to authenticate
        to the server. If script_name is provided, then api_key must be as
        well and neither login nor password can be provided.

        :param api_key: key assigned to the client script, used to
        authenticate to the server.  If api_key is provided, then script_name
        must be as well and neither login nor password can be provided.

        :param convert_datetimes_to_utc: If True date time values are
        converted from local time to UTC time before been sent to the server.
        Datetimes received from the server are converted back to local time.
        If False the client should use UTC date time values.
        Default is True.

        :param http_proxy: Optional, URL for the http proxy server, on the
        form [username:pass@]proxy.com[:8080]

        :param connect: If True, connect to the server. Only used for testing.
        
        :param ca_certs: Optional path to an external SSL certificates file. By 
        default, the Shotgun API will use its own built-in certificates file
        which stores root certificates for the most common Certificate 
        Authorities (CAs). If you are using a corporate or internal CA, or are
        packaging an application into an executeable, it may be necessary to 
        point to your own certificates file. You can do this by passing in the 
        full path to the file via this parameter or by setting the environment 
        variable `SHOTGUN_API_CACERTS`. In the case both are set, this 
        parameter will take precedence. 

        :param login: The login to use to authenticate to the server. If login
        is provided, then password must be as well and neither script_name nor
        api_key can be provided.

        :param password: The password for the login to use to authenticate to
        the server. If password is provided, then login must be as well and
        neither script_name nor api_key can be provided.
        
        :param sudo_as_login: A user login string for the user whose permissions will
        be applied to all actions and who will be logged as the user performing
        all actions. Note that logged events will have an additional extra meta-data parameter 
        'sudo_actual_user' indicating the script or user that actually authenticated.
        
        :param session_token: The session token to use to authenticate to the server. This
        can be used as an alternative to authenticating with a script user or regular user.
        You retrieve the session token by running the get_session_token() method.        

        :param auth_token: The authentication token required to authenticate to
        a server with two factor authentication turned on. If auth_token is provided,
        then login and password must be as well and neither script_name nor api_key
        can be provided. Note that these tokens can be short lived so a session is
        established right away if an auth_token is provided. A
        MissingTwoFactorAuthenticationFault will be raised if the auth_token is invalid.
        """

        # verify authentication arguments
        if session_token is not None:
            if script_name is not None or api_key is not None:
                raise ValueError("cannot provide both session_token "
                                 "and script_name/api_key")
            if login is not None or password is not None:
                raise ValueError("cannot provide both session_token "
                                 "and login/password")
        
        if login is not None or password is not None:
            if script_name is not None or api_key is not None:
                raise ValueError("cannot provide both login/password "
                                 "and script_name/api_key")
            if login is None:
                raise ValueError("password provided without login")
            if password is None:
                raise ValueError("login provided without password")

        if script_name is not None or api_key is not None:
            if script_name is None:
                raise ValueError("api_key provided without script_name")
            if api_key is None:
                raise ValueError("script_name provided without api_key")

        if auth_token is not None:
            if login is None or password is None:
                raise ValueError("must provide a user login and password with an auth_token")

            if script_name is not None or api_key is not None:
                raise ValueError("cannot provide an auth_code with script_name/api_key")

        # Can't use 'all' with python 2.4
        if len([x for x in [session_token, script_name, api_key, login, password] if x]) == 0:
            if connect:
                raise ValueError("must provide login/password, session_token or script_name/api_key")

        self.config = _Config()
        self.config.api_key = api_key
        self.config.script_name = script_name
        self.config.user_login = login
        self.config.user_password = password
        self.config.auth_token = auth_token
        self.config.session_token = session_token
        self.config.sudo_as_login = sudo_as_login
        self.config.convert_datetimes_to_utc = convert_datetimes_to_utc
        self.config.no_ssl_validation = NO_SSL_VALIDATION
        self.config.raw_http_proxy = http_proxy
        self._connection = None
        if ca_certs is not None:
            self.__ca_certs = ca_certs
        else:
            self.__ca_certs = os.environ.get('SHOTGUN_API_CACERTS')

        self.base_url = (base_url or "").lower()
        self.config.scheme, self.config.server, api_base, _, _ = \
            urlparse.urlsplit(self.base_url)
        if self.config.scheme not in ("http", "https"):
            raise ValueError("base_url must use http or https got '%s'" %
                self.base_url)
        self.config.api_path = urlparse.urljoin(urlparse.urljoin(
            api_base or "/", self.config.api_ver + "/"), "json")


        # if the service contains user information strip it out
        # copied from the xmlrpclib which turned the user:password into
        # and auth header
        auth, self.config.server = urllib.splituser(self.config.server)
        if auth:
            auth = base64.encodestring(urllib.unquote(auth))
            self.config.authorization = "Basic " + auth.strip()

        # foo:bar@123.456.789.012:3456
        if http_proxy:
            # check if we're using authentication
            p = http_proxy.split("@", 1)
            if len(p) > 1:
                self.config.proxy_user, self.config.proxy_pass = \
                    p[0].split(":", 1)
                proxy_server = p[1]
            else:
                proxy_server = http_proxy
            proxy_netloc_list = proxy_server.split(":", 1)
            self.config.proxy_server = proxy_netloc_list[0]
            if len(proxy_netloc_list) > 1:
                try:
                    self.config.proxy_port = int(proxy_netloc_list[1])
                except ValueError:
                    raise ValueError("Invalid http_proxy address '%s'. Valid " \
                        "format is '123.456.789.012' or '123.456.789.012:3456'"\
                        ". If no port is specified, a default of %d will be "\
                        "used." % (http_proxy, self.config.proxy_port))

            # now populate self.config.proxy_handler
            if self.config.proxy_user and self.config.proxy_pass:
                auth_string = "%s:%s@" % (self.config.proxy_user, self.config.proxy_pass)
            else:
                auth_string = ""
            proxy_addr = "http://%s%s:%d" % (auth_string, self.config.proxy_server, self.config.proxy_port)
            self.config.proxy_handler = urllib2.ProxyHandler({self.config.scheme : proxy_addr})

        if ensure_ascii:
            self._json_loads = self._json_loads_ascii

        self.client_caps = ClientCapabilities()
        # this relies on self.client_caps being set first 
        self.reset_user_agent()

        self._server_caps = None
        # test to ensure the the server supports the json API
        # call to server will only be made once and will raise error
        if connect:
            self.server_caps

        # When using auth_token in a 2FA scenario we need to switch to session-based
        # authentication because the auth token will no longer be valid after a first use.
        if self.config.auth_token is not None:
            self.config.session_token = self.get_session_token()
            self.config.user_login = None
            self.config.user_password = None
            self.config.auth_token = None


    # ========================================================================
    # API Functions

    @property
    def server_info(self):
        """Returns server information."""
        return self.server_caps.server_info

    @property
    def server_caps(self):
        """
        :returns: ServerCapabilities that describe the server the client is
        connected to.
        """
        if not self._server_caps or (
            self._server_caps.host != self.config.server):
            self._server_caps = ServerCapabilities(self.config.server,
                self.info())
        return self._server_caps

    def connect(self):
        """Forces the client to connect to the server if it is not already
        connected.

        NOTE: The client will automatically connect to the server. Only
        call this function if you wish to confirm the client can connect.
        """
        self._get_connection()
        self.info()
        return

    def close(self):
        """Closes the current connection to the server.

        If the client needs to connect again it will do so automatically.
        """
        self._close_connection()
        return

    def info(self):
        """Calls the Info function on the Shotgun API to get the server meta.

        :returns: dict of the server meta data.
        """
        return self._call_rpc("info", None, include_auth_params=False)

    def find_one(self, entity_type, filters, fields=None, order=None,
        filter_operator=None, retired_only=False, include_archived_projects=True):
        """Calls the find() method and returns the first result, or None.

        :param entity_type: Required, entity type (string) to find.

        :param filters: Required, list of filters to apply.

        :param fields: Optional list of fields from the matched entities to
        return. Defaults to id.

        :param order: Optional list of fields to order the results by, list
        has the form [{'field_name':'foo','direction':'asc or desc'},]

        :param filter_operator: Optional operator to apply to the filters,
        supported values are 'all' and 'any'. Defaults to 'all'.

        :param limit: Optional, number of entities to return per page.
        Defaults to 0 which returns all entities that match.

        :param page: Optional, page of results to return. By default all
        results are returned. Use together with limit.

        :param retired_only: Optional, flag to return only entities that have
        been retried. Defaults to False which returns only entities which
        have not been retired.
        """

        results = self.find(entity_type, filters, fields, order,
            filter_operator, 1, retired_only, include_archived_projects=include_archived_projects)

        if results:
            return results[0]
        return None

    def find(self, entity_type, filters, fields=None, order=None,
            filter_operator=None, limit=0, retired_only=False, page=0,
            include_archived_projects=True):
        """Find entities matching the given filters.

        :param entity_type: Required, entity type (string) to find.

        :param filters: Required, list of filters to apply.

        :param fields: Optional list of fields from the matched entities to
        return. Defaults to id.

        :param order: Optional list of fields to order the results by, list
        has the form [{'field_name':'foo','direction':'asc or desc'},]

        :param filter_operator: Optional operator to apply to the filters,
        supported values are 'all' and 'any'. Defaults to 'all'.

        :param limit: Optional, number of entities to return per page.
        Defaults to 0 which returns all entities that match.

        :param page: Optional, page of results to return. By default all
        results are returned. Use together with limit.

        :param retired_only: Optional, flag to return only entities that have
        been retried. Defaults to False which returns only entities which
        have not been retired.

        :param include_archived_projects: Optional, flag to include entities
        whose projects have been archived

        :returns: list of the dicts for each entity with the requested fields,
        and their id and type.
        """

        if not isinstance(limit, int) or limit < 0:
            raise ValueError("limit parameter must be a positive integer")

        if not isinstance(page, int) or page < 0:
            raise ValueError("page parameter must be a positive integer")

        if isinstance(filters, (list, tuple)):
            filters = _translate_filters(filters, filter_operator)
        elif filter_operator:
            #TODO:Not sure if this test is correct, replicated from prev api
            raise ShotgunError("Deprecated: Use of filter_operator for find()"
                " is not valid any more. See the documentation on find()")

        if not include_archived_projects:
            # This defaults to True on the server (no argument is sent)
            # So we only need to check the server version if it is False
            self.server_caps.ensure_include_archived_projects()


        params = self._construct_read_parameters(entity_type,
                                                 fields,
                                                 filters,
                                                 retired_only,
                                                 order,
                                                 include_archived_projects)

        if limit and limit <= self.config.records_per_page:
            params["paging"]["entities_per_page"] = limit
            # If page isn't set and the limit doesn't require pagination,
            # then trigger the faster code path.
            if page == 0:
                page = 1

        if self.server_caps.version and self.server_caps.version >= (3, 3, 0):
            params['api_return_image_urls'] = True

        # if page is specified, then only return the page of records requested
        if page != 0:
            # No paging_info needed, so optimize it out.
            params["return_paging_info"] = False
            params["paging"]["current_page"] = page
            records = self._call_rpc("read", params).get("entities", [])
            return self._parse_records(records)

        records = []
        result = self._call_rpc("read", params)
        while result.get("entities"):
            records.extend(result.get("entities"))

            if limit and len(records) >= limit:
                records = records[:limit]
                break
            if len(records) == result["paging_info"]["entity_count"]:
                break

            params['paging']['current_page'] += 1
            result = self._call_rpc("read", params)

        return self._parse_records(records)



    def _construct_read_parameters(self,
                                   entity_type,
                                   fields,
                                   filters,
                                   retired_only,
                                   order,
                                   include_archived_projects):
        params = {}
        params["type"] = entity_type
        params["return_fields"] = fields or ["id"]
        params["filters"] = filters
        params["return_only"] = (retired_only and 'retired') or "active"
        params["return_paging_info"] = True
        params["paging"] = { "entities_per_page": self.config.records_per_page,
                             "current_page": 1 }

        if include_archived_projects is False:
            # Defaults to True on the server, so only pass it if it's False
            params["include_archived_projects"] = False

        if order:
            sort_list = []
            for sort in order:
                if sort.has_key('column'):
                    # TODO: warn about deprecation of 'column' param name
                    sort['field_name'] = sort['column']
                sort.setdefault("direction", "asc")
                sort_list.append({
                    'field_name': sort['field_name'],
                    'direction' : sort['direction']
                })
            params['sorts'] = sort_list
        return params


    def _add_project_param(self, params, project_entity):

        if project_entity and self.server_caps.ensure_per_project_customization():
            params["project"] = project_entity

        return params


    def summarize(self,
                  entity_type,
                  filters,
                  summary_fields,
                  filter_operator=None,
                  grouping=None,
                  include_archived_projects=True):
        """
        Return group and summary information for entity_type for summary_fields
        based on the given filters.
        """

        if not isinstance(grouping, list) and grouping is not None:
            msg = "summarize() 'grouping' parameter must be a list or None"
            raise ValueError(msg)

        if isinstance(filters, (list, tuple)):
            filters = _translate_filters(filters, filter_operator)

        if not include_archived_projects:
            # This defaults to True on the server (no argument is sent)
            # So we only need to check the server version if it is False
            self.server_caps.ensure_include_archived_projects()

        params = {"type": entity_type,
                  "summaries": summary_fields,
                  "filters": filters}

        if include_archived_projects is False:
            # Defaults to True on the server, so only pass it if it's False
            params["include_archived_projects"] = False

        if grouping is not None:
            params['grouping'] = grouping

        records = self._call_rpc('summarize', params)
        return records

    def create(self, entity_type, data, return_fields=None):
        """Create a new entity of the specified entity_type.

        :param entity_type: Required, entity type (string) to create.

        :param data: Required, dict fields to set on the new entity.

        :param return_fields: Optional list of fields from the new entity
        to return. Defaults to 'id' field.

        :returns: dict of the requested fields.
        """

        data = data.copy()
        if not return_fields:
            return_fields = ["id"]

        upload_image = None
        if 'image' in data:
            upload_image = data.pop('image')

        upload_filmstrip_image = None
        if 'filmstrip_image' in data:
            if not self.server_caps.version or self.server_caps.version < (3, 1, 0):
                raise ShotgunError("Filmstrip thumbnail support requires server version 3.1 or "\
                    "higher, server is %s" % (self.server_caps.version,))
            upload_filmstrip_image = data.pop('filmstrip_image')

        params = {
            "type" : entity_type,
            "fields" : self._dict_to_list(data),
            "return_fields" : return_fields
        }

        record = self._call_rpc("create", params, first=True)
        result = self._parse_records(record)[0]

        if upload_image:
            image_id = self.upload_thumbnail(entity_type, result['id'],
                                             upload_image)
            image = self.find_one(entity_type, [['id', 'is', result.get('id')]],
                                  fields=['image'])
            result['image'] = image.get('image')

        if upload_filmstrip_image:
            filmstrip_id = self.upload_filmstrip_thumbnail(entity_type, result['id'], upload_filmstrip_image)
            filmstrip = self.find_one(entity_type,
                                     [['id', 'is', result.get('id')]],
                                     fields=['filmstrip_image'])
            result['filmstrip_image'] = filmstrip.get('filmstrip_image')

        return result

    def update(self, entity_type, entity_id, data):
        """Updates the specified entity with the supplied data.

        :param entity_type: Required, entity type (string) to update.

        :param entity_id: Required, id of the entity to update.

        :param data: Required, dict fields to update on the entity.

        :returns: dict of the fields updated, with the entity_type and
        id added.
        """

        data = data.copy()
        upload_image = None
        if 'image' in data and data['image'] is not None:
            upload_image = data.pop('image')
        upload_filmstrip_image = None
        if 'filmstrip_image' in data:
            if not self.server_caps.version or self.server_caps.version < (3, 1, 0):
                raise ShotgunError("Filmstrip thumbnail support requires server version 3.1 or "\
                    "higher, server is %s" % (self.server_caps.version,))
            upload_filmstrip_image = data.pop('filmstrip_image')

        if data:
            params = {
                "type" : entity_type,
                "id" : entity_id,
                "fields" : self._dict_to_list(data)
            }
            record = self._call_rpc("update", params)
            result = self._parse_records(record)[0]
        else:
            result = {'id': entity_id, 'type': entity_type}

        if upload_image:
            image_id = self.upload_thumbnail(entity_type, entity_id,
                                             upload_image)
            image = self.find_one(entity_type, [['id', 'is', result.get('id')]],
                                  fields=['image'])
            result['image'] = image.get('image')

        if upload_filmstrip_image:
            filmstrip_id = self.upload_filmstrip_thumbnail(entity_type, result['id'], upload_filmstrip_image)
            filmstrip = self.find_one(entity_type,
                                     [['id', 'is', result.get('id')]],
                                     fields=['filmstrip_image'])
            result['filmstrip_image'] = filmstrip.get('filmstrip_image')

        return result

    def delete(self, entity_type, entity_id):
        """Retire the specified entity.

        The entity can be brought back to life using the revive function.

        :param entity_type: Required, entity type (string) to delete.

        :param entity_id: Required, id of the entity to delete.

        :returns: True if the entity was deleted, False otherwise e.g. if the
        entity has previously been deleted.
        """

        params = {
            "type" : entity_type,
            "id" : entity_id
        }

        return self._call_rpc("delete", params)

    def revive(self, entity_type, entity_id):
        """Revive an entity that has previously been deleted.

        :param entity_type: Required, entity type (string) to revive.

        :param entity_id: Required, id of the entity to revive.

        :returns: True if the entity was revived, False otherwise e.g. if the
        entity has previously been revived (or was not deleted).
        """

        params = {
            "type" : entity_type,
            "id" : entity_id
        }

        return self._call_rpc("revive", params)

    def batch(self, requests):
        """Make a batch request  of several create, update and delete calls.

        All requests are performed within a transaction, so either all will
        complete or none will.

        :param requests: A list of dict's of the form which have a
            request_type key and also specifies:
            - create: entity_type, data dict of fields to set
            - update: entity_type, entity_id, data dict of fields to set
            - delete: entity_type and entity_id

        :returns: A list of values for each operation, create and update
        requests return a dict of the fields updated. Delete requests
        return True if the entity was deleted.
        """

        if not isinstance(requests, list):
            raise ShotgunError("batch() expects a list.  Instead was sent "\
                "a %s" % type(requests))

        # If we have no requests, just return an empty list immediately.
        # Nothing to process means nothing to get results of.
        if len(requests) == 0:
            return []

        calls = []

        def _required_keys(message, required_keys, data):
            missing = set(required_keys) - set(data.keys())
            if missing:
                raise ShotgunError("%s missing required key: %s. "\
                    "Value was: %s." % (message, ", ".join(missing), data))

        for req in requests:
            _required_keys("Batched request",
                           ['request_type', 'entity_type'],
                           req)
            request_params = {'request_type': req['request_type'],
                              "type" : req["entity_type"]}

            if req["request_type"] == "create":
                _required_keys("Batched create request", ['data'], req)
                request_params['fields'] = self._dict_to_list(req["data"])
                request_params["return_fields"] = req.get("return_fields") or["id"]
            elif req["request_type"] == "update":
                _required_keys("Batched update request",
                               ['entity_id', 'data'],
                               req)
                request_params['id'] = req['entity_id']
                request_params['fields'] = self._dict_to_list(req["data"])
            elif req["request_type"] == "delete":
                _required_keys("Batched delete request", ['entity_id'], req)
                request_params['id'] = req['entity_id']
            else:
                raise ShotgunError("Invalid request_type '%s' for batch" % (
                                   req["request_type"]))
            calls.append(request_params)
        records = self._call_rpc("batch", calls)
        return self._parse_records(records)

    def work_schedule_read(self, start_date, end_date, project=None, user=None):
        """Get the work day rules for a given date range.

        reasons:
            STUDIO_WORK_WEEK
            STUDIO_EXCEPTION
            PROJECT_WORK_WEEK
            PROJECT_EXCEPTION
            USER_WORK_WEEK
            USER_EXCEPTION


        :param start_date: Start date of date range.
        :type start_date: str (YYYY-MM-DD)
        :param end_date: End date of date range.
        :type end_date: str (YYYY-MM-DD)
        :param dict project: Project entity to query WorkDayRules for. (optional)
        :param dict user: User entity to query WorkDayRules for. (optional)
        """

        if not self.server_caps.version or self.server_caps.version < (3, 2, 0):
            raise ShotgunError("Work schedule support requires server version 3.2 or "\
                "higher, server is %s" % (self.server_caps.version,))

        if not isinstance(start_date, str) or not isinstance(end_date, str):
            raise ShotgunError("The start_date and end_date arguments must be strings in YYYY-MM-DD format")

        params = dict(
            start_date=start_date,
            end_date=end_date,
            project=project,
            user=user
        )

        return self._call_rpc('work_schedule_read', params)

    def work_schedule_update(self, date, working, description=None, project=None, user=None, recalculate_field=None):
        """Update the work schedule for a given date. If neither project nor user are passed the studio work schedule will be updated.
        Project and User can only be used separately.

        :param date: Date of WorkDayRule to update.
        :type date: str (YYYY-MM-DD)
        :param bool working:
        :param str description: Reason for time off. (optional)
        :param dict project: Project entity to assign to. Cannot be used with user. (optional)
        :param dict user: User entity to assign to. Cannot be used with project. (optional)
        :param str recalculate_field: Choose the schedule field that will be recalculated on Tasks when they are affected by a change in working schedule. 'due_date' or 'duration', default is a Site Preference (optional)
        """

        if not self.server_caps.version or self.server_caps.version < (3, 2, 0):
            raise ShotgunError("Work schedule support requires server version 3.2 or "\
                "higher, server is %s" % (self.server_caps.version,))

        if not isinstance(date, str):
            raise ShotgunError("The date argument must be string in YYYY-MM-DD format")

        params = dict(
            date=date,
            working=working,
            description=description,
            project=project,
            user=user,
            recalculate_field=recalculate_field
        )

        return self._call_rpc('work_schedule_update', params)

    def follow(self, user, entity):
        """Adds the entity to the user's followed entities (or does nothing if the user is already following the entity)
        
        :param dict user: User entity to follow the entity
        :param dict entity: Entity to be followed
        
        :returns: dict with 'followed'=true, and dicts for the 'user' and 'entity' that were passed in
        """

        if not self.server_caps.version or self.server_caps.version < (5, 1, 22):
            raise ShotgunError("Follow support requires server version 5.2 or "\
                "higher, server is %s" % (self.server_caps.version,))
        
        params = dict(
            user=user,
            entity=entity
        )
        
        return self._call_rpc('follow', params)

    def unfollow(self, user, entity):
        """Removes entity from the user's followed entities (or does nothing if the user is not following the entity)
        
        :param dict user: User entity to unfollow the entity
        :param dict entity: Entity to be unfollowed
        
        :returns: dict with 'unfollowed'=true, and dicts for the 'user' and 'entity' that were passed in
        """

        if not self.server_caps.version or self.server_caps.version < (5, 1, 22):
            raise ShotgunError("Follow support requires server version 5.2 or "\
                "higher, server is %s" % (self.server_caps.version,))
        
        params = dict(
            user=user,
            entity=entity
        )
        
        return self._call_rpc('unfollow', params)

    def followers(self, entity):
        """Gets all followers of the entity.
        
        :param dict entity: Find all followers of this entity
        
        :returns list of dicts for all the users following the entity
        """

        if not self.server_caps.version or self.server_caps.version < (5, 1, 22):
            raise ShotgunError("Follow support requires server version 5.2 or "\
                "higher, server is %s" % (self.server_caps.version,))
        
        params = dict(
            entity=entity
        )
        
        return self._call_rpc('followers', params)

    def schema_entity_read(self, project_entity=None):
        """Gets all active entities defined in the schema.

        :param dict project_entity: Optional, if set, each field's visibility is reported accordingly
        to the specified project's current visibility settings.
        If None, all fields are reported as visible.

        :returns: dict of Entity Type to dict containing the display name.
        """

        params = {}

        params = self._add_project_param(params, project_entity)

        if params:
            return self._call_rpc("schema_entity_read", params)
        else:
            return self._call_rpc("schema_entity_read", None)

    def schema_read(self, project_entity=None):
        """Gets the schema for all fields in all entities.

        :param dict project_entity: Optional, if set, each field's visibility is reported accordingly
        to the specified project's current visibility settings.
        If None, all fields are reported as visible.

        :returns: nested dicts
        """

        params = {}

        params = self._add_project_param(params, project_entity)

        if params:
            return self._call_rpc("schema_read", params)
        else:
            return self._call_rpc("schema_read", None)

    def schema_field_read(self, entity_type, field_name=None, project_entity=None):
        """Gets all schema for fields in the specified entity_type or one
        field.

        :param entity_type: Required, entity type (string) to get the schema
        for.

        :param field_name: Optional, name of the field to get the schema
        definition for. If not supplied all fields for the entity type are
        returned.

        :param dict project_entity: Optional, if set, each field's visibility is reported accordingly
        to the specified project's current visibility settings.
        If None, all fields are reported as visible.

        :returns: dict of field name to nested dicts which describe the field
        """

        params = {
            "type": entity_type,
        }

        if field_name:
            params["field_name"] = field_name

        params = self._add_project_param(params, project_entity)

        return self._call_rpc("schema_field_read", params)

    def schema_field_create(self, entity_type, data_type, display_name,
        properties=None):
        """Creates a field for the specified entity type.

        :param entity_type: Required, entity type (string) to add the field to

        :param data_type: Required, Shotgun data type for the new field.

        :param display_name: Required, display name for the new field.

        :param properties: Optional, dict of properties for the new field.

        :returns: The Shotgun name (string) for the new field, this is
        different to the display_name passed in.
        """

        params = {
            "type" : entity_type,
            "data_type" : data_type,
            "properties" : [
                {'property_name': 'name', 'value': display_name}
            ]
        }
        params["properties"].extend(self._dict_to_list(properties,
            key_name="property_name", value_name="value"))

        return self._call_rpc("schema_field_create", params)

    def schema_field_update(self, entity_type, field_name, properties):
        """Updates the specified field definition with the supplied
        properties.

        :param entity_type: Required, entity type (string) to add the field to

        :param field_name: Required, Shotgun name of the field to update.

        :param properties: Required, dict of updated properties for the field.

        :returns: True if the field was updated, False otherwise.
        """

        params = {
            "type" : entity_type,
            "field_name" : field_name,
            "properties": [
                {"property_name" : k, "value" : v}
                for k, v in (properties or {}).iteritems()
            ]
        }

        return self._call_rpc("schema_field_update", params)

    def schema_field_delete(self, entity_type, field_name):
        """Deletes the specified field definition from the entity_type.

        :param entity_type: Required, entity type (string) to delete the field
        from.

        :param field_name: Required, Shotgun name of the field to delete.

        :param properties: Required, dict of updated properties for the field.

        :returns: True if the field was updated, False otherwise.
        """

        params = {
            "type" : entity_type,
            "field_name" : field_name
        }

        return self._call_rpc("schema_field_delete", params)

    def add_user_agent(self, agent):
        """Add agent to the user-agent header

        Append agent to the string passed in as the user-agent to be logged
        in events for this API session.

        :param agent: Required, string to append to user-agent.
        """
        self._user_agents.append(agent)

    def reset_user_agent(self):
        """Reset user agent to the default

        Eg. shotgun-json (3.0.17); Python 2.6 (Mac)
        """
        ua_platform = "Unknown"
        if self.client_caps.platform is not None:
            ua_platform = self.client_caps.platform.capitalize()
        self._user_agents = ["shotgun-json (%s)" % __version__,
                             "Python %s (%s)" % (self.client_caps.py_version, ua_platform)]

    def set_session_uuid(self, session_uuid):
        """Sets the browser session_uuid for this API session.

        Once set events generated by this API session will include the
        session_uuid in their EventLogEntries.

        :param session_uuid: Session UUID to set.
        """

        self.config.session_uuid = session_uuid
        return

    def share_thumbnail(self, entities, thumbnail_path=None, source_entity=None,
        filmstrip_thumbnail=False, **kwargs):
        if not self.server_caps.version or self.server_caps.version < (4, 0, 0):
            raise ShotgunError("Thumbnail sharing support requires server "\
                "version 4.0 or higher, server is %s" % (self.server_caps.version,))

        if not isinstance(entities, list) or len(entities) == 0:
            raise ShotgunError("'entities' parameter must be a list of entity "\
                "hashes and may not be empty")

        for e in entities:
            if not isinstance(e, dict) or 'id' not in e or 'type' not in e:
                raise ShotgunError("'entities' parameter must be a list of "\
                    "entity hashes with at least 'type' and 'id' keys.\nInvalid "\
                    "entity: %s" % e)

        if (not thumbnail_path and not source_entity) or \
            (thumbnail_path and source_entity):
            raise ShotgunError("You must supply either thumbnail_path OR "\
                "source_entity.")

        # upload thumbnail
        if thumbnail_path:
            source_entity = entities.pop(0)
            if filmstrip_thumbnail:
                thumb_id = self.upload_filmstrip_thumbnail(source_entity['type'],
                    source_entity['id'], thumbnail_path, **kwargs)
            else:
                thumb_id = self.upload_thumbnail(source_entity['type'],
                    source_entity['id'], thumbnail_path, **kwargs)
        else:
            if not isinstance(source_entity, dict) or 'id' not in source_entity \
                or 'type' not in source_entity:
                raise ShotgunError("'source_entity' parameter must be a dict "\
                    "with at least 'type' and 'id' keys.\nGot: %s (%s)" \
                    % (source_entity, type(source_entity)))

        # only 1 entity in list and we already uploaded the thumbnail to it
        if len(entities) == 0:
            return thumb_id

        # update entities with source_entity thumbnail
        entities_str = []
        for e in entities:
            entities_str.append("%s_%s" % (e['type'], e['id']))
        # format for post request
        if filmstrip_thumbnail:
            filmstrip_thumbnail = 1
        params = {
            "entities" : ','.join(entities_str),
            "source_entity": "%s_%s" % (source_entity['type'], source_entity['id']),
            "filmstrip_thumbnail" : filmstrip_thumbnail,
        }

        params.update(self._auth_params())

        # Create opener with extended form post support
        opener = self._build_opener(FormPostHandler)
        url = urlparse.urlunparse((self.config.scheme, self.config.server,
            "/upload/share_thumbnail", None, None, None))

        # Perform the request
        try:
            resp = opener.open(url, params)
            result = resp.read()
            # response headers are in str(resp.info()).splitlines()
        except urllib2.HTTPError, e:
            if e.code == 500:
                raise ShotgunError("Server encountered an internal error. "
                    "\n%s\n(%s)\n%s\n\n" % (url, params, e))
            else:
                raise ShotgunError("Unanticipated error occurred %s" % (e))
        else:
            if not str(result).startswith("1"):
                raise ShotgunError("Unable to share thumbnail: %s" % result)
            else:
                # clearing thumbnail returns no attachment_id
                try:
                    attachment_id = int(str(result).split(":")[1].split("\n")[0])
                except ValueError:
                    attachment_id = None

        return attachment_id

    def upload_thumbnail(self, entity_type, entity_id, path, **kwargs):
        """Convenience function for uploading thumbnails, see upload.
        """
        return self.upload(entity_type, entity_id, path,
            field_name="thumb_image", **kwargs)

    def upload_filmstrip_thumbnail(self, entity_type, entity_id, path, **kwargs):
        """Convenience function for uploading thumbnails, see upload.
        """
        if not self.server_caps.version or self.server_caps.version < (3, 1, 0):
            raise ShotgunError("Filmstrip thumbnail support requires server version 3.1 or "\
                "higher, server is %s" % (self.server_caps.version,))

        return self.upload(entity_type, entity_id, path,
            field_name="filmstrip_thumb_image", **kwargs)

    def upload(self, entity_type, entity_id, path, field_name=None,
        display_name=None, tag_list=None):
        """Upload a file as an attachment/thumbnail to the specified
        entity_type and entity_id.

        :param entity_type: Required, entity type (string) to revive.

        :param entity_id: Required, id of the entity to revive.

        :param path: path to file on disk

        :param field_name: the field on the entity to upload to
            (ignored if thumbnail)

        :param display_name: the display name to use for the file in the ui
            (ignored if thumbnail)

        :param tag_list: comma-separated string of tags to assign to the file

        :returns: Id of the new attachment.
        """
        path = os.path.abspath(os.path.expanduser(path or ""))
        if not os.path.isfile(path):
            raise ShotgunError("Path must be a valid file, got '%s'" % path)

        is_thumbnail = (field_name == "thumb_image" or field_name == "filmstrip_thumb_image")

        params = {
            "entity_type" : entity_type,
            "entity_id" : entity_id,
        }

        params.update(self._auth_params())

        if is_thumbnail:
            url = urlparse.urlunparse((self.config.scheme, self.config.server,
                "/upload/publish_thumbnail", None, None, None))
            params["thumb_image"] = open(path, "rb")
            if field_name == "filmstrip_thumb_image":
                params["filmstrip"] = True

        else:
            url = urlparse.urlunparse((self.config.scheme, self.config.server,
                "/upload/upload_file", None, None, None))
            if display_name is None:
                display_name = os.path.basename(path)
            # we allow linking to nothing for generic reference use cases
            if field_name is not None:
                params["field_name"] = field_name
            params["display_name"] = display_name
            # None gets converted to a string and added as a tag...
            if tag_list:
                params["tag_list"] = tag_list

            params["file"] = open(path, "rb")

        # Create opener with extended form post support
        opener = self._build_opener(FormPostHandler)

        # Perform the request
        try:
            result = opener.open(url, params).read()
        except urllib2.HTTPError, e:
            if e.code == 500:
                raise ShotgunError("Server encountered an internal error. "
                    "\n%s\n(%s)\n%s\n\n" % (url, params, e))
            else:
                raise ShotgunError("Unanticipated error occurred uploading "
                    "%s: %s" % (path, e))
        else:
            if not str(result).startswith("1"):
                raise ShotgunError("Could not upload file successfully, but "\
                    "not sure why.\nPath: %s\nUrl: %s\nError: %s" % (
                    path, url, str(result)))

        attachment_id = int(str(result).split(":")[1].split("\n")[0])
        return attachment_id

    def download_attachment(self, attachment=False, file_path=None, 
                            attachment_id=None):
        """Downloads the file associated with a Shotgun Attachment.

        NOTE: On older (< v5.1.0) Shotgun versions, non-downloadable files 
        on Shotgun don't raise exceptions, they cause a server error which 
        returns a 200 with the page content.

        :param attachment: (mixed) Usually a dict representing an Attachment.
        The dict should have a 'url' key that specifies the download url. 
        Optionally, the dict can be a standard entity hash format with 'id' and
        'type' keys as long as 'type'=='Attachment'. This is only supported for
        backwards compatibility (#22150).
        If an int value is passed in, the Attachment with the matching id will
        be downloaded from the Shotgun server.

        :param file_path: (str) Optional. If provided, write the data directly
        to local disk using the file_path. This avoids loading all of the data 
        in memory and saves the file locally which is probably what is desired
        anyway. 

        :param attachment_id: (int) Optional. Deprecated in favor of passing in 
        Attachment hash to attachment param. This attachment_id exists only for
        backwards compatibility for scripts specifying the parameter with
        keywords.

        :returns: (str) If file_path is None, returns data of the Attachment 
        file as a string. If file_path is provided, returns file_path.
        """
        # backwards compatibility when passed via keyword argument 
        if attachment is False:
            if type(attachment_id) == int:
                attachment = attachment_id
            else:
                raise TypeError("Missing parameter 'attachment'. Expected a "\
                                "dict, int, NoneType value or"\
                                "an int for parameter attachment_id")
        # write to disk
        if file_path:
            try:
                fp = open(file_path, 'wb')
            except IOError, e:
                raise IOError("Unable to write Attachment to disk using "\
                              "file_path. %s" % e) 

        url = self.get_attachment_download_url(attachment)
        if url is None:
            return None

        # We only need to set the auth cookie for downloads from Shotgun server
        if self.config.server in url:
            self.set_up_auth_cookie()
   
        try:
            request = urllib2.Request(url)
            request.add_header('user-agent', "; ".join(self._user_agents))
            req = urllib2.urlopen(request)
            if file_path:
                shutil.copyfileobj(req, fp)
            else:
                attachment = req.read()
        # 400 [sg] Attachment id doesn't exist or is a local file
        # 403 [s3] link is invalid
        except urllib2.URLError, e:
            if file_path:
                fp.close()
            err = "Failed to open %s\n%s" % (url, e)
            if hasattr(e, 'code'):
                if e.code == 400:
                    err += "\nAttachment may not exist or is a local file?"
                elif e.code == 403:
                    # Only parse the body if it is an Amazon S3 url. 
                    if url.find('s3.amazonaws.com') != -1 \
                        and e.headers['content-type'] == 'application/xml':
                        body = e.readlines()
                        if body:
                            xml = ''.join(body)
                            # Once python 2.4 support is not needed we can think about using elementtree.
                            # The doc is pretty small so this shouldn't be an issue.
                            match = re.search('<Message>(.*)</Message>', xml)
                            if match:
                                err += ' - %s' % (match.group(1))
            raise ShotgunFileDownloadError(err)
        else:
            if file_path:
                return file_path
            else:
                return attachment

    def set_up_auth_cookie(self):
        """Sets up urllib2 with a cookie for authentication on the Shotgun 
        instance.
        """
        sid = self.get_session_token()
        cj = cookielib.LWPCookieJar()
        c = cookielib.Cookie('0', '_session_id', sid, None, False,
            self.config.server, False, False, "/", True, False, None, True,
            None, None, {})
        cj.set_cookie(c)
        cookie_handler = urllib2.HTTPCookieProcessor(cj)
        opener = self._build_opener(cookie_handler)
        urllib2.install_opener(opener)

    def get_attachment_download_url(self, attachment):
        """Returns the URL for downloading provided Attachment.

        :param attachment: (mixed) If type is an int, construct url to download
        Attachment with id from Shotgun. 
        If type is a dict, and a url key is present, use that url. 
        If type is a dict, and url key is not present, check if we have
        an id and type keys and the type is 'Attachment' in which case we 
        construct url to download Attachment with id from Shotgun as if just
        the id has been passed in. 

        :todo: Support for a standard entity hash should be removed: #22150

        :returns: (str) the download URL for the Attachment or None if None was
        passed to attachment param. This avoids raising an error when results
        from a find() are passed off to a download_attachment() call.
        """
        attachment_id = None
        if isinstance(attachment, int):
            attachment_id = attachment
        elif isinstance(attachment, dict):
            try:
                url = attachment['url']
            except KeyError:
                if ('id' in attachment and 'type' in attachment and 
                    attachment['type'] == 'Attachment'):
                    attachment_id = attachment['id']
                else:
                    raise ValueError("Missing 'url' key in Attachment dict")
        elif attachment is None:
            url = None
        else:
            raise TypeError("Unable to determine download url. Expected "\
                "dict, int, or NoneType. Instead got %s" % type(attachment))

        if attachment_id: 
            url = urlparse.urlunparse((self.config.scheme, self.config.server,
                "/file_serve/attachment/%s" % urllib.quote(str(attachment_id)),
                None, None, None))
        return url

    def authenticate_human_user(self, user_login, user_password, auth_token=None):
        '''Authenticate Shotgun HumanUser. HumanUser must be an active account.
        :param user_login: Login name of Shotgun HumanUser

        :param user_password: Password for Shotgun HumanUser

        :param auth_token: One-time token required to authenticate Shotgun HumanUser
        when two factor authentication is turned on.

        :return: Dictionary of HumanUser including ID if authenticated, None if unauthorized.
        """
        '''
        if not user_login:
            raise ValueError('Please supply a username to authenticate.')

        if not user_password:
            raise ValueError('Please supply a password for the user.')

        # Override permissions on Config obj
        original_login = self.config.user_login
        original_password = self.config.user_password
        original_auth_token = self.config.auth_token

        self.config.user_login = user_login
        self.config.user_password = user_password
        self.config.auth_token = auth_token

        try:
            data = self.find_one('HumanUser', [['sg_status_list', 'is', 'act'], ['login', 'is', user_login]], ['id', 'login'], '', 'all')
            # Set back to default - There finally and except cannot be used together in python2.4
            self.config.user_login = original_login
            self.config.user_password = original_password
            self.config.auth_token = original_auth_token
            return data
        except Fault:
            # Set back to default - There finally and except cannot be used together in python2.4
            self.config.user_login = original_login
            self.config.user_password = original_password
            self.config.auth_token = original_auth_token
        except:
            # Set back to default - There finally and except cannot be used together in python2.4
            self.config.user_login = original_login
            self.config.user_password = original_password
            self.config.auth_token = original_auth_token
            raise


    def update_project_last_accessed(self, project, user=None):
        """
        Update projects last_accessed_by_current_user field.
        
        :param project - a project entity hash
        :param user - A human user entity hash. Optional if either login or sudo_as are used.

        """
        if self.server_caps.version and self.server_caps.version < (5, 3, 20):
                raise ShotgunError("update_project_last_accessed requires server version 5.3.20 or "\
                    "higher, server is %s" % (self.server_caps.version,))

        if not user:
            # Try to use sudo as user if present
            if self.config.sudo_as_login:
                user = self.find_one('HumanUser', [['login', 'is', self.config.sudo_as_login]])
            # Try to use login if present
            if self.config.user_login:
                user = self.find_one('HumanUser', [['login', 'is', self.config.user_login]])

        params = { "project_id": project['id'], }
        if user:
            params['user_id'] = user['id']

        record = self._call_rpc("update_project_last_accessed_by_current_user", params)
        result = self._parse_records(record)[0]

    def get_session_token(self):
        """
        Get the session token associated with the current session.
        If a session token has already been established, this is returned, 
        otherwise a new one is generated on the server and returned.
        
        :returns: String containing a session token
        """
        if self.config.session_token:
            return self.config.session_token

        rv = self._call_rpc("get_session_token", None)
        session_token = (rv or {}).get("session_id")
        if not session_token:
            raise RuntimeError("Could not extract session_id from %s", rv)
        self.config.session_token = session_token

        return session_token

    def _build_opener(self, handler):
        """Build urllib2 opener with appropriate proxy handler."""
        if self.config.proxy_handler:
            opener = urllib2.build_opener(self.config.proxy_handler, handler)
        else:
            opener = urllib2.build_opener(handler)
        return opener

    # Deprecated methods from old wrapper
    def schema(self, entity_type):
        raise ShotgunError("Deprecated: use schema_field_read('type':'%s') "
            "instead" % entity_type)

    def entity_types(self):
        raise ShotgunError("Deprecated: use schema_entity_read() instead")
    # ========================================================================
    # RPC Functions

    def _call_rpc(self, method, params, include_auth_params=True, first=False):
        """Calls the specified method on the Shotgun Server sending the
        supplied payload.

        """

        LOG.debug("Starting rpc call to %s with params %s" % (
            method, params))

        params = self._transform_outbound(params)
        payload = self._build_payload(method, params,
            include_auth_params=include_auth_params)
        encoded_payload = self._encode_payload(payload)

        req_headers = {
            "content-type" : "application/json; charset=utf-8",
            "connection" : "keep-alive"
        }
        http_status, resp_headers, body = self._make_call("POST",
            self.config.api_path, encoded_payload, req_headers)
        LOG.debug("Completed rpc call to %s" % (method))
        try:
            self._parse_http_status(http_status)
        except ProtocolError, e:
            e.headers = resp_headers
            # 403 is returned with custom error page when api access is blocked
            if e.errcode == 403:
                e.errmsg += ": %s" % body
            raise

        response = self._decode_response(resp_headers, body)
        self._response_errors(response)
        response = self._transform_inbound(response)

        if not isinstance(response, dict) or "results" not in response:
            return response

        results = response.get("results")
        if first and isinstance(results, list):
            return results[0]
        return results

    def _auth_params(self):
        """ return a dictionary of the authentication parameters being used. """
                
        # Used to authenticate HumanUser credentials
        if self.config.user_login and self.config.user_password:
            auth_params = {
                "user_login" : str(self.config.user_login),
                "user_password" : str(self.config.user_password),
            }
            if self.config.auth_token:
                auth_params["auth_token"] = str(self.config.auth_token)

        # Use script name instead
        elif self.config.script_name and self.config.api_key:
            auth_params = {
                "script_name" : str(self.config.script_name),
                "script_key" : str(self.config.api_key),
            }

        # Authenticate using session_id
        elif self.config.session_token:
            if self.server_caps.version and self.server_caps.version < (5, 3, 0):
                raise ShotgunError("Session token based authentication requires server version 5.3.0 or "\
                    "higher, server is %s" % (self.server_caps.version,))
            
            auth_params = {"session_token" : str(self.config.session_token)}

            # Request server side to raise exception for expired sessions. 
            # This was added in as part of Shotgun 5.4.4            
            if self.server_caps.version and self.server_caps.version > (5, 4, 3):
                auth_params["reject_if_expired"] = True

        else:
            raise ValueError("invalid auth params")

        if self.config.session_uuid:
            auth_params["session_uuid"] = self.config.session_uuid

        # Make sure sudo_as_login is supported by server version
        if self.config.sudo_as_login:
            if self.server_caps.version and self.server_caps.version < (5, 3, 12):
                raise ShotgunError("Option 'sudo_as_login' requires server version 5.3.12 or "\
                    "higher, server is %s" % (self.server_caps.version,))
            auth_params["sudo_as_login"] = self.config.sudo_as_login

        return auth_params

    def _build_payload(self, method, params, include_auth_params=True):
        """Builds the payload to be send to the rpc endpoint.

        """
        if not method:
            raise ValueError("method is empty")

        call_params = []

        if include_auth_params:
            auth_params = self._auth_params()
            call_params.append(auth_params)

        if params:
            call_params.append(params)

        return {
            "method_name" : method,
            "params" : call_params
        }

    def _encode_payload(self, payload):
        """Encodes the payload to a string to be passed to the rpc endpoint.

        The payload is json encoded as a unicode string if the content
        requires it. The unicode string is then encoded as 'utf-8' as it must
        be in a single byte encoding to go over the wire.
        """

        wire = json.dumps(payload, ensure_ascii=False)
        if isinstance(wire, unicode):
            return wire.encode("utf-8")
        return wire

    def _make_call(self, verb, path, body, headers):
        """Makes a HTTP call to the server, handles retry and failure.
        """

        attempt = 0
        req_headers = {
            "user-agent": "; ".join(self._user_agents),
        }
        if self.config.authorization:
            req_headers["Authorization"] = self.config.authorization

        req_headers.update(headers or {})
        body = body or None

        max_rpc_attempts = self.config.max_rpc_attempts

        while (attempt < max_rpc_attempts):
            attempt += 1
            try:
                return self._http_request(verb, path, body, req_headers)
            except Exception:
                #TODO: LOG ?
                self._close_connection()
                if attempt == max_rpc_attempts:
                    raise

    def _http_request(self, verb, path, body, headers):
        """Makes the actual HTTP request.
        """
        url = urlparse.urlunparse((self.config.scheme, self.config.server,
            path, None, None, None))
        LOG.debug("Request is %s:%s" % (verb, url))
        LOG.debug("Request headers are %s" % headers)
        LOG.debug("Request body is %s" % body)

        conn = self._get_connection()
        resp, content = conn.request(url, method=verb, body=body,
            headers=headers)
        #http response code is handled else where
        http_status = (resp.status, resp.reason)
        resp_headers = dict(
            (k.lower(), v)
            for k, v in resp.iteritems()
        )
        resp_body = content

        LOG.debug("Response status is %s %s" % http_status)
        LOG.debug("Response headers are %s" % resp_headers)
        LOG.debug("Response body is %s" % resp_body)

        return (http_status, resp_headers, resp_body)

    def _parse_http_status(self, status):
        """Parse the status returned from the http request.

        :raises: RuntimeError if the http status is non success.

        :param status: Tuple of (code, reason).
        """
        error_code = status[0]
        errmsg = status[1]

        if status[0] >= 300:
            headers = "HTTP error from server"
            if status[0] == 503:
                errmsg = "Shotgun is currently down for maintenance. Please try again later."
            raise ProtocolError(self.config.server,
                                error_code,
                                errmsg,
                                headers)

        return

    def _decode_response(self, headers, body):
        """Decodes the response from the server from the wire format to
        a python data structure.

        :param headers: Headers from the server.

        :param body: Raw response body from the server.

        :returns: If the content-type starts with application/json or
        text/javascript the body is json decoded. Otherwise the raw body is
        returned.
        """
        if not body:
            return body

        ct = (headers.get("content-type") or "application/json").lower()

        if ct.startswith("application/json") or ct.startswith("text/javascript"):
            return self._json_loads(body)
        return body

    def _json_loads(self, body):
        return json.loads(body)

    def _json_loads_ascii(self, body):
        '''See http://stackoverflow.com/questions/956867'''
        def _decode_list(lst):
            newlist = []
            for i in lst:
                if isinstance(i, unicode):
                    i = i.encode('utf-8')
                elif isinstance(i, list):
                    i = _decode_list(i)
                newlist.append(i)
            return newlist

        def _decode_dict(dct):
            newdict = {}
            for k, v in dct.iteritems():
                if isinstance(k, unicode):
                    k = k.encode('utf-8')
                if isinstance(v, unicode):
                    v = v.encode('utf-8')
                elif isinstance(v, list):
                    v = _decode_list(v)
                newdict[k] = v
            return newdict
        return json.loads(body, object_hook=_decode_dict)


    def _response_errors(self, sg_response):
        """Raises any API errors specified in the response.

        :raises ShotgunError: If the server response contains an exception.
        """

        ERR_AUTH = 102 # error code for authentication related problems
        ERR_2FA  = 106 # error code when 2FA authentication is required but no 2FA token provided.

        if isinstance(sg_response, dict) and sg_response.get("exception"):
            if sg_response.get("error_code") == ERR_AUTH:
                raise AuthenticationFault(sg_response.get("message", "Unknown Authentication Error"))
            elif sg_response.get("error_code") == ERR_2FA:
                raise MissingTwoFactorAuthenticationFault(sg_response.get("message", "Unknown 2FA Authentication Error"))
            else:
                # raise general Fault            
                raise Fault(sg_response.get("message", "Unknown Error"))
        return

    def _visit_data(self, data, visitor):
        """Walk the data (simple python types) and call the visitor."""

        if not data:
            return data

        recursive = self._visit_data
        if isinstance(data, list):
            return [recursive(i, visitor) for i in data]

        if isinstance(data, tuple):
            return tuple(recursive(i, visitor) for i in data)

        if isinstance(data, dict):
            return dict(
                (k, recursive(v, visitor))
                for k, v in data.iteritems()
            )

        return visitor(data)

    def _transform_outbound(self, data):
        """Transforms data types or values before they are sent by the
        client.

        - changes timezones
        - converts dates and times to strings
        """

        if self.config.convert_datetimes_to_utc:
            def _change_tz(value):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=SG_TIMEZONE.local)
                return value.astimezone(SG_TIMEZONE.utc)
        else:
            _change_tz = None

        local_now = datetime.datetime.now()

        def _outbound_visitor(value):

            if isinstance(value, datetime.datetime):
                if _change_tz:
                    value = _change_tz(value)

                return value.strftime("%Y-%m-%dT%H:%M:%SZ")

            if isinstance(value, datetime.date):
                #existing code did not tz transform dates.
                return value.strftime("%Y-%m-%d")

            if isinstance(value, datetime.time):
                value = local_now.replace(hour=value.hour,
                    minute=value.minute, second=value.second,
                    microsecond=value.microsecond)
                if _change_tz:
                    value = _change_tz(value)
                return value.strftime("%Y-%m-%dT%H:%M:%SZ")

            if isinstance(value, str):
                # Convert strings to unicode
                return value.decode("utf-8")

            return value

        return self._visit_data(data, _outbound_visitor)

    def _transform_inbound(self, data):
        """Transforms data types or values after they are received from the
        server."""
        #NOTE: The time zone is removed from the time after it is transformed
        #to the local time, otherwise it will fail to compare to datetimes
        #that do not have a time zone.
        if self.config.convert_datetimes_to_utc:
            _change_tz = lambda x: x.replace(tzinfo=SG_TIMEZONE.utc)\
                .astimezone(SG_TIMEZONE.local)
        else:
            _change_tz = None

        def _inbound_visitor(value):
            if isinstance(value, basestring):
                if len(value) == 20 and self._DATE_TIME_PATTERN.match(value):
                    try:
                        # strptime was not on datetime in python2.4
                        value = datetime.datetime(
                            *time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")[:6])
                    except ValueError:
                        return value
                    if _change_tz:
                        return _change_tz(value)
                    return value

            return value

        return self._visit_data(data, _inbound_visitor)

    # ========================================================================
    # Connection Functions

    def _get_connection(self):
        """Returns the current connection or creates a new connection to the
        current server.
        """
        if self._connection is not None:
            return self._connection

        if self.config.proxy_server:
            pi = ProxyInfo(socks.PROXY_TYPE_HTTP, self.config.proxy_server,
                 self.config.proxy_port, proxy_user=self.config.proxy_user,
                 proxy_pass=self.config.proxy_pass)
            self._connection = Http(timeout=self.config.timeout_secs, ca_certs=self.__ca_certs,
                proxy_info=pi, disable_ssl_certificate_validation=self.config.no_ssl_validation)
        else:
            self._connection = Http(timeout=self.config.timeout_secs, ca_certs=self.__ca_certs,
                proxy_info=None, disable_ssl_certificate_validation=self.config.no_ssl_validation)

        return self._connection

    def _close_connection(self):
        """Closes the current connection."""
        if self._connection is None:
            return

        for conn in self._connection.connections.values():
            try:
                conn.close()
            except Exception:
                pass
        self._connection.connections.clear()
        self._connection = None
        return
    # ========================================================================
    # Utility

    def _parse_records(self, records):
        """Parses 'records' returned from the api to do local modifications:

        - Insert thumbnail urls
        - Insert local file paths.
        - Revert &lt; html entities that may be the result of input sanitization
          mechanisms back to a litteral < character.

        :param records: List of records (dicts) to process or a single record.

        :returns: A list of the records processed.
        """

        if not records:
            return []

        if not isinstance(records, (list, tuple)):
            records = [records, ]

        for rec in records:
            # skip results that aren't entity dictionaries
            if not isinstance(rec, dict):
                continue

            # iterate over each item and check each field for possible injection
            for k, v in rec.iteritems():
                if not v:
                    continue

                # Check for html entities in strings
                if isinstance(v, types.StringTypes):
                    rec[k] = rec[k].replace('&lt;', '<')

                # check for thumbnail for older version (<3.3.0) of shotgun
                if k == 'image' and \
                   self.server_caps.version and \
                   self.server_caps.version < (3, 3, 0):
                    rec['image'] = self._build_thumb_url(rec['type'],
                        rec['id'])
                    continue

                if isinstance(v, dict) and v.get('link_type') == 'local' \
                    and self.client_caps.local_path_field in v:
                    local_path = v[self.client_caps.local_path_field]
                    v['local_path'] = local_path
                    v['url'] = "file://%s" % (local_path or "",)

        return records

    def _build_thumb_url(self, entity_type, entity_id):
        """Returns the URL for the thumbnail of an entity given the
        entity type and the entity id.

        Note: This makes a call to the server for every thumbnail.

        :param entity_type: Entity type the id is for.

        :param entity_id: id of the entity to get the thumbnail for.

        :returns: Fully qualified url to the thumbnail.
        """
        # Example response from the end point
        # curl "https://foo.com/upload/get_thumbnail_url?entity_type=Version&entity_id=1"
        # 1
        # /files/0000/0000/0012/232/shot_thumb.jpg.jpg
        entity_info = {'e_type':urllib.quote(entity_type),
                       'e_id':urllib.quote(str(entity_id))}
        url = ("/upload/get_thumbnail_url?" +
                "entity_type=%(e_type)s&entity_id=%(e_id)s" % entity_info)

        body = self._make_call("GET", url, None, None)[2]

        code, thumb_url = body.splitlines()
        code = int(code)

        #code of 0 means error, second line is the error code
        if code == 0:
            raise ShotgunError(thumb_url)

        if code == 1:
            return urlparse.urlunparse((self.config.scheme,
                self.config.server, thumb_url.strip(), None, None, None))

        # Comments in prev version said we can get this sometimes.
        raise RuntimeError("Unknown code %s %s" % (code, thumb_url))

    def _dict_to_list(self, d, key_name="field_name", value_name="value"):
        """Utility function to convert a dict into a list dicts using the
        key_name and value_name keys.

        e.g. d {'foo' : 'bar'} changed to [{'field_name':'foo, 'value':'bar'}]
        """

        return [
            {key_name : k, value_name : v }
            for k, v in (d or {}).iteritems()
        ]


# Helpers from the previous API, left as is.

# Based on http://code.activestate.com/recipes/146306/
class FormPostHandler(urllib2.BaseHandler):
    """
    Handler for multipart form data
    """
    handler_order = urllib2.HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.get_data()
        if data is not None and not isinstance(data, basestring):
            files = []
            params = []
            for key, value in data.items():
                if isinstance(value, file):
                    files.append((key, value))
                else:
                    params.append((key, value))
            if not files:
                data = urllib.urlencode(params, True) # sequencing on
            else:
                boundary, data = self.encode(params, files)
                content_type = 'multipart/form-data; boundary=%s' % boundary
                request.add_unredirected_header('Content-Type', content_type)
            request.add_data(data)
        return request

    def encode(self, params, files, boundary=None, buffer=None):
        if boundary is None:
            boundary = mimetools.choose_boundary()
        if buffer is None:
            buffer = cStringIO.StringIO()
        for (key, value) in params:
            buffer.write('--%s\r\n' % boundary)
            buffer.write('Content-Disposition: form-data; name="%s"' % key)
            buffer.write('\r\n\r\n%s\r\n' % value)
        for (key, fd) in files:
            filename = fd.name.split('/')[-1]
            content_type = mimetypes.guess_type(filename)[0]
            content_type = content_type or 'application/octet-stream'
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            buffer.write('--%s\r\n' % boundary)
            c_dis = 'Content-Disposition: form-data; name="%s"; filename="%s"%s'
            content_disposition = c_dis % (key, filename, '\r\n')
            buffer.write(content_disposition)
            buffer.write('Content-Type: %s\r\n' % content_type)
            buffer.write('Content-Length: %s\r\n' % file_size)
            fd.seek(0)
            buffer.write('\r\n%s\r\n' % fd.read())
        buffer.write('--%s--\r\n\r\n' % boundary)
        buffer = buffer.getvalue()
        return boundary, buffer

    def https_request(self, request):
        return self.http_request(request)


def _translate_filters(filters, filter_operator):
    '''_translate_filters translates filters params into data structure
    expected by rpc call.'''
    wrapped_filters = {
        "filter_operator": filter_operator or "all",
        "filters": filters
    }

    return _translate_filters_dict(wrapped_filters)

def _translate_filters_dict(sg_filter):
    new_filters = {}
    filter_operator = sg_filter.get("filter_operator")
    
    if filter_operator == "all" or filter_operator == "and":
        new_filters["logical_operator"] = "and"
    elif filter_operator == "any" or filter_operator == "or":
        new_filters["logical_operator"] = "or"
    else:
        raise ShotgunError("Invalid filter_operator %s" % filter_operator)

    if not isinstance(sg_filter["filters"], (list,tuple)):
        raise ShotgunError("Invalid filters, expected a list or a tuple, got %s" % sg_filter["filters"])
        
    new_filters["conditions"] = _translate_filters_list(sg_filter["filters"])
    
    return new_filters
    
def _translate_filters_list(filters):
    conditions = []
    
    for sg_filter in filters:
        if isinstance(sg_filter, (list,tuple)):
            conditions.append(_translate_filters_simple(sg_filter))
        elif isinstance(sg_filter, dict):
            conditions.append(_translate_filters_dict(sg_filter))
        else:
            raise ShotgunError("Invalid filters, expected a list, tuple or dict, got %s" % sg_filter)
    
    return conditions

def _translate_filters_simple(sg_filter):
    condition = {
        "path": sg_filter[0],
        "relation": sg_filter[1]
    }
    
    values = sg_filter[2:]
    if len(values) == 1 and isinstance(values[0], (list, tuple)):
        values = values[0]

    condition["values"] = values

    return condition

def _version_str(version):
    """Converts a tuple of int's to a '.' separated str"""
    return '.'.join(map(str, version))
