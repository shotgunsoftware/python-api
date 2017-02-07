#!/usr/bin/env python
"""
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2017, Shotgun Software Inc.

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
"""


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
"""
Logging instance for shotgun_api3

Provides a logging instance where log messages are sent during execution. This instance has no
handler associated with it.

.. seealso:: :ref:`logging`
"""
LOG.setLevel(logging.WARN)

SG_TIMEZONE = SgTimezone()

NO_SSL_VALIDATION = False
"""
Turns off hostname matching validation for SSL certificates

Sometimes there are cases where certificate validation should be disabled. For example, if you
have a self-signed internal certificate that isn't included in our certificate bundle, you may
not require the added security provided by enforcing this.
"""
try:
    import ssl        
except ImportError, e:
    if "SHOTGUN_FORCE_CERTIFICATE_VALIDATION" in os.environ:
        raise ImportError("%s. SHOTGUN_FORCE_CERTIFICATE_VALIDATION environment variable prevents "
                          "disabling SSL certificate validation." % e)
    LOG.debug("ssl not found, disabling certificate validation")
    NO_SSL_VALIDATION = True

# ----------------------------------------------------------------------------
# Version
__version__ = "3.0.33.dev"

# ----------------------------------------------------------------------------
# Errors

class ShotgunError(Exception):
    """
    Base for all Shotgun API Errors.
    """
    pass

class ShotgunFileDownloadError(ShotgunError):
    """
    Exception for file download-related errors.
    """
    pass

class Fault(ShotgunError):
    """
    Exception when server-side exception detected.
    """
    pass

class AuthenticationFault(Fault):
    """
    Exception when the server side reports an error related to authentication.
    """
    pass

class MissingTwoFactorAuthenticationFault(Fault):
    """
    Exception when the server side reports an error related to missing two-factor authentication
    credentials.
    """
    pass

# ----------------------------------------------------------------------------
# API

class ServerCapabilities(object):
    """
    Container for the servers capabilities, such as version enabled features.

    .. warning::

        This class is part of the internal API and its interfaces may change at any time in 
        the future. Therefore, usage of this class is discouraged. 
    """

    def __init__(self, host, meta):
        """
        ServerCapabilities.__init__

        :param str host: Host name for the server excluding protocol.
        :param dict meta: dict of meta data for the server returned from the info() api method.

        :ivar str host:
        :ivar dict server_info:
        :ivar tuple version: Simple version of the Shotgun server. ``(major, minor, rev)``
        :ivar bool is_dev: ``True`` if server is running a development version of the Shotgun
            codebase.
        """
        # Server host name
        self.host = host
        self.server_info = meta

        # Version from server is major.minor.rev or major.minor.rev."Dev"
        # Store version as tuple and check dev flag
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
        """
        Checks the server version supports a given feature, raises an exception if it does not.

        :param dict feature: dict where **version** key contains a 3 integer tuple indicating the
            supported server version and **label** key contains a human-readable label str::

                { 'version': (5, 4, 4), 'label': 'project parameter }
        :param bool raise_hell: Whether to raise an exception if the feature is not supported.
            Defaults to ``True``
        :raises: :class:`ShotgunError` if the current server version does not support ``feature``
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
        """
        Ensures server has support for JSON API endpoint added in v2.4.0.
        """
        self._ensure_support({
            'version': (2, 4, 0),
            'label': 'JSON API'
        })

    def ensure_include_archived_projects(self):
        """
        Ensures server has support for archived Projects feature added in v5.3.14.
        """
        self._ensure_support({
            'version': (5, 3, 14),
            'label': 'include_archived_projects parameter'
        })

    def ensure_per_project_customization(self):
        """
        Ensures server has support for per-project customization feature added in v5.4.4.
        """
        return self._ensure_support({
            'version': (5, 4, 4),
            'label': 'project parameter'
        }, True)

    def ensure_support_for_additional_filter_presets(self):
        """
        Ensures server has support for additional filter presets feature added in v7.0.0.
        """
        return self._ensure_support({
            'version': (7, 0, 0),
            'label': 'additional_filter_presets parameter'
        }, True)

    def __str__(self):
        return "ServerCapabilities: host %s, version %s, is_dev %s"\
                 % (self.host, self.version, self.is_dev)

class ClientCapabilities(object):
    """
    Container for the client capabilities.

    .. warning::

        This class is part of the internal API and its interfaces may change at any time in 
        the future. Therefore, usage of this class is discouraged. 

    :ivar str platform: The current client platform. Valid values are ``mac``, ``linux``,
        ``windows``, or ``None`` (if the current platform couldn't be determined).
    :ivar str local_path_field: The SG field used for local file paths. This is calculated using
        the value of ``platform``. Ex. ``local_path_mac``.
    :ivar str py_version: Simple version of Python executable as a string. Eg. ``2.7``.
    :ivar str ssl_version: Version of OpenSSL installed. Eg. ``OpenSSL 1.0.2g  1 Mar 2016``. This
        info is only available in Python 2.7+ if the ssl module was imported successfully.
        Defaults to ``unknown``
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

        # extract the OpenSSL version if we can. The version is only available in Python 2.7 and
        # only if we successfully imported ssl
        self.ssl_version = "unknown"
        try:
            self.ssl_version = ssl.OPENSSL_VERSION
        except (AttributeError, NameError):
            pass

    def __str__(self):
        return "ClientCapabilities: platform %s, local_path_field %s, "\
            "py_verison %s, ssl version %s" % (self.platform, self.local_path_field,
            self.py_version, self.ssl_version)

class _Config(object):
    """
    Container for the client configuration.
    """

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
        # Authentication parameters to be folded into final auth_params dict
        self.extra_auth_params = None
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
    """
    Shotgun Client connection.
    """

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
        """
        Initializes a new instance of the Shotgun client.

        :param str base_url: http or https url of the Shotgun server. Do not include the trailing
            slash::

                https://example.shotgunstudio.com
        :param str script_name: name of the Script entity used to authenticate to the server.
            If provided, then ``api_key`` must be as well, and neither ``login`` nor ``password``
            can be provided.

            .. seealso:: :ref:`authentication`
        :param str api_key: API key for the provided ``script_name``. Used to authenticate to the
            server.  If provided, then ``script_name`` must be as well, and neither ``login`` nor
            ``password`` can be provided.

            .. seealso:: :ref:`authentication`
        :param bool convert_datetimes_to_utc: (optional) When ``True``, datetime values are converted
            from local time to UTC time before being sent to the server. Datetimes received from
            the server are then converted back to local time. When ``False`` the client should use
            UTC date time values. Default is ``True``.
        :param str http_proxy: (optional) URL for a proxy server to use for all connections. The
            expected str format is ``[username:password@]111.222.333.444[:8080]``. Examples::

                192.168.0.1
                192.168.0.1:8888
                joe:user@192.168.0.1:8888
        :param bool connect: (optional) When ``True``, as soon as the :class:`~shotgun_api3.Shotgun`
            instance is created, a connection will be made to the Shotgun server to determine the
            server capabilities and confirm this version of the client is compatible with the server
            version. This is mostly used for testing. Default is ``True``.
        :param str ca_certs: (optional) path to an external SSL certificates file. By default, the
            Shotgun API will use its own built-in certificates file which stores root certificates
            for the most common Certificate Authorities (CAs). If you are using a corporate or
            internal CA, or are packaging an application into an executable, it may be necessary to
            point to your own certificates file. You can do this by passing in the full path to the
            file via this parameter or by setting the environment variable ``SHOTGUN_API_CACERTS``.
            In the case both are set, this parameter will take precedence.
        :param str login: The user login str to use to authenticate to the server when using user-based
            authentication. If provided, then ``password`` must be as well, and neither
            ``script_name`` nor ``api_key`` can be provided.

            .. seealso:: :ref:`authentication`
        :param str password: The password str to use to authenticate to the server when using user-based
            authentication. If provided, then ``login`` must be as well and neither ``script_name``
            nor ``api_key`` can be provided.

            See :ref:`authentication` for more info.
        :param str sudo_as_login: A user login string for the user whose permissions will be applied
            to all actions. Event log entries will be generated showing this user performing all
            actions with an additional extra meta-data parameter ``sudo_actual_user`` indicating the
            script or user that is actually authenticated.
        :param str session_token: The session token to use to authenticate to the server. This
            can be used as an alternative to authenticating with a script user or regular user.
            You can retrieve the session token by running the
            :meth:`~shotgun_api3.Shotgun.get_session_token()` method.

            .. todo: Add this info to the Authentication section of the docs
        :param str auth_token: The authentication token required to authenticate to a server with
            two-factor authentication turned on. If provided, then ``login`` and ``password`` must
            be provided as well, and neither ``script_name`` nor ``api_key`` can be provided.

            .. note:: These tokens can be short lived so a session is established right away if an
                ``auth_token`` is provided. A
                :class:`~shotgun_api3.MissingTwoFactorAuthenticationFault` will be raised if the
                ``auth_token`` is invalid.
            .. todo: Add this info to the Authentication section of the docs

        .. note:: A note about proxy connections: If you are using Python <= v2.6.2, HTTPS
            connections through a proxy server will not work due to a bug in the :mod:`urllib2`
            library (see http://bugs.python.org/issue1424152). This will affect upload and
            download-related methods in the Shotgun API (eg. :meth:`~shotgun_api3.Shotgun.upload`,
            :meth:`~shotgun_api3.Shotgun.upload_thumbnail`,
            :meth:`~shotgun_api3.Shotgun.upload_filmstrip_thumbnail`,
            :meth:`~shotgun_api3.Shotgun.download_attachment`. Normal CRUD methods for passing JSON
            data should still work fine. If you cannot upgrade your Python installation, you can see
            the patch merged into Python v2.6.3 (http://hg.python.org/cpython/rev/0f57b30a152f/) and
            try and hack it into your installation but YMMV. For older versions of Python there
            are other patches that were proposed in the bug report that may help you as well.
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
        auth, self.config.server = urllib.splituser(urlparse.urlsplit(base_url).netloc)
        if auth:
            auth = base64.encodestring(urllib.unquote(auth))
            self.config.authorization = "Basic " + auth.strip()

        # foo:bar@123.456.789.012:3456
        if http_proxy:
            # check if we're using authentication. Start from the end since there might be
            # @ in the user's password.
            p = http_proxy.rsplit("@", 1)
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
        """
        Property containing server information.

        >>> sg.server_info
        {'full_version': [6, 3, 15, 0],
         's3_uploads_enabled': True,
         's3_direct_uploads_enabled': True,
         'version': [6, 3, 15]}

        :returns: dict of server information from :class:`ServerCapabilities` object
        :rtype: dict
        """
        return self.server_caps.server_info

    @property
    def server_caps(self):
        """
        Property containing :class:`ServerCapabilities` object.

        >>> sg.server_caps
        <shotgun_api3.shotgun.ServerCapabilities object at 0x10120d350>

        :returns: :class:`ServerCapabilities` object that describe the server the client is
            connected to.
        :rtype: :class:`ServerCapabilities` object
        """
        if not self._server_caps or (
            self._server_caps.host != self.config.server):
            self._server_caps = ServerCapabilities(self.config.server,
                self.info())
        return self._server_caps

    def connect(self):
        """
        Connect client to the server if it is not already connected.

        .. note:: The client will automatically connect to the server on demand. You only need to
            call this function if you wish to confirm the client can connect.
        """
        self._get_connection()
        self.info()
        return

    def close(self):
        """
        Close the current connection to the server.

        If the client needs to connect again it will do so automatically.
        """
        self._close_connection()
        return

    def info(self):
        """
        Get API-related metadata from the Shotgun server.

        >>> sg.info()
        {'s3_uploads_enabled': True, 'full_version': [6, 3, 15, 0], 'version': [6, 3, 15]}

        :returns: dict of the server metadata.
        :rtype: dict
        """
        return self._call_rpc("info", None, include_auth_params=False)

    def find_one(self, entity_type, filters, fields=None, order=None,
        filter_operator=None, retired_only=False, include_archived_projects=True,
        additional_filter_presets=None):
        """
        Shortcut for :meth:`~shotgun_api3.Shotgun.find` with ``limit=1`` so it returns a single
        result.

            >>> sg.find_one("Asset", [["id", "is", 32]], ["id", "code", "sg_status_list"])
            {'code': 'Gopher', 'id': 32, 'sg_status_list': 'ip', 'type': 'Asset'}

        :param str entity_type: Shotgun entity type as a string to find.
        :param list filters: list of filters to apply to the query.

            .. seealso:: :ref:`filter_syntax`

        :param list fields: Optional list of fields to include in each entity record returned.
            Defaults to ``["id"]``.
        :param int order: Optional list of fields to order the results by. List has the format::

            [{'field_name':'foo', 'direction':'asc'}, {'field_name':'bar', 'direction':'desc'}]

            Defaults to sorting by ``id`` in ascending order.
        :param str filter_operator: Operator to apply to the filters. Supported values are ``"all"``
            and ``"any"``. These are just another way of defining if the query is an AND or OR
            query. Defaults to ``"all"``.
        :param bool retired_only: Optional boolean when ``True`` will return only entities that have
            been retried. Defaults to ``False`` which returns only entities which have not been
            retired. There is no option to return both retired and non-retired entities in the
            same query.
        :param bool include_archived_projects: Optional boolean flag to include entities whose projects
            have been archived. Defaults to ``True``.
        :param additional_filter_presets: Optional list of presets to further filter the result
            set, list has the form::

                [{"preset_name": <preset_name>, <optional_param1>: <optional_value1>, ... }]

            Note that these filters are ANDed together and ANDed with the 'filter'
            argument.

            For details on supported presets and the format of this parameter see
            :ref:`additional_filter_presets`
        :returns: Dictionary representing a single matching entity with the requested fields,
            and the defaults ``"id"`` and ``"type"`` which are always included.
        :rtype: dict
        """

        results = self.find(entity_type, filters, fields, order,
            filter_operator, 1, retired_only, include_archived_projects=include_archived_projects,
            additional_filter_presets=additional_filter_presets)

        if results:
            return results[0]
        return None

    def find(self, entity_type, filters, fields=None, order=None,
            filter_operator=None, limit=0, retired_only=False, page=0,
            include_archived_projects=True, additional_filter_presets=None):
        """
        Find entities matching the given filters.

            >>> # Find Character Assets in Sequence 100_FOO
            >>> # -------------
            >>> fields = ['id', 'code', 'sg_asset_type']
            >>> sequence_id = 2 # Sequence "100_FOO"
            >>> project_id = 4 # Demo Project
            >>> filters = [
            ...     ['project', 'is', {'type': 'Project', 'id': project_id}],
            ...     ['sg_asset_type', 'is', 'Character'],
            ...     ['sequences', 'is', {'type': 'Sequence', 'id': sequence_id}]
            ... ]
            >>> assets= sg.find("Asset",filters,fields)
            [{'code': 'Gopher', 'id': 32, 'sg_asset_type': 'Character', 'type': 'Asset'},
             {'code': 'Cow', 'id': 33, 'sg_asset_type': 'Character', 'type': 'Asset'},
             {'code': 'Bird_1', 'id': 35, 'sg_asset_type': 'Character', 'type': 'Asset'},
             {'code': 'Bird_2', 'id': 36, 'sg_asset_type': 'Character', 'type': 'Asset'},
             {'code': 'Bird_3', 'id': 37, 'sg_asset_type': 'Character', 'type': 'Asset'},
             {'code': 'Raccoon', 'id': 45, 'sg_asset_type': 'Character', 'type': 'Asset'},
             {'code': 'Wet Gopher', 'id': 149, 'sg_asset_type': 'Character', 'type': 'Asset'}]

        You can drill through single entity links to filter on fields or display linked fields.
        This is often called "deep linking" or using "dot syntax".

            .. seealso:: :ref:`filter_syntax`

            >>> # Find Versions created by Tasks in the Animation Pipeline Step
            >>> # -------------
            >>> fields = ['id', 'code']
            >>> pipeline_step_id = 2 # Animation Step ID
            >>> project_id = 4 # Demo Project
            >>> # you can drill through single-entity link fields
            >>> filters = [
            ...     ['project','is', {'type': 'Project','id': project_id}],
            ...     ['sg_task.Task.step.Step.id', 'is', pipeline_step_id]
            >>> ]
            >>> sg.find("Version", filters, fields)
            [{'code': 'scene_010_anim_v001', 'id': 42, 'type': 'Version'},
             {'code': 'scene_010_anim_v002', 'id': 134, 'type': 'Version'},
             {'code': 'bird_v001', 'id': 137, 'type': 'Version'},
             {'code': 'birdAltBlue_v002', 'id': 236, 'type': 'Version'}]

        :param str entity_type: Shotgun entity type to find.
        :param list filters: list of filters to apply to the query.

            .. seealso:: :ref:`filter_syntax`

        :param list fields: Optional list of fields to include in each entity record returned.
            Defaults to ``["id"]``.
        :param list order: Optional list of dictionaries defining how to order the results of the
            query. Each dictionary contains the ``field_name`` to order by and  the ``direction``
            to sort::

                [{'field_name':'foo', 'direction':'asc'}, {'field_name':'bar', 'direction':'desc'}]

            Defaults to sorting by ``id`` in ascending order.
        :param str filter_operator: Operator to apply to the filters. Supported values are ``"all"``
            and ``"any"``. These are just another way of defining if the query is an AND or OR
            query. Defaults to ``"all"``.
        :param int limit: Optional limit to the number of entities to return. Defaults to ``0`` which
            returns all entities that match.
        :param int page: Optional page of results to return. Use this together with the ``limit``
            parameter to control how your query results are paged. Defaults to ``0`` which returns
            the first page of results.
        :param bool retired_only: Optional boolean when ``True`` will return only entities that have
            been retried. Defaults to ``False`` which returns only entities which have not been
            retired. There is no option to return both retired and non-retired entities in the
            same query.
        :param bool include_archived_projects: Optional boolean flag to include entities whose projects
            have been archived. Defaults to ``True``.
        :param additional_filter_presets: Optional list of presets to further filter the result
            set, list has the form::

                [{"preset_name": <preset_name>, <optional_param1>: <optional_value1>, ... }]

            Note that these filters are ANDed together and ANDed with the 'filter'
            argument.

            For details on supported presets and the format of this parameter see
            :ref:`additional_filter_presets`
        :returns: list of dictionaries representing each entity with the requested fields, and the
            defaults ``"id"`` and ``"type"`` which are always included.
        :rtype: list
        """

        if not isinstance(limit, int) or limit < 0:
            raise ValueError("limit parameter must be a positive integer")

        if not isinstance(page, int) or page < 0:
            raise ValueError("page parameter must be a positive integer")

        if isinstance(filters, (list, tuple)):
            filters = _translate_filters(filters, filter_operator)
        elif filter_operator:
            # TODO: Not sure if this test is correct, replicated from prev api
            raise ShotgunError("Deprecated: Use of filter_operator for find()"
                " is not valid any more. See the documentation on find()")

        if not include_archived_projects:
            # This defaults to True on the server (no argument is sent)
            # So we only need to check the server version if it is False
            self.server_caps.ensure_include_archived_projects()

        if additional_filter_presets:
            self.server_caps.ensure_support_for_additional_filter_presets()

        params = self._construct_read_parameters(entity_type,
                                                 fields,
                                                 filters,
                                                 retired_only,
                                                 order,
                                                 include_archived_projects,
                                                 additional_filter_presets)

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
                                   include_archived_projects,
                                   additional_filter_presets):
        params = {}
        params["type"] = entity_type
        params["return_fields"] = fields or ["id"]
        params["filters"] = filters
        params["return_only"] = (retired_only and 'retired') or "active"
        params["return_paging_info"] = True
        params["paging"] = { "entities_per_page": self.config.records_per_page,
                             "current_page": 1 }

        if additional_filter_presets:
            params["additional_filter_presets"] = additional_filter_presets;

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
        Summarize field data returned by a query.

        This provides the same functionality as the summaries in the UI. You can specify one or
        more fields to summarize, choose the summary type for each, and optionally group the
        results which will return summary information for each group as well as the total for
        the query.

        **Example: Count all Assets for a Project**

        >>> sg.summarize(entity_type='Asset',
        ...              filters = [['project', 'is', {'type':'Project', 'id':4}]],
        ...              summary_fields=[{'field':'id', 'type':'count'}])
        {'groups': [], 'summaries': {'id': 15}}

        ``summaries`` contains the total summary for the query. Each key is the field summarized
        and the value is the result of the summary operation for the entire result set.

        .. note::
            You cannot perform more than one summary on a field at a time, but you can summarize
            several different fields in the same call.

        **Example: Count all Assets for a Project, grouped by sg_asset_type**

        >>> sg.summarize(entity_type='Asset',
        ...              filters=[['project', 'is', {'type': 'Project', 'id': 4}]],
        ...              summary_fields=[{'field': 'id', 'type': 'count'}],
        ...              grouping=[{'field': 'sg_asset_type', 'type': 'exact', 'direction': 'asc'}])
        {'groups': [{'group_name': 'Character','group_value': 'Character', 'summaries': {'id': 3}},
                    {'group_name': 'Environment','group_value': 'Environment', 'summaries': {'id': 3}},
                    {'group_name': 'Matte Painting', 'group_value': 'Matte Painting', 'summaries': {'id': 1}},
                    {'group_name': 'Prop', 'group_value': 'Prop', 'summaries': {'id': 4}},
                    {'group_name': 'Vehicle', 'group_value': 'Vehicle', 'summaries': {'id': 4}}],
         'summaries': {'id': 15}}

        - ``summaries`` contains the total summary for the query.
        - ``groups`` contains the summary for each group.

            - ``group_name`` is the display name for the group.
            - ``group_value`` is the actual value of the grouping value. This is often the same as
              ``group_name`` but in the case when grouping by entity, the ``group_name`` may be
              ``PuppyA`` and the group_value would be
              ``{'type':'Asset','id':922,'name':'PuppyA'}``.
            - ``summaries`` contains the summary calculation dict for each field requested.

        **Example: Count all Tasks for a Sequence and find the latest due_date**

        >>> sg.summarize(entity_type='Task',
        ...              filters = [
        ...                 ['entity.Shot.sg_sequence', 'is', {'type':'Sequence', 'id':2}],
        ...                 ['sg_status_list', 'is_not', 'na']],
        ...              summary_fields=[{'field':'id', 'type':'count'},
        ...                              {'field':'due_date','type':'latest'}])
        {'groups': [], 'summaries': {'due_date': '2013-07-05', 'id': 30}}

        This shows that the there are 30 Tasks for Shots in the Sequence and the latest ``due_date``
        of any Task is ``2013-07-05``.

        **Example: Count all Tasks for a Sequence, find the latest due_date and group by Shot**

        >>> sg.summarize(entity_type='Task',
        ...              filters = [
        ...                 ['entity.Shot.sg_sequence', 'is', {'type': 'Sequence', 'id': 2}],
        ...                 ['sg_status_list', 'is_not', 'na']],
        ...              summary_fields=[{'field': 'id', 'type': 'count'}, {'field': 'due_date', 'type': 'latest'}],
        ...              grouping=[{'field': 'entity', 'type': 'exact', 'direction': 'asc'}]))
        {'groups': [{'group_name': 'shot_010',
                     'group_value': {'id': 2, 'name': 'shot_010', 'type': 'Shot', 'valid': 'valid'},
                     'summaries': {'due_date': '2013-06-18', 'id': 10}},
                    {'group_name': 'shot_020',
                     'group_value': {'id': 3, 'name': 'shot_020', 'type': 'Shot', 'valid': 'valid'},
                     'summaries': {'due_date': '2013-06-28', 'id': 10}},
                    {'group_name': 'shot_030',
                     'group_value': {'id': 4, 'name': 'shot_030', 'type': 'Shot', 'valid': 'valid'},
                     'summaries': {'due_date': '2013-07-05', 'id': 10}}],
         'summaries': {'due_date': '2013-07-05', 'id': 30}}

        This shows that the there are 30 Tasks for Shots in the Sequence and the latest ``due_date``
        of any Task is ``2013-07-05``. Because the summary is grouped by ``entity``, we can also
        see the summaries for each Shot returned. Each Shot has 10 Tasks and the latest ``due_date``
        for each Shot. The difference between ``group_name`` and ``group_value`` is highlighted in
        this example as the name of the Shot is different from its value.

        **Example: Count all Tasks for a Sequence, find the latest due_date, group by Shot and
        Pipeline Step**

        >>> sg.summarize(entity_type='Task',
        ...                 filters = [
        ...                    ['entity.Shot.sg_sequence', 'is', {'type': 'Sequence', 'id': 2}],
        ...                    ['sg_status_list', 'is_not', 'na']],
        ...                 summary_fields=[{'field': 'id', 'type': 'count'},
        ...                                 {'field': 'due_date', 'type': 'latest'}],
        ...                 grouping=[{'field': 'entity', 'type': 'exact', 'direction': 'asc'},
        ...                           {'field': 'step', 'type': 'exact', 'direction': 'asc'}])
        {'groups': [{'group_name': 'shot_010',
                     'group_value': {'id': 2, 'name': 'shot_010', 'type': 'Shot', 'valid': 'valid'},
                     'groups': [{'group_name': 'Client',
                                 'group_value': {'id': 1, 'name': 'Client', 'type': 'Step', 'valid': 'valid'},
                                 'summaries': {'due_date': '2013-05-04', 'id': 1}},
                                {'group_name': 'Online',
                                 'group_value': {'id': 2, 'name': 'Online', 'type': 'Step', 'valid': 'valid'},
                                 'summaries': {'due_date': '2013-05-05', 'id': 1}},
                                ...
                                ... truncated for brevity
                                ...
                                {'group_name': 'Comp',
                                 'group_value': {'id': 8, 'name': 'Comp', 'type': 'Step', 'valid': 'valid'},
                                 'summaries': {'due_date': '2013-06-18', 'id': 1}}],
                     'summaries': {'due_date': '2013-06-18', 'id': 10}},
                    {'group_name': 'shot_020',
                     'group_value': {'id': 3, 'name': 'shot_020', 'type': 'Shot', 'valid': 'valid'},
                     'groups': [{'group_name': 'Client',
                                 'group_value': {'id': 1, 'name': 'Client', 'type': 'Step', 'valid': 'valid'},
                                 'summaries': {'due_date': '2013-05-15', 'id': 1}},
                                {'group_name': 'Online',
                                 'group_value': {'id': 2, 'name': 'Online', 'type': 'Step', 'valid': 'valid'},
                                 'summaries': {'due_date': '2013-05-16', 'id': 1}},
                                ...
                                ... truncated for brevity
                                ...
                                {'group_name': 'Comp',
                                 'group_value': {'id': 8, 'name': 'Comp', 'type': 'Step', 'valid': 'valid'},
                                 'summaries': {'due_date': '2013-06-28', 'id': 1}}],
                     'summaries': {'due_date': '2013-06-28', 'id': 10}},
                    {'group_name': 'shot_030',
                     'group_value': {'id': 4, 'name': 'shot_030', 'type': 'Shot', 'valid': 'valid'},
                     'groups': [{'group_name': 'Client',
                                 'group_value': {'id': 1, 'name': 'Client', 'type': 'Step', 'valid': 'valid'},
                                 'summaries': {'due_date': '2013-05-20', 'id': 1}},
                                {'group_name': 'Online',
                                 'group_value': {'id': 2, 'name': 'Online', 'type': 'Step', 'valid': 'valid'},
                                 'summaries': {'due_date': '2013-05-21', 'id': 1}},
                                ...
                                ... truncated for brevity
                                ...
                                {'group_name': 'Comp',
                                 'group_value': {'id': 8, 'name': 'Comp', 'type': 'Step', 'valid': 'valid'},
                                 'summaries': {'due_date': '2013-07-05', 'id': 1}}],
                     'summaries': {'due_date': '2013-07-05', 'id': 10}}],
        'summaries': {'due_date': '2013-07-05', 'id': 30}}

        When grouping my more than one field, the grouping structure is repeated for each sub-group
        and summary values are returned for each group on each level.

        :param str entity_type: The entity type to summarize
        :param list filters: A list of conditions used to filter the find query. Uses the same
            syntax as :meth:`~shotgun_api3.Shotgun.find` method.
        :param list summary_fields: A list of dictionaries with the following keys:

            :field: The internal Shotgun field name you are summarizing.
            :type: The type of summary you are performing on the field. Summary types can be any of
                ``record_count``, ``count``, ``sum``, ``maximum``, ``minimum``, ``average``,
                ``earliest``, ``latest``, ``percentage``, ``status_percentage``, ``status_list``,
                ``checked``, ``unchecked`` depending on the type of field you're summarizing.

        :param str filter_operator: Operator to apply to the filters. Supported values are ``"all"``
            and ``"any"``. These are just another way of defining if the query is an AND or OR
            query. Defaults to ``"all"``.
        :param list grouping: Optional list of dicts with the following keys:

                :field: a string indicating the internal Shotgun field name on ``entity_type`` to
                    group results by.
                :type: A string indicating the type of grouping to perform for each group.
                    Valid types depend on the type of field you are grouping on and can be one of
                    ``exact``, ``tens``, ``hundreds``, ``thousands``, ``tensofthousands``,
                    ``hundredsofthousands``, ``millions``, ``day``, ``week``, ``month``,
                    ``quarter``,``year``, ``clustered_date``, ``oneday``, ``fivedays``,
                    ``entitytype``, ``firstletter``.
                :direction: A string that sets the order to display the grouped results. Valid
                    options are ``asc`` and  ``desc``. Defaults to ``asc``.

        :returns: dictionary containing grouping and summaries keys.
        :rtype: dict
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
        """
        Create a new entity of the specified ``entity_type``.

            >>> data = {
            ...     "project": {"type": "Project", "id": 161},
            ...     "sg_sequence": {"type": "Sequence", "id": 109},
            ...     "code": "001_100",
            ...     'sg_status_list': "ip"
            ... }
            >>> sg.create('Shot', data)
            {'code': '001_100',
             'id': 2557,
             'project': {'id': 161, 'name': 'Pied Piper', 'type': 'Project'},
             'sg_sequence': {'id': 109, 'name': 'Sequence 001', 'type': 'Sequence'},
             'sg_status_list': 'ip',
             'type': 'Shot'}

        :param str entity_type: Shotgun entity type to create.
        :param dict data: Dictionary of fields and corresponding values to set on the new entity. If
            ``image`` or ``filmstrip_image`` fields are provided, the file path will be uploaded
            to the server automatically.
        :param list return_fields: Optional list of additional field values to return from the new
            entity. Defaults to ``id`` field.
        :returns: Shotgun entity dictionary containing the field/value pairs of all of the fields
            set from the ``data`` parameter as well as the defaults ``type`` and ``id``. If any
            additional fields were provided using the ``return_fields`` parameter, these would be
            included as well.
        :rtype: dict
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

    def update(self, entity_type, entity_id, data, multi_entity_update_modes=None):
        """
        Update the specified entity with the supplied data.

        >>> shots = [
        ...    {'type':'Shot', 'id':'40435'},
        ...    {'type':'Shot', 'id':'40438'},
        ...    {'type':'Shot', 'id':'40441'}]
        >>> data = {
        ...    'shots': shots_asset_is_in,
        ...    'sg_status_list':'rev'}
        >>> sg.update("Asset", 55, data)
        {'type': 'Shot',
         'id': 55,
         'sg_status_`list`': 'rev',
         'shots': [{'id': 40435, 'name': '100_010', 'type': 'Shot', 'valid': 'valid'},
                   {'id': 40438, 'name': '100_040', 'type': 'Shot', 'valid': 'valid'},
                   {'id': 40441, 'name': '100_070', 'type': 'Shot', 'valid': 'valid'}]
        }

        :param str entity_type: Entity type to update.
        :param id entity_id: id of the entity to update.
        :param dict data: key/value pairs where key is the field name and value is the value to set
            for that field. This method does not restrict the updating of fields hidden in the web
            UI via the Project Tracking Settings panel.
        :param dict multi_entity_update_modes: Optional dict indicating what update mode to use
            when updating a multi-entity link field. The keys in the dict are the fields to set
            the mode for, and the values from the dict are one of ``set``, ``add``, or ``remove``.
            Defaults to ``set``.
            ::

                multi_entity_update_modes={"shots": "add", "assets": "remove"}

        :returns: Dictionary of the fields updated, with the default keys `type` and `id` added as well.
        :rtype: dict
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
                "fields" : self._dict_to_list(
                    data,
                    extra_data=self._dict_to_extra_data(
                        multi_entity_update_modes, "multi_entity_update_mode"))
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
        """
        Retire the specified entity.

        Entities in Shotgun are not "deleted" destructively, they are instead, "retired". This
        means they are placed in the trash where they are no longer accessible to users.

        The entity can be brought back to life using :meth:`~shotgun_api3.Shotgun.revive`.

            >>> sg.delete("Shot", 2557)
            True

        :param str entity_type: Shotgun entity type to delete.
        :param id entity_id: ``id`` of the entity to delete.
        :returns: ``True`` if the entity was deleted, ``False`` otherwise (for example, if the
            entity was already deleted).
        :rtype: bool
        :raises: :class:`Fault` if entity does not exist (deleted or not).
       """

        params = {
            "type" : entity_type,
            "id" : entity_id
        }

        return self._call_rpc("delete", params)

    def revive(self, entity_type, entity_id):
        """
        Revive an entity that has previously been deleted.

        >>> sg.revive("Shot", 860)
        True

        :param str entity_type: Shotgun entity type to revive.
        :param int entity_id: id of the entity to revive.
        :returns: ``True`` if the entity was revived, ``False`` otherwise (e.g. if the
            entity is not currently retired).
        :rtype: bool
        """

        params = {
            "type" : entity_type,
            "id" : entity_id
        }

        return self._call_rpc("revive", params)

    def batch(self, requests):
        """
        Make a batch request of several :meth:`~shotgun_api3.Shotgun.create`,
        :meth:`~shotgun_api3.Shotgun.update`, and :meth:`~shotgun_api3.Shotgun.delete` calls.

        All requests are performed within a transaction, so either all will complete or none will.

        Ex. Make a bunch of shots::

            batch_data = []
            for i in range(1,100):
                data = {
                    "code": "shot_%04d" % i,
                    "project": project
                }
                batch_data.append({"request_type": "create", "entity_type": "Shot", "data": data})
            sg.batch(batch_data)

        Example output::

             [{'code': 'shot_0001',
               'type': 'Shot',
               'id': 3624,
               'project': {'id': 4, 'name': 'Demo Project', 'type': 'Project'}},
              ...
              ... and a bunch more ...
              ...
              {'code': 'shot_0099',
               'type': 'Shot',
               'id': 3722,
               'project': {'id': 4, 'name': 'Demo Project', 'type': 'Project'}}]

        Ex. All three types of requests in one batch::

            batch_data = [
              {"request_type": "create", "entity_type": "Shot", "data": {"code": "New Shot 1", "project": project}},
              {"request_type": "update", "entity_type": "Shot", "entity_id": 3624, "data": {"code": "Changed 1"}},
              {"request_type": "delete", "entity_type": "Shot", "entity_id": 3624}
            ]
            sg.batch(batch_data)

        Example output::

             [{'code': 'New Shot 1', 'type': 'Shot', 'id': 3723, 'project': {'id': 4, 'name': 'Demo Project', 'type': 'Project'}},
              {'code': 'Changed 1', 'type': 'Shot', 'id': 3624},
              True]

        :param list requests: A list of dict's of the form which have a request_type key and also
            specifies:

            - create: ``entity_type``, data dict of fields to set
            - update: ``entity_type``, ``entity_id``, data dict of fields to set, and optionally ``multi_entity_update_modes``
            - delete: ``entity_type`` and entity_id
        :returns: A list of values for each operation. Create and update requests return a dict of
            the fields updated. Delete requests return ``True`` if the entity was deleted.
        :rtype: list
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
                request_params['fields'] = self._dict_to_list(req["data"],
                    extra_data=self._dict_to_extra_data(
                        req.get("multi_entity_update_modes"),
                        "multi_entity_update_mode"))
                if "multi_entity_update_mode" in req:
                    request_params['multi_entity_update_mode'] = req["multi_entity_update_mode"]
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
        """
        Return the work day rules for a given date range.

        .. versionadded:: 3.0.9
            Requires Shotgun server v3.2.0+

        This returns the defined WorkDayRules between the ``start_date`` and ``end_date`` inclusive
        as a dict where the key is the date and the value is another dict describing the rule for
        that date.

        Rules are represented by a dict with the following keys:

        :description: the description entered into the work day rule exception if applicable.
        :reason: one of six options:

            - STUDIO_WORK_WEEK: standard studio schedule applies
            - STUDIO_EXCEPTION: studio-wide exception applies
            - PROJECT_WORK_WEEK: standard project schedule applies
            - PROJECT_EXCEPTION: project-specific exception applies
            - USER_WORK_WEEK: standard user work week applies
            - USER_EXCEPTION: user-specific exception applies

        :working: boolean indicating whether it is a "working" day or not.

        >>> sg.work_schedule_read("2015-12-21", "2015-12-25")
        {'2015-12-21': {'description': None,
                        'reason': 'STUDIO_WORK_WEEK',
                        'working': True},
         '2015-12-22': {'description': None,
                        'reason': 'STUDIO_WORK_WEEK',
                        'working': True},
         '2015-12-23': {'description': None,
                        'reason': 'STUDIO_WORK_WEEK',
                        'working': True},
         '2015-12-24': {'description': 'Closed for Christmas Eve',
                        'reason': 'STUDIO_EXCEPTION',
                        'working': False},
         '2015-12-25': {'description': 'Closed for Christmas',
                        'reason': 'STUDIO_EXCEPTION',
                        'working': False}}


        :param str start_date: Start date of date range. ``YYYY-MM-DD``
        :param str end_date: End date of date range. ``YYYY-MM-DD``
        :param dict project: Optional Project entity to query `WorkDayRules` for.
        :param dict user: Optional HumanUser entity to query WorkDayRules for.
        :returns: Complex dict containing each date and the WorkDayRule defined for that date
            between the ``start_date`` and ``end date`` inclusive. See above for details.
        :rtype: dict
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

    def work_schedule_update(self, date, working, description=None, project=None, user=None,
                             recalculate_field=None):
        """
        Update the work schedule for a given date.

        .. versionadded:: 3.0.9
            Requires Shotgun server v3.2.0+

        If neither ``project`` nor ``user`` are passed in, the studio work schedule will be updated.
        ``project`` and ``user`` can only be used exclusively of each other.

        >>> sg.work_schedule_update ("2015-12-31", working=False,
        ...                          description="Studio closed for New Years Eve", project=None,
        ...                          user=None, recalculate_field=None)
        {'date': '2015-12-31',
         'description': "Studio closed for New Years Eve",
         'project': None,
         'user': None,
         'working': False}

        :param str date: Date of WorkDayRule to update. ``YYY-MM-DD``
        :param bool working: Indicates whether the day is a working day or not.
        :param str description: Optional reason for time off.
        :param dict project: Optional Project entity to assign the rule to. Cannot be used with the
            ``user`` param.
        :param dict user: Optional HumanUser entity to assign the rule to. Cannot be used with the
            ``project`` param.
        :param str recalculate_field: Optional schedule field that will be recalculated on Tasks
            when they are affected by a change in working schedule. Options are ``due_date`` or
            ``duration``. Defaults to the value set in the Shotgun web application's Site
            Preferences.
        :returns: dict containing key/value pairs for each value of the work day rule updated.
        :rtype: dict
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
        """
        Add the entity to the user's followed entities.

        If the user is already following the entity, the method will succeed but nothing will be
        changed on the server-side.

            >>> sg.follow({"type": "HumanUser", "id": 42}, {"type": "Shot", "id": 2050})
            {'followed': True, 'user': {'type': 'HumanUser', 'id': 42},
             'entity': {'type': 'Shot', 'id': 2050}}

        :param dict user: User entity that will follow the entity.
        :param dict entity: Shotgun entity to be followed.
        :returns: dict with ``"followed": True`` as well as key/values for the params that were
            passed in.
        :rtype: dict
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
        """
        Remove entity from the user's followed entities.

        This does nothing if the user is not following the entity.

        >>> sg.unfollow({"type": "HumanUser", "id": 42}, {"type": "Shot", "id": 2050})
        {'entity': {'type': 'Shot', 'id': 2050}, 'user': {'type': 'HumanUser', 'id': 42},
         'unfollowed': True}

        :param dict user: User entity that will unfollow the entity.
        :param dict entity: Entity to be unfollowed
        :returns: dict with ``"unfollowed": True`` as well as key/values for the params that were
            passed in.
        :rtype: dict
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
        """
        Return all followers for an entity.

            >>> sg.followers({"type": "Shot", "id": 2050})
            [{'status': 'act', 'valid': 'valid', 'type': 'HumanUser', 'name': 'Richard Hendriks',
              'id': 42},
             {'status': 'act', 'valid': 'valid', 'type': 'HumanUser', 'name': 'Bertram Gilfoyle',
              'id': 33},
             {'status': 'act', 'valid': 'valid', 'type': 'HumanUser', 'name': 'Dinesh Chugtai',
              'id': 57}]

        :param dict entity: Entity to find followers of.
        :returns: list of dicts representing each user following the entity
        :rtype: list
        :versionadded:
        """

        if not self.server_caps.version or self.server_caps.version < (5, 1, 22):
            raise ShotgunError("Follow support requires server version 5.2 or "\
                "higher, server is %s" % (self.server_caps.version,))
        
        params = dict(
            entity=entity
        )
        
        return self._call_rpc('followers', params)

    def schema_entity_read(self, project_entity=None):
        """
        Return all active entity types, their display names, and their visibility.

        If the project parameter is specified, the schema visibility for the given project is
        being returned. If the project parameter is omitted or set to ``None``, a full listing is
        returned where per-project entity type visibility settings are not considered.

        >>> sg.schema_entity_read()
        {'ActionMenuItem': {'name': {'editable': False, 'value': 'Action Menu Item'},
                            'visible': {'editable': False, 'value': True}},
         'ApiUser': {'name': {'editable': False, 'value': 'Script'},
                     'visible': {'editable': False, 'value': True}},
         'AppWelcomeUserConnection': {'name': {'editable': False,
                                               'value': 'App Welcome User Connection'},
                                      'visible': {'editable': False, 'value': True}},
         'Asset': {'name': {'editable': False, 'value': 'Asset'},
                   'visible': {'editable': False, 'value': True}},
         'AssetAssetConnection': {'name': {'editable': False,
                                           'value': 'Asset Asset Connection'},
                                  'visible': {'editable': False, 'value': True}},
         '...'
        }

        :param dict project_entity: Optional Project entity specifying which project to return
            the listing for. If omitted or set to ``None``, per-project visibility settings are
            not taken into consideration and the global list is returned. Example:
            ``{'type': 'Project', 'id': 3}``
        :returns: dict of Entity Type to dict containing the display name.
        :rtype: dict
        """

        params = {}

        params = self._add_project_param(params, project_entity)

        if params:
            return self._call_rpc("schema_entity_read", params)
        else:
            return self._call_rpc("schema_entity_read", None)

    def schema_read(self, project_entity=None):
        """
        Get the schema for all fields on all entities.

        .. note::
            If ``project_entity`` is not specified, everything is reported as visible.

        >>> sg.schema_read()
        {'ActionMenuItem': {'created_at': {'data_type': {'editable': False, 'value': 'date_time'},
                                           'description': {'editable': True,  'value': ''},
                                           'editable': {'editable': False, 'value': False},
                                           'entity_type': {'editable': False, 'value': 'ActionMenuItem'},
                                           'mandatory': {'editable': False, 'value': False},
                                           'name': {'editable': True, 'value': 'Date Created'},
                                           'properties': {'default_value': {'editable': False, 'value': None},
                                                          'summary_default': {'editable': True, 'value': 'none'}},
                                           'unique': {'editable': False, 'value': False},
                                           'visible': {'editable': False, 'value': True}},
                            'created_by': {'data_type': {'editable': False,'value': 'entity'},
                                           'description': {'editable': True,'value': ''},
                                           'editable': {'editable': False,'value': False},
                                           'entity_type': {'editable': False,'value': 'ActionMenuItem'},
                                           'mandatory': {'editable': False,'value': False},
                                           'name': {'editable': True,'value': 'Created by'},
                                           'properties': {'default_value': {'editable': False,'value': None},
                                                          'summary_default': {'editable': True,'value': 'none'},
                                                          'valid_types': {'editable': True,'value': ['HumanUser','ApiUser']}},
                                           'unique': {'editable': False,'value': False},
                                           'visible': {'editable': False,'value': True}},
                            ...
                            ...
         ...
         ...
         'Version': {'client_approved': {'data_type': {'editable': False,'value': 'checkbox'},
                                         'description': {'editable': True,'value': ''},
                                         'editable': {'editable': False,'value': True},
                                         'entity_type': {'editable': False,'value': 'Version'},
                                         'mandatory': {'editable': False,'value': False},
                                         'name': {'editable': True,'value': 'Client Approved'},
                                         'properties': {'default_value': {'editable': False,'value': False},
                                                        'summary_default': {'editable': False,'value': 'none'}},
                                         'unique': {'editable': False,'value': False},
                                         'visible': {'editable': False,'value': True}},
                     ...
                     ...
         ...
         ...
        }

        :param dict project_entity: Optional, Project entity specifying which project to return
            the listing for. If omitted or set to ``None``, per-project visibility settings are
            not taken into consideration and the global list is returned. Example:
            ``{'type': 'Project', 'id': 3}``. Defaults to ``None``.
        :returns: A nested dict object containing a key/value pair for all fields of all entity
            types. Properties that are ``'editable': True``, can be updated using the
            :meth:`~shotgun_api3.Shotgun.schema_field_update` method.
        :rtype: dict
        """

        params = {}

        params = self._add_project_param(params, project_entity)

        if params:
            return self._call_rpc("schema_read", params)
        else:
            return self._call_rpc("schema_read", None)

    def schema_field_read(self, entity_type, field_name=None, project_entity=None):
        """
        Get schema for all fields on the specified entity type or just the field name specified
        if provided.

        .. note::
            Unlike how the results of a :meth:`~shotgun_api3.Shotgun.find` can be pumped into a
            :meth:`~shotgun_api3.Shotgun.create` or :meth:`~shotgun_api3.Shotgun.update`, the
            results of :meth:`~shotgun_api3.Shotgun.schema_field_read` are not compatible with
            the format used for :meth:`~shotgun_api3.Shotgun.schema_field_create` or
            :meth:`~shotgun_api3.Shotgun.schema_field_update`. If you need to pipe the results
            from :meth:`~shotgun_api3.Shotgun.schema_field_read` into a
            :meth:`~shotgun_api3.Shotgun.schema_field_create` or
            :meth:`~shotgun_api3.Shotgun.schema_field_update`, you will need to reformat the
            data in your script.

        .. note::
            If you don't specify a ``project_entity``, everything is reported as visible.

        >>> sg.schema_field_read('Asset', 'shots')
        {'shots': {'data_type': {'editable': False, 'value': 'multi_entity'},
                   'description': {'editable': True, 'value': ''},
                   'editable': {'editable': False, 'value': True},
                   'entity_type': {'editable': False, 'value': 'Asset'},
                   'mandatory': {'editable': False, 'value': False},
                   'name': {'editable': True, 'value': 'Shots'},
                   'properties': {'default_value': {'editable': False,
                                                    'value': None},
                                  'summary_default': {'editable': True,
                                                      'value': 'none'},
                                  'valid_types': {'editable': True,
                                                  'value': ['Shot']}},
                   'unique': {'editable': False, 'value': False},
                   'visible': {'editable': False, 'value': True}}}

        :param str entity_type: Entity type to get the schema for.
        :param str field_name: Optional internal Shotgun name of the field to get the schema
            definition for. If this parameter is excluded or set to ``None``, data structures of
            all fields will be returned. Defaults to ``None``. Example: ``sg_temp_field``.
        :param dict project_entity: Optional Project entity specifying which project to return
            the listing for. If omitted or set to ``None``, per-project visibility settings are
            not taken into consideration and the global list is returned. Example:
            ``{'type': 'Project', 'id': 3}``
        :returns: a nested dict object containing a key/value pair for the ``field_name`` specified
            and its properties, or if no field_name is specified, for all the fields of the
            ``entity_type``. Properties that are ``'editable': True``, can be updated using the
            :meth:`~shotgun_api3.Shotgun.schema_field_update` method.
        :rtype: dict
        """

        params = {
            "type": entity_type,
        }

        if field_name:
            params["field_name"] = field_name

        params = self._add_project_param(params, project_entity)

        return self._call_rpc("schema_field_read", params)

    def schema_field_create(self, entity_type, data_type, display_name, properties=None):
        """
        Create a field for the specified entity type.

        .. note::
            If the internal Shotgun field name computed from the provided ``display_name`` already
            exists, the internal Shotgun field name will automatically be appended with ``_1`` in
            order to create a unique name. The integer suffix will be incremented by 1 until a
            unique name is found.

        >>> properties = {"summary_default": "count", "description": "Complexity breakdown of Asset"}
        >>> sg.schema_field_create("Asset", "text", "Complexity", properties)
        'sg_complexity'

        :param str entity_type: Entity type to add the field to.
        :param str data_type: Shotgun data type for the new field.
        :param str display_name: Specifies the display name of the field you are creating. The
            system name will be created from this display name and returned upon successful
            creation.
        :param dict properties: Dict of valid properties for the new field. Use this to specify
            other field properties such as the 'description' or 'summary_default'.
        :returns: The internal Shotgun name for the new field, this is different to the
            ``display_name`` parameter passed in.
        :rtype: str
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
        """
        Update the properties for the specified field on an entity.

        .. note::
            Although the property name may be the key in a nested dictionary, like
            'summary_default', it is treated no differently than keys that are up
            one level, like 'description'.

        >>> properties = {"name": "Test Number Field Renamed", "summary_default": "sum",
        ...               "description": "this is only a test"}
        >>> sg.schema_field_update("Asset", "sg_test_number", properties)
        True

        :param entity_type: Entity type of field to update.
        :param field_name: Internal Shotgun name of the field to update.
        :param properties: Dictionary with key/value pairs where the key is the property to be
            updated and the value is the new value.
        :returns: ``True`` if the field was updated.
        :rtype: bool
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
        """
        Delete the specified field from the entity type.

        >>> sg.schema_field_delete("Asset", "sg_temp_field")
        True

        :param str entity_type: Entity type to delete the field from.
        :param str field_name: Internal Shotgun name of the field to delete.
        :returns: ``True`` if the field was deleted.
        :rtype: bool
        """

        params = {
            "type" : entity_type,
            "field_name" : field_name
        }

        return self._call_rpc("schema_field_delete", params)

    def add_user_agent(self, agent):
        """
        Add agent to the user-agent header.

        Appends agent to the user-agent string sent with every API request.

        >>> sg.add_user_agent("my_tool 1.0")

        :param str agent: string to append to user-agent.
        """
        self._user_agents.append(agent)

    def reset_user_agent(self):
        """
        Reset user agent to the default value.

        Example default user-agent::

            shotgun-json (3.0.17); Python 2.6 (Mac); ssl OpenSSL 1.0.2d 9 Jul 2015 (validate)

        """
        ua_platform = "Unknown"
        if self.client_caps.platform is not None:
            ua_platform = self.client_caps.platform.capitalize()
        

        # create ssl validation string based on settings
        validation_str = "validate"
        if self.config.no_ssl_validation:
            validation_str = "no-validate"
        
        self._user_agents = ["shotgun-json (%s)" % __version__,
                             "Python %s (%s)" % (self.client_caps.py_version, ua_platform),
                             "ssl %s (%s)" % (self.client_caps.ssl_version, validation_str)]


    def set_session_uuid(self, session_uuid):
        """
        Set the browser session_uuid in the current Shotgun API instance.

        When this is set, any events generated by the API will include the ``session_uuid`` value
        on the corresponding EventLogEntries. If there is a current browser session open with
        this ``session_uuid``, the browser will display updates for these events.

        >>> sg.set_session_uuid("5a1d49b0-0c69-11e0-a24c-003048d17544")

        :param str session_uuid: The uuid of the browser session to be updated.
        """

        self.config.session_uuid = session_uuid
        return

    def share_thumbnail(self, entities, thumbnail_path=None, source_entity=None,
        filmstrip_thumbnail=False, **kwargs):
        """
        Associate a thumbnail with more than one Shotgun entity.

        .. versionadded:: 3.0.9
            Requires Shotgun server v4.0.0+

        Share the thumbnail from between entities without requiring uploading the thumbnail file
        multiple times. You can use this in two ways:

        1) Upload an image to set as the thumbnail on multiple entities.
        2) Update multiple entities to point to an existing entity's thumbnail.

        .. note::
            When sharing a filmstrip thumbnail, it is required to have a static thumbnail in
            place before the filmstrip will be displayed in the Shotgun web UI.

        >>> thumb = '/data/show/ne2/100_110/anim/01.mlk-02b.jpg'
        >>> e = [{'type': 'Version', 'id': 123}, {'type': 'Version', 'id': 456}]
        >>> sg.share_thumbnail(entities=e, thumbnail_path=thumb)
        4271

        >>> e = [{'type': 'Version', 'id': 123}, {'type': 'Version', 'id': 456}]
        >>> sg.share_thumbnail(entities=e, source_entity={'type':'Version', 'id': 789})
        4271

        :param list entities: The entities to update to point to the shared  thumbnail provided in
            standard entity dict format::

                [{'type': 'Version', 'id': 123},
                 {'type': 'Version', 'id': 456}]
        :param str thumbnail_path: The full path to the local thumbnail file to upload and share.
            Required if ``source_entity`` is not provided.
        :param dict source_entity: The entity whos thumbnail will be the source for sharing.
            Required if ``source_entity`` is not provided.
        :param bool filmstrip_thumbnail: ``True`` to share the filmstrip thumbnail. ``False`` to
            share the static thumbnail. Defaults to ``False``.
        :returns: ``id`` of the Attachment entity representing the source thumbnail that is shared.
        :rtype: int
        """
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

        result = self._send_form(url, params)

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
        """
        Upload a file from a local path and assign it as the thumbnail for the specified entity.

        .. note::
            Images will automatically be re-sized on the server to generate a size-appropriate image
            file. However, the original file is retained as well and is accessible when you click
            on the thumbnail image in the web UI. If you are using a local install of Shotgun and
            have not enabled S3, this can eat up disk space if you're uploading really large source
            images for your thumbnails.

        You can un-set (aka clear) a thumbnail on an entity using the
        :meth:`~shotgun_api3.Shotgun.update` method and setting the **image** field to ``None``.
        This will also unset the ``filmstrip_thumbnail`` field if it is set.

        Supported image file types include ``.jpg` and ``.png`` (preferred) but will also accept.
        ``.gif```, ``.tif``, ``.tiff``, ``.bmp``, ``.exr``, ``.dpx``, and ``.tga``.

        This method wraps over :meth:`~shotgun_api3.Shotgun.upload`. Additional keyword arguments
        passed to this method will be forwarded to the :meth:`~shotgun_api3.Shotgun.upload` method.

        :param str entity_type: Entity type to set the thumbnail for.
        :param int entity_id: Id of the entity to set the thumbnail for.
        :param str path: Full path to the thumbnail file on disk.
        :returns: Id of the new attachment
        """
        return self.upload(entity_type, entity_id, path,
            field_name="thumb_image", **kwargs)

    def upload_filmstrip_thumbnail(self, entity_type, entity_id, path, **kwargs):
        """
        Upload filmstrip thumbnail to specified entity.

        .. versionadded:: 3.0.9
            Requires Shotgun server v3.1.0+

        Uploads a file from a local directory and assigns it as the filmstrip thumbnail for the
        specified entity. The image must be a horizontal strip of any number of frames that are
        exactly 240 pixels wide. Therefore the whole strip must be an exact multiple of 240 pixels
        in width. The height can be anything (and will depend on the aspect ratio of the frames).
        Any image file type that works for thumbnails will work for filmstrip thumbnails.

        Filmstrip thumbnails will only be visible in the Thumbnail field on an entity if a
        regular thumbnail image is also uploaded to the entity. The standard thumbnail is
        displayed by default as the poster frame. Then, on hover, the filmstrip thumbnail is
        displayed and updated based on your horizontal cursor position for scrubbing. On mouseout,
        the default thumbnail is displayed again as the poster frame.

        The url for a filmstrip thumbnail on an entity is available by querying for the
        ``filmstrip_image field``.

        You can un-set (aka clear) a thumbnail on an entity using the
        :meth:`~shotgun_api3.Shotgun.update` method and setting the **image** field to ``None``.
        This will also unset the ``filmstrip_thumbnail`` field if it is set.

        This method wraps over :meth:`~shotgun_api3.Shotgun.upload`. Additional keyword arguments
        passed to this method will be forwarded to the :meth:`~shotgun_api3.Shotgun.upload` method.

        >>> filmstrip_thumbnail = '/data/show/ne2/100_110/anim/01.mlk-02b_filmstrip.jpg'
        >>> sg.upload_filmstrip_thumbnail("Version", 27, filmstrip_thumbnail)
        87

        :param str entity_type: Entity type to set the filmstrip thumbnail for.
        :param int entity_id: Id of the entity to set the filmstrip thumbnail for.
        :param str path: Full path to the filmstrip thumbnail file on disk.
        :returns: Id of the new Attachment entity created for the filmstrip thumbnail
        :rtype: int
        """
        if not self.server_caps.version or self.server_caps.version < (3, 1, 0):
            raise ShotgunError("Filmstrip thumbnail support requires server version 3.1 or "\
                "higher, server is %s" % (self.server_caps.version,))

        return self.upload(entity_type, entity_id, path,
            field_name="filmstrip_thumb_image", **kwargs)

    def upload(self, entity_type, entity_id, path, field_name=None, display_name=None,
               tag_list=None):
        """
        Upload a file to the specified entity.

        Creates an Attachment entity for the file in Shotgun and links it to the specified entity.
        You can optionally store the file in a field on the entity, change the display name, and
        assign tags to the Attachment.

        >>> mov_file = '/data/show/ne2/100_110/anim/01.mlk-02b.mov'
        >>> sg.upload("Shot", 423, mov_file, field_name="sg_latest_quicktime",
        ...           display_name="Latest QT")
        72

        :param str entity_type: Entity type to link the upload to.
        :param int entity_id: Id of the entity to link the upload to.
        :param str path: Full path to an existing non-empty file on disk to upload.
        :param str field_name: The internal Shotgun field name on the entity to store the file in.
            This field must be a File/Link field type.
        :param str display_name: The display name to use for the file. Defaults to the file name.
        :param str tag_list: comma-separated string of tags to assign to the file.
        :returns: Id of the Attachment entity that was created for the image.
        :rtype: int
        """
        # Basic validations of the file to upload.
        path = os.path.abspath(os.path.expanduser(path or ""))
        if not os.path.isfile(path):
            raise ShotgunError("Path must be a valid file, got '%s'" % path)
        if os.path.getsize(path) == 0:
            raise ShotgunError("Path cannot be an empty file: '%s'" % path)

        is_thumbnail = (field_name in ["thumb_image", "filmstrip_thumb_image", "image",
                                       "filmstrip_image"])

        # Version.sg_uploaded_movie is handled as a special case and uploaded
        # directly to Cloud storage
        if self.server_info["s3_direct_uploads_enabled"] \
                and entity_type == "Version" and field_name == "sg_uploaded_movie":
            return self._upload_to_storage(entity_type, entity_id, path, field_name, display_name,
                                           tag_list, is_thumbnail)
        else:
            return self._upload_to_sg(entity_type, entity_id, path, field_name, display_name,
                                      tag_list, is_thumbnail)

    def _upload_to_storage(self, entity_type, entity_id, path, field_name, display_name,
                           tag_list, is_thumbnail):
        """
        Internal function to upload a file to the Cloud storage and link it to the specified entity.

        :param str entity_type: Entity type to link the upload to.
        :param int entity_id: Id of the entity to link the upload to.
        :param str path: Full path to an existing non-empty file on disk to upload.
        :param str field_name: The internal Shotgun field name on the entity to store the file in.
            This field must be a File/Link field type.
        :param str display_name: The display name to use for the file. Defaults to the file name.
        :param str tag_list: comma-separated string of tags to assign to the file.
        :param bool is_thumbnail: indicates if the attachment is a thumbnail.
        :returns: Id of the Attachment entity that was created for the image.
        :rtype: int
        """

        filename = os.path.basename(path)

        # Step 1: get the upload url

        upload_info = self._get_attachment_upload_info(is_thumbnail, filename)

        # Step 2: upload the file

        fd = open(path, "rb")
        try:
            content_type = mimetypes.guess_type(filename)[0]
            content_type = content_type or "application/octet-stream"
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]

            # Perform the request
            opener = urllib2.build_opener(urllib2.HTTPHandler)

            request = urllib2.Request(upload_info["upload_url"], data=fd)
            request.add_header("Content-Type", content_type)
            request.add_header("Content-Length", file_size)
            request.get_method = lambda: "PUT"
            result = opener.open(request)
        except urllib2.HTTPError, e:
            if e.code == 500:
                raise ShotgunError("Server encountered an internal error.\n%s\n%s\n\n" % (url, e))
            else:
                raise ShotgunError("Unanticipated error occurred uploading %s: %s" % (path, e))
        finally:
            fd.close()

        LOG.debug("File uploaded to Cloud storage: %s", filename)

        # Step 3: create the attachment

        url = urlparse.urlunparse((self.config.scheme, self.config.server,
                                   "/upload/api_link_file", None, None, None))

        params = {
            "entity_type" : entity_type,
            "entity_id" : entity_id,
            "upload_link_info": upload_info['upload_info']
        }

        params.update(self._auth_params())

        if is_thumbnail:
            if field_name == "filmstrip_thumb_image" or field_name == "filmstrip_image":
                params["filmstrip"] = True
        else:
            if display_name is None:
                display_name = filename
            # we allow linking to nothing for generic reference use cases
            if field_name is not None:
                params["field_name"] = field_name
            params["display_name"] = display_name
            # None gets converted to a string and added as a tag...
            if tag_list:
                params["tag_list"] = tag_list

        result = self._send_form(url, params)
        if not str(result).startswith("1"):
            raise ShotgunError("Could not upload file successfully, but " \
                               "not sure why.\nPath: %s\nUrl: %s\nError: %s" % (
                                   path, url, str(result)))

        LOG.debug("Attachment linked to content on Cloud storage")

        attachment_id = int(str(result).split(":")[1].split("\n")[0])
        return attachment_id

    def _upload_to_sg(self, entity_type, entity_id, path, field_name, display_name,
                      tag_list, is_thumbnail):
        """
        Internal function to upload a file to Shotgun and link it to the specified entity.

        :param str entity_type: Entity type to link the upload to.
        :param int entity_id: Id of the entity to link the upload to.
        :param str path: Full path to an existing non-empty file on disk to upload.
        :param str field_name: The internal Shotgun field name on the entity to store the file in.
            This field must be a File/Link field type.
        :param str display_name: The display name to use for the file. Defaults to the file name.
        :param str tag_list: comma-separated string of tags to assign to the file.
        :param bool is_thumbnail: indicates if the attachment is a thumbnail.

        :returns: Id of the Attachment entity that was created for the image.
        :rtype: int
        """

        params = {
            "entity_type" : entity_type,
            "entity_id" : entity_id,
        }

        params.update(self._auth_params())

        if is_thumbnail:
            url = urlparse.urlunparse((self.config.scheme, self.config.server,
                "/upload/publish_thumbnail", None, None, None))
            params["thumb_image"] = open(path, "rb")
            if field_name == "filmstrip_thumb_image" or field_name == "filmstrip_image":
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

        result = self._send_form(url, params)

        if not str(result).startswith("1"):
            raise ShotgunError("Could not upload file successfully, but "\
                "not sure why.\nPath: %s\nUrl: %s\nError: %s" % (
                path, url, str(result)))

        attachment_id = int(str(result).split(":")[1].split("\n")[0])
        return attachment_id

    def _get_attachment_upload_info(self, is_thumbnail, filename):
        """
        Internal function to get the information needed to upload a file to Cloud storage.

        :param bool is_thumbnail: indicates if the attachment is a thumbnail.
        :param str filename: name of the file that will be uploaded.

        :returns: dictionary containing the upload url and
            upload_info (passed back to the SG server once the upload is completed).
        :rtype: dict
        """

        if is_thumbnail:
            upload_type = "Thumbnail"
        else:
            upload_type = "Attachment"

        params = {
            "upload_type" : upload_type,
            "filename" : filename
        }

        params.update(self._auth_params())

        upload_url = "/upload/api_get_upload_link_info"
        url = urlparse.urlunparse((self.config.scheme, self.config.server,
                                   upload_url, None, None, None))

        upload_info = self._send_form(url, params)
        if not str(upload_info).startswith("1"):
            raise ShotgunError("Could not get upload_url but " \
                               "not sure why.\nPath: %s\nUrl: %s\nError: %s" % (
                                   path, url, str(upload_info)))

        LOG.debug("Completed rpc call to %s" % (upload_url))
        return {
            "upload_url" : str(upload_info).split("\n")[1],
            "upload_info" : upload_info
        }

    def download_attachment(self, attachment=False, file_path=None, attachment_id=None):
        """
        Download the file associated with a Shotgun Attachment.

            >>> version = sg.find_one("Version", [["id", "is", 7115]], ["sg_uploaded_movie"])
            >>> local_file_path = "/var/tmp/%s" % version["sg_uploaded_movie"]["name"]
            >>> sg.download_attachment(version["sg_uploaded_movie"], file_path=local_file_path)
            /var/tmp/100b_scene_output_v032.mov

        .. warning::

            On older (< v5.1.0) Shotgun versions, non-downloadable files
            on Shotgun don't raise exceptions, they cause a server error which
            returns a 200 with the page content.

        :param dict attachment: Usually a dictionary representing an Attachment entity.
            The dictionary should have a ``url`` key that specifies the download url.
            Optionally, the dictionary can be a standard entity hash format with ``id`` and
            ``type`` keys as long as ``"type"=="Attachment"``. This is only supported for
            backwards compatibility (#22150).

            If an int value is passed in, the Attachment entity with the matching id will
            be downloaded from the Shotgun server.
        :param str file_path: Optional file path to write the data directly to local disk. This
            avoids loading all of the data in memory and saves the file locally at the given path.
        :param id attachment_id: (deprecated) Optional ``id`` of the Attachment entity in Shotgun to
            download.

            .. note:
                This parameter exists only for backwards compatibility for scripts specifying
                the parameter with keywords.
        :returns: If ``file_path`` is provided, returns the path to the file on disk.  If
            ``file_path`` is ``None``, returns the actual data of the file as a string.
        :rtype: str
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
                            # Once python 2.4 support is not needed we can think about using
                            # elementtree. The doc is pretty small so this shouldn't be an issue.
                            match = re.search('<Message>(.*)</Message>', xml)
                            if match:
                                err += ' - %s' % (match.group(1))
            raise ShotgunFileDownloadError(err)
        else:
            if file_path:
                if not fp.closed:
                    fp.close()
                return file_path
            else:
                return attachment

    def set_up_auth_cookie(self):
        """
        Set up urllib2 with a cookie for authentication on the Shotgun instance.

        Looks up session token and sets that in a cookie in the :mod:`urllib2` handler. This is
        used internally for downloading attachments from the Shotgun server.
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
        """
        Return the URL for downloading provided Attachment.

        :param mixed attachment: Usually a dict representing An Attachment entity in Shotgun to
            return the download url for. If the ``url`` key is present, it will be used as-is for
            the download url. If the ``url`` key is not present, a url will be constructed pointing
            at the current Shotgun server for downloading the Attachment entity using the ``id``.

            If ``None`` is passed in, it is silently ignored in order to avoid raising an error when
            results from a :meth:`~shotgun_api3.Shotgun.find` are passed off to
            :meth:`~shotgun_api3.Shotgun.download_attachment`

        .. note::
            Support for passing in an int representing the Attachment ``id`` is deprecated

        .. todo::
            Support for a standard entity hash should be removed: #22150

        :returns: the download URL for the Attachment or ``None`` if ``None`` was passed to
            ``attachment`` parameter.
        :rtype: str
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
        """
        Authenticate Shotgun HumanUser.

        Authenticates a user given the login, password, and optionally, one-time auth token (when
        two-factor authentication is required). The user must be a ``HumanUser`` entity and the
        account must be active.

        >>> sg.authenticate_human_user("rhendriks", "c0mPre$Hi0n", None)
        {"type": "HumanUser", "id": 123, "name": "Richard Hendriks"}

        :param str user_login: Login name of Shotgun HumanUser
        :param str user_password: Password for Shotgun HumanUser
        :param str auth_token: One-time token required to authenticate Shotgun HumanUser
            when two-factor authentication is turned on.
        :returns: Standard Shotgun dictionary representing the HumanUser if authentication
            succeeded. ``None`` if authentication failed for any reason.
        :rtype: dict
        """
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
            data = self.find_one('HumanUser', [['sg_status_list', 'is', 'act'],
                                               ['login', 'is', user_login]],
                                 ['id', 'login'], '', 'all')
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
        Update a Project's ``last_accessed_by_current_user`` field to the current timestamp.

        This helps keep track of the recent Projects each user has worked on and enables scripts
        and apps to use this information to display "Recent Projects" for users as a convenience.

        .. versionadded::
            Requires Shotgun v5.3.20+

        >>> sg.update_project_last_accessed({"type": "Project", "id": 66},
        ...                                 {"type": "HumanUser", "id": 43})

        :param dict project: Standard Project entity dictionary
        :param dict user: Standard user entity dictionary. This is optional if the current API
            instance is using user-based authenitcation, or has specified ``sudo_as_login``. In
            these cases, if ``user`` is not provided, the ``sudo_as_login`` value or ``login``
            value from the current instance will be used instead.
        """
        if self.server_caps.version and self.server_caps.version < (5, 3, 20):
                raise ShotgunError("update_project_last_accessed requires server version 5.3.20 or "
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
        self._parse_records(record)[0]



    def note_thread_read(self, note_id, entity_fields=None):
        """
        Return the full conversation for a given note, including Replies and Attachments.

        Returns a complex data structure on the following form::

            [{'content': 'Please add more awesomeness to the color grading.',
              'created_at': '2015-07-14 21:33:28 UTC',
              'created_by': {'id': 38,
                             'name': 'John Pink',
                             'status': 'act',
                             'type': 'HumanUser',
                             'valid': 'valid'},
              'id': 6013,
              'type': 'Note'},
             {'created_at': '2015-07-14 21:33:32 UTC',
              'created_by': {'id': 38,
                             'name': 'John Pink',
                             'status': 'act',
                             'type': 'HumanUser',
                             'valid': 'valid'},
              'id': 159,
              'type': 'Attachment'},
             {'content': 'More awesomeness added',
              'created_at': '2015-07-14 21:54:51 UTC',
              'id': 5,
              'type': 'Reply',
              'user': {'id': 38,
                       'name': 'David Blue',
                       'status': 'act',
                       'type': 'HumanUser',
                       'valid': 'valid'}}]

        The list is returned in descending chronological order.

        If you wish to include additional fields beyond the ones that are
        returned by default, you can specify these in an entity_fields
        dictionary. This dictionary should be keyed by entity type and each
        key should contain a list of fields to retrieve, for example::

            { "Note":       ["created_by.HumanUser.image",
                             "addressings_to",
                             "playlist",
                             "user" ],
              "Reply":      ["content"],
              "Attachment": ["filmstrip_image",
                            "local_storage",
                            "this_file",
                            "image"]
            }

        :param int note_id: The id for the note to be retrieved
        :param dict entity_fields: Additional fields to retrieve as part of the request.
            See above for details.
        :returns: A list of dictionaries. See above for example.
        :rtype: list
        """

        if self.server_caps.version and self.server_caps.version < (6, 2, 0):
                raise ShotgunError("note_thread requires server version 6.2.0 or "\
                    "higher, server is %s" % (self.server_caps.version,))

        entity_fields = entity_fields or {}
        
        if not isinstance(entity_fields, dict):
            raise ValueError("entity_fields parameter must be a dictionary")
        
        params = { "note_id": note_id, "entity_fields": entity_fields }

        record = self._call_rpc("note_thread_contents", params)
        result = self._parse_records(record)
        return result


    def text_search(self, text, entity_types, project_ids=None, limit=None):
        """
        Search across the specified entity types for the given text.

        This method can be used to implement auto completion or a Shotgun global search. The method
        requires a text input phrase that is at least three characters long, or an exception will
        be raised.

        Several ways to limit the results of the query are available:

        - Using the ``project_ids`` parameter, you can provide a list of Project ids to search
          across. Leaving this at its default value of ``None`` will search across all Shotgun data.

        - You need to define which subset of entity types to search using the ``entity_types``
          parameter. Each of these entity types can be associated with a filter query to further
          reduce the list of matches. The filter list is using the standard filter syntax used by
          for example the :meth:`~shotgun_api3.Shotgun.find` method.

        **Example: Constrain the search to all Tasks but Character Assets only**

        >>> entity_types = {
        ...     "Asset": [["sg_asset_type", "is", "Character"]],
        ...     "Task": []
        ... }
        >>> sg.text_search("bunny", entity_types)
        {'matches': [{'id': 734,
                      'type': 'Asset',
                      'name': 'Bunny',
                      'project_id': 65,
                      'image': 'https://...',
                      'links': ['', ''],
                      'status': 'fin'},
                      ...
                      {'id': 558,
                       'type': 'Task'
                       'name': 'FX',
                       'project_id': 65,
                       'image': 'https://...',
                       'links': ['Shot', 'bunny_010_0010'],
                       'status': 'fin'}],
            'terms': ['bunny']}

        The links field will contain information about any linked entity. This is useful when, for
        example, presenting Tasks and you want to display what Shot or Asset the Task is associated
        with.

        :param str text: Text to search for. This must be at least three characters long, or an
            exception will be raised.
        :param dict entity_types: Dictionary to specify which entity types to search across. See
            above for usage examples.
        :param list project_ids: List of Projects to search. By default, all projects will be
            searched.
        :param int limit: Specify the maximum number of matches to return.
        :returns: A complex dictionary structure, see above for example.
        :rtype: dict
        """
        if self.server_caps.version and self.server_caps.version < (6, 2, 0):
                raise ShotgunError("auto_complete requires server version 6.2.0 or "\
                    "higher, server is %s" % (self.server_caps.version,))
        
        # convert entity_types structure into the form 
        # that the API endpoint expects
        if not isinstance(entity_types, dict):
            raise ValueError("entity_types parameter must be a dictionary")
        
        api_entity_types = {}
        for (entity_type, filter_list) in entity_types.iteritems():

            if isinstance(filter_list, (list, tuple)):
                resolved_filters = _translate_filters(filter_list, filter_operator=None)
                api_entity_types[entity_type] = resolved_filters      
            else:
                raise ValueError("value of entity_types['%s'] must "
                                 "be a list or tuple." % entity_type)
            
        project_ids = project_ids or []

        params = { "text": text, 
                   "entity_types": api_entity_types,
                   "project_ids": project_ids,
                   "max_results": limit }

        record = self._call_rpc("query_display_name_cache", params)
        result = self._parse_records(record)[0]
        return result


    def activity_stream_read(self, entity_type, entity_id, entity_fields=None, min_id=None,
                             max_id=None, limit=None):
        """
        Retrieve activity stream data from Shotgun.

        This data corresponds to the data that is displayed in the
        Activity tab for an entity in the Shotgun Web UI.

        A complex data structure on the following form will be
        returned from Shotgun::

            {'earliest_update_id': 50,
             'entity_id': 65,
             'entity_type': 'Project',
             'latest_update_id': 79,
             'updates': [{'created_at': '2015-07-15 11:06:55 UTC',
                          'created_by': {'id': 38,
                                         'image': '6641',
                                         'name': 'John Smith',
                                         'status': 'act',
                                         'type': 'HumanUser'},
                          'id': 79,
                          'meta': {'entity_id': 6004,
                                   'entity_type': 'Version',
                                   'type': 'new_entity'},
                          'primary_entity': {'id': 6004,
                                             'name': 'Review_turntable_v2',
                                             'status': 'rev',
                                             'type': 'Version'},
                          'read': False,
                          'update_type': 'create'},
                         {...},
                        ]
            }

        The main payload of the return data can be found inside the 'updates'
        key, containing a list of dictionaries. This list is always returned
        in descending date order. Each item may contain different fields
        depending on their update type. The primary_entity key represents the
        main Shotgun entity that is associated with the update. By default,
        this entity is returned with a set of standard fields. By using the
        entity_fields parameter, you can extend the returned data to include
        additional fields. If for example you wanted to return the asset type
        for all assets and the linked sequence for all Shots, pass the
        following entity_fields::

            {"Shot": ["sg_sequence"], "Asset": ["sg_asset_type"]}

        Deep queries can be used in this syntax if you want to
        traverse into connected data.

        :param str entity_type: Entity type to retrieve activity stream for
        :param int entity_id: Entity id to retrieve activity stream for
        :param list entity_fields: List of additional fields to include.
                              See above for details
        :param int max_id: Do not retrieve ids greater than this id.
                       This is useful when implementing paging.
        :param int min_id: Do not retrieve ids lesser than this id.
                       This is useful when implementing caching of
                       the event stream data and you want to
                       "top up" an existing cache.
        :param int limit: Limit the number of returned records. If not specified,
                      the system default will be used.
        :returns: A complex activity stream data structure. See above for details.
        :rtype: dict
        """
        if self.server_caps.version and self.server_caps.version < (6, 2, 0):
                raise ShotgunError("activity_stream requires server version 6.2.0 or "\
                    "higher, server is %s" % (self.server_caps.version,))

        # set up parameters to send to server.
        entity_fields = entity_fields or {}
        
        if not isinstance(entity_fields, dict):
            raise ValueError("entity_fields parameter must be a dictionary")
        
        params = { "type": entity_type,
                   "id": entity_id,
                   "max_id": max_id,
                   "min_id": min_id,
                   "limit": limit,
                   "entity_fields": entity_fields }

        record = self._call_rpc("activity_stream", params)
        result = self._parse_records(record)[0]
        return result

    def nav_expand(self, path, seed_entity_field=None, entity_fields=None):
        """
        Expand the navigation hierarchy for the supplied path.

        .. warning::

            This is an experimental method that is not officially part of the
            python-api. Usage of this method is discouraged. This method's name,
            arguments, and argument types may change at any point.

        """
        return self._call_rpc(
            'nav_expand',
            {
                'path':path,
                'seed_entity_field': seed_entity_field,
                'entity_fields': entity_fields
            }
        )

    def get_session_token(self):
        """
        Get the session token associated with the current session.

        If a session token has already been established, this is returned, otherwise a new one is
        generated on the server and returned.

        >>> sg.get_session_token()
        dd638be7d07c39fa73d935a775558a50

        :returns: String containing a session token.
        :rtype: str
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
        """
        Build urllib2 opener with appropriate proxy handler.
        """
        if self.config.proxy_handler:
            opener = urllib2.build_opener(self.config.proxy_handler, handler)
        else:
            opener = urllib2.build_opener(handler)
        return opener

    def _turn_off_ssl_validation(self):
        """
        Turn off SSL certificate validation.
        """
        global NO_SSL_VALIDATION
        self.config.no_ssl_validation = True
        NO_SSL_VALIDATION = True
        # reset ssl-validation in user-agents
        self._user_agents = ["ssl %s (no-validate)" % self.client_caps.ssl_version 
                             if ua.startswith("ssl ") else ua 
                             for ua in self._user_agents] 

    # Deprecated methods from old wrapper
    def schema(self, entity_type):
        """
        .. deprecated:: 3.0.0
           Use :meth:`~shotgun_api3.Shotgun.schema_field_read` instead.
        """
        raise ShotgunError("Deprecated: use schema_field_read('type':'%s') "
            "instead" % entity_type)

    def entity_types(self):
        """
        .. deprecated:: 3.0.0
           Use :meth:`~shotgun_api3.Shotgun.schema_entity_read` instead.
        """
        raise ShotgunError("Deprecated: use schema_entity_read() instead")
    # ========================================================================
    # RPC Functions

    def _call_rpc(self, method, params, include_auth_params=True, first=False):
        """
        Call the specified method on the Shotgun Server sending the supplied payload.
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
        """
        Return a dictionary of the authentication parameters being used.
        """
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
                raise ShotgunError("Session token based authentication requires server version "
                    "5.3.0 or higher, server is %s" % (self.server_caps.version,))

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

        if self.config.extra_auth_params:
            auth_params.update(self.config.extra_auth_params)

        return auth_params

    def _sanitize_auth_params(self, params):
        """
        Given an authentication parameter dictionary, sanitize any sensitive
        information and return the sanitized dict copy.
        """
        sanitized_params = copy.copy(params)
        for k in ['user_password', 'script_key', 'session_token']:
            if k in sanitized_params:
                sanitized_params[k] = '********'
        return sanitized_params

    def _build_payload(self, method, params, include_auth_params=True):
        """
        Build the payload to be send to the rpc endpoint.
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
        """
        Encode the payload to a string to be passed to the rpc endpoint.

        The payload is json encoded as a unicode string if the content
        requires it. The unicode string is then encoded as 'utf-8' as it must
        be in a single byte encoding to go over the wire.
        """

        wire = json.dumps(payload, ensure_ascii=False)
        if isinstance(wire, unicode):
            return wire.encode("utf-8")
        return wire

    def _make_call(self, verb, path, body, headers):
        """
        Make an HTTP call to the server.

        Handles retry and failure.
        """

        attempt = 0
        req_headers = {}
        req_headers["user-agent"] = "; ".join(self._user_agents)
        if self.config.authorization:
            req_headers["Authorization"] = self.config.authorization

        req_headers.update(headers or {})
        body = body or None

        max_rpc_attempts = self.config.max_rpc_attempts

        while (attempt < max_rpc_attempts):
            attempt += 1
            try:
                return self._http_request(verb, path, body, req_headers)
            except SSLHandshakeError, e:
                # Test whether the exception is due to the fact that this is an older version of
                # Python that cannot validate certificates encrypted with SHA-2. If it is, then 
                # fall back on disabling the certificate validation and try again - unless the
                # SHOTGUN_FORCE_CERTIFICATE_VALIDATION environment variable has been set by the 
                # user. In that case we simply raise the exception. Any other exceptions simply 
                # get raised as well. 
                #
                # For more info see:
                # http://blog.shotgunsoftware.com/2016/01/important-ssl-certificate-renewal-and.html
                #
                # SHA-2 errors look like this: 
                #   [Errno 1] _ssl.c:480: error:0D0C50A1:asn1 encoding routines:ASN1_item_verify:
                #   unknown message digest algorithm
                # 
                # Any other exceptions simply get raised.
                if not str(e).endswith("unknown message digest algorithm") or \
                   "SHOTGUN_FORCE_CERTIFICATE_VALIDATION" in os.environ:
                    raise
                
                if self.config.no_ssl_validation is False:
                    LOG.warning("SSLHandshakeError: this Python installation is incompatible with "
                                "certificates signed with SHA-2. Disabling certificate validation. "
                                "For more information, see http://blog.shotgunsoftware.com/2016/01/"
                                "important-ssl-certificate-renewal-and.html")
                    self._turn_off_ssl_validation()
                    # reload user agent to reflect that we have turned off ssl validation
                    req_headers["user-agent"] = "; ".join(self._user_agents)
                
                self._close_connection()
                if attempt == max_rpc_attempts:
                    raise
            except Exception:
                #TODO: LOG ?
                self._close_connection()
                if attempt == max_rpc_attempts:
                    raise

    def _http_request(self, verb, path, body, headers):
        """
        Make the actual HTTP request.
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
        """
        Parse the status returned from the http request.

        :param tuple status: Tuple of (code, reason).
        :raises: RuntimeError if the http status is non success.
        """
        error_code = status[0]
        errmsg = status[1]

        if status[0] >= 300:
            headers = "HTTP error from server"
            if status[0] == 503:
                errmsg = "Shotgun is currently down for maintenance or too busy to reply. Please " \
                         "try again later."
            raise ProtocolError(self.config.server,
                                error_code,
                                errmsg,
                                headers)

        return

    def _decode_response(self, headers, body):
        """
        Decode the response from the server from the wire format to
        a python data structure.

        :param dict headers: Headers from the server.
        :param str body: Raw response body from the server.
        :returns: If the content-type starts with application/json or
            text/javascript the body is json decoded. Otherwise the raw body is
            returned.
        :rtype: str
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
        """
        See http://stackoverflow.com/questions/956867
        """
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
        """
        Raise any API errors specified in the response.

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
        """
        Walk the data (simple python types) and call the visitor.
        """

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
        """
        Transform data types or values before they are sent by the client.

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
        """
        Transforms data types or values after they are received from the server.
        """
        # NOTE: The time zone is removed from the time after it is transformed
        # to the local time, otherwise it will fail to compare to datetimes
        # that do not have a time zone.
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
        """
        Return the current connection or creates a new connection to the current server.
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
        """
        Close the current connection.
        """
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
        """
        Parse 'records' returned from the api to do local modifications:

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
        """
        Return the URL for the thumbnail of an entity given the entity type and the entity id.

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

        # code of 0 means error, second line is the error code
        if code == 0:
            raise ShotgunError(thumb_url)

        if code == 1:
            return urlparse.urlunparse((self.config.scheme,
                self.config.server, thumb_url.strip(), None, None, None))

        # Comments in prev version said we can get this sometimes.
        raise RuntimeError("Unknown code %s %s" % (code, thumb_url))

    def _dict_to_list(self, d, key_name="field_name", value_name="value", extra_data=None):
        """
        Utility function to convert a dict into a list dicts using the key_name and value_name keys.

        e.g. d {'foo' : 'bar'} changed to [{'field_name':'foo', 'value':'bar'}]

        Any dictionary passed in via extra_data will be merged into the resulting dictionary.
        e.g. d as above and extra_data of {'foo': {'thing1': 'value1'}} changes into
        [{'field_name': 'foo', 'value': 'bar', 'thing1': 'value1'}]
        """
        ret = []
        for k, v in (d or {}).iteritems():
            d = {key_name: k, value_name: v}
            d.update((extra_data or {}).get(k, {}))
            ret.append(d)
        return ret

    def _dict_to_extra_data(self, d, key_name="value"):
        """
        Utility function to convert a dict into a dict compatible with the extra_data arg
        of _dict_to_list.

        e.g. d {'foo' : 'bar'} changed to {'foo': {"value": 'bar'}]
        """
        return dict([(k, {key_name: v}) for (k,v) in (d or {}).iteritems()])

    def _send_form(self, url, params):
        """
        Utility function to send a Form to Shotgun and process any HTTP errors that
        could occur.

        :param url: endpoint where the form is sent.
        :param params: form data
        :returns: result from the server.
        """
        opener = self._build_opener(FormPostHandler)

        # Perform the request
        try:
            resp = opener.open(url, params)
            result = resp.read()
            # response headers are in str(resp.info()).splitlines()
        except urllib2.HTTPError, e:
            if e.code == 500:
                raise ShotgunError("Server encountered an internal error. "
                                   "\n%s\n(%s)\n%s\n\n" % (url, self._sanitize_auth_params(params), e))
            else:
                raise ShotgunError("Unanticipated error occurred %s" % (e))

        return result

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
    """
    Translate filters params into data structure expected by rpc call.
    """
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
        raise ShotgunError("Invalid filters, expected a list or a tuple, got %s"
                           % sg_filter["filters"])

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
            raise ShotgunError("Invalid filters, expected a list, tuple or dict, got %s"
                               % sg_filter)

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
    """
    Convert a tuple of int's to a '.' separated str.
    """
    return '.'.join(map(str, version))
