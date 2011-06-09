#!/usr/bin/env python
# ---------------------------------------------------------------------------------------------
# Copyright (c) 2009-2011, Shotgun Software Inc
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  - Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  - Neither the name of the Shotgun Software Inc nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

__version__ = "3.1a1"

# needed for httplib2, future imports must be first
from __future__ import generators

import base64
import cookielib    # used for attachment upload
import cStringIO    # used for attachment upload
import datetime
import logging
import mimetools    # used for attachment upload
import mimetypes    # used for attachment upload
import os
import platform
import re
import stat         # used for attachment upload
import sys
import time
import urllib
import urllib2      # used for image upload
import urlparse

log = logging.getLogger("shotgun_api3")

try:
    import simplejson as json
except ImportError:
    log.debug("simplejson not found, dropping back to json")
    import json as json 

# ----------------------------------------------------------------------------
# Errors

class ShotgunError(Exception):
    """Base for all Shotgun API Errors"""
    pass

class Fault(ShotgunError):
    pass
    
# ----------------------------------------------------------------------------
# API

class ServerCapabilities(object):
    
    def __init__(self, host, meta):
        """Container for the servers capabilities, such as version and 
        paging. 
        
        :param host: Host name for the server excluding protocol.
        
        :param meta: dict of meta data for the server returned from the 
        info api method. 
        """
        
        #Server host name
        self.host = host
        try:
            meta = dict(meta)
        except ValueError:
            meta = {}
        self.server_info = meta
        
        #Version from server is major.minor.rev or major.minor.rev."Dev"
        #Store version as triple and check dev flag
        self.version = meta.get("version", None)
        if not self.version:
            self.version = (0,0,0)
            self.is_dev = False
        else:
            if len(self.version) > 3 and self.version[3] == "Dev":
                self.is_dev = True 
            else:
                self.is_dev = False
            self.version = tuple(self.version[:3])
        
        self._ensure_json_supported()
        
        #Flag if this server supports paging
        self.has_paging = self._is_paging(self.version)
    
    def _ensure_json_supported(self):
        """Checks the server version supports the JSON api, raises an 
        exception if it does not.
        
        :raises ShotgunError: The current server version does not support json
        """
        
        if not self.version or self.version < (2,4,0):
            raise ShotgunError("JSON API requires server version 2.4 or "\
                "higher, server is %s" % (self.version,))
        return 
    def _is_paging(self, version):
        """Determines if the server version supports paging.
        
        :param version: Version to check. 
        
        :returns: True if the server supports paging, False otherwise.
        """
        if version >= (2, 3, 4):
            return True
        return False
        
    def __str__(self):
        return "ServerCapabilities: host %s, version %s, is_dev %s, "\
            "has_paging %s" % (self.host, self.version, self.is_dev, 
            self.has_paging)
            
class ClientCapabilities(object):
    
    def __init__(self):
        """Container for the client capabilities.
        
        Detects the current client platform and works out the SG field 
        used for local data paths.
        """
        
        system = platform.system().lower()
        if system =='darwin':
            self.platform = "mac"
        elif system in ('windows','linux'):
            self.platform = system
        else:
            self.platform = None
        
        if self.platform:
            self.local_path_field = "local_path_%s" % (self.platform) 
        else:
            self.local_path_field = None
        
        self.py_version = ".".join( str(x) for x in sys.version_info[:2])

    def __str__(self):
        return "ClientCapabilities: platform %s, local_path_field %s, "\
            "py_verison %s" % (self.platform, self.local_path_field, 
            self.py_version)

class _Config(object):

    def __init__(self):
        """Container for the client configuration."""
        
        self.max_rpc_attempts = 3
        self.timeout_secs = 3
        self.api_ver = 'api3'
        self.convert_datetimes_to_utc = True
        self.records_per_page = 500
        self.api_key = None
        self.script_name = None
        # uuid as a string
        self.session_uuid = None
        self.scheme = None
        self.server = None
        self.api_path = None
        self.proxy_server = None
        self.proxy_port = None
        self.session_token = None
        self.authorization = None
        
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
            
    def __init__(self, base_url, script_name, api_key, 
        convert_datetimes_to_utc=True, http_proxy=None):
        """Initialises a new instance of the Shotgun client.
        
        :param base_url: http or https url to the shotgun server.
        
        :param script_name: name of the client script, used to authenticate 
        to the server.
        
        :param api_key: key assigned to the client script, used to 
        authenticate to the server.
        
        :param convert_datetimes_to_utc: If True date time values are 
        converted from local time to UTC time before been sent to the server. 
        Datetimes received from the server are converted back to local time. 
        If False the client should use UTC date time values.
        Default is True.
        
        :param http_proxy: Optional, URL for the http proxy server, of the
        form http://proxy.com:8080 
        """
        
        self.config = _Config()
        self.config.api_key = api_key
        self.config.script_name = script_name
        self.config.convert_datetimes_to_utc = convert_datetimes_to_utc
        self.config.proxy_info = http_proxy
        
        self._connection = None
        
        base_url = (base_url or "").lower()
        self.config.scheme, self.config.server, api_base, _, _ = \
            urlparse.urlsplit(base_url)
        if self.config.scheme not in ("http", "https"):
            raise ValueError("base_url must use http or https got '%s'" % 
                base_url)
        self.config.api_path = urlparse.urljoin(urlparse.urljoin(
            api_base or "/", self.config.api_ver + "/"), "json")
        
        # if the service contains user information strip it out 
        # copied from the xmlrpclib which turned the user:password into 
        # and auth header
        auth, self.config.server = urllib.splituser(self.config.server)
        if auth:
            auth = base64.encodestring(urllib.unquote(auth))
            self.config.authorization = "Basic " + auth.strip()

        if http_proxy:
            _, proxy_netloc, _, _, _ = urlparse.urlsplit(http_proxy)
            self.config.proxy_server, _, proxy_port = proxy_netloc.partition(
                ":")
            self.config.proxy_port = int(proxy_port or 8080)
            
        self.client_caps = ClientCapabilities()
        self._server_caps = None
        #test to ensure the the server supports the json API
        #call to server will only be made once and will raise error
        sc = self.server_caps
        
    # ========================================================================
    # API Functions 
    
    @property
    def server_info(self):
        return self.server_caps.server_info
        
    @property
    def server_caps(self):
        """
        :returns: ServerCapabilities that describe the server the client is 
        connected to.
        """
        if not self._server_caps or (
            self._server_caps.host != self.config.server):
            self._server_caps =  ServerCapabilities(self.config.server, 
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
        
        return self._call_rpc("info", None, include_script_name=False)

    def find_one(self, entity_type, filters, fields=None, order=None, 
        filter_operator=None, retired_only=False):
        """Calls the find() method and returns the first result, or None.
        
        The params are the same as for find().
        """
        
        results = self.find(entity_type, filters, fields, order, 
            filter_operator, 1, retired_only)
        
        if results:
            return results[0]
        return None

    def find(self, entity_type, filters, fields=None, order=None, 
        filter_operator=None, limit=0, retired_only=False, page=0):
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
        
        :returns: list of the dicts for each entity with the requested fields,
        and their id and type. 
        """
        
        if not isinstance(limit, int) or limit < 0:
           raise ValueError("limit parameter must be a positive integer")

        if not isinstance(page, int) or page < 0:
            raise ValueError("page parameter must be a positive integer")

        if isinstance(filters, (list, tuple)):
            new_filters = {}
            
            if not filter_operator or filter_operator == "all":
                new_filters["logical_operator"] = "and"
            else:
                new_filters["logical_operator"] = "or"
            
            new_filters["conditions"] = [
                {"path" : f[0], "relation" : f[1], "values" : f[2:]}
                for f in filters
            ]
            
            filters = new_filters
        elif filter_operator:
            #TODO:Not sure if this test is correct, replicated from prev api 
            raise ShotgunError("Deprecated: Use of filter_operator for find()"
                " is not valid any more. See the documentation on find()")
                
        params = {
            "type" : entity_type,
            "return_fields": fields or ["id"],
            "filters": filters,
            "return_only" : (retired_only and 'retired') or "active",
            "paging": {
                "entities_per_page": self.config.records_per_page, 
                "current_page": 1
            }
        }

        if self.server_caps.has_paging:
            params["return_paging_info"] = True

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
           
        if limit and limit <= self.config.records_per_page:
            params["paging"]["entities_per_page"] = limit
            # If page isn't set and the limit doesn't require pagination, 
            # then trigger the faster code path.
            if page == 0:
                page = 1
        
        # if page is specified, then only return the page of records requested
        if page != 0:
            # No paging_info needed, so optimize it out.
            if self.server_caps.has_paging:
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

    def create(self, entity_type, data, return_fields=None):
        """Create a new entity of the specified entity_type.
        
        :param entity_type: Required, entity type (string) to create.
        
        :param data: Required, dict fields to set on the new entity. 
        
        :param return_fields: Optional list of fields from the new entity 
        to return. Defaults to 'id' field.
        
        :returns: dict of the requested fields.
        """
        
        params = {
            "type" : entity_type,
            "fields" : self._dict_to_list(data),
            "return_fields" : return_fields or ["id"]
        }
        
        record = self._call_rpc("create", params, first=True)
        return self._parse_records(record)[0]
        
    def update(self, entity_type, entity_id, data):
        """Updates the specified entity with the supplied data.
        
        :param entity_type: Required, entity type (string) to update.

        :param entity_id: Required, id of the entity to update.
        
        :param data: Required, dict fields to update on the entity. 
        
        :returns: dict of the fields updated, with the entity_type and 
        id added.
        """
        
        params = {
            "type" : entity_type,
            "id" : entity_id,
            "fields" : self._dict_to_list(data)
        }
        
        record = self._call_rpc("update", params)
        return self._parse_records(record)[0]

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

        calls = []

        def _required_keys(message, required_keys, data):
            if set(required_keys) - set(data.keys()):
                raise ShotgunError("%s missing required key: %s. "\
                    "Value was: %s." % (message, ", ".join(missing), data))

        for req in requests:
            _required_keys("Batched request", ['request_type','entity_type'], 
                req)

            if req["request_type"] == "create":
                _required_keys("Batched create request", ['data'], req)

                calls.append({
                    "request_type" : "create",
                    "type" : req["entity_type"],
                    "fields" : self._dict_to_list(req["data"]), 
                    "return_fields" : req.get("return_fields") or["id"]
                })
                
            elif req["request_type"] == "update":
                _required_keys("Batched update request", ['entity_id','data'],
                    req)

                calls.append({
                    "request_type" : "update",
                    "type" : req["entity_type"],
                    "id" : req["entity_id"],
                    "fields" : self._dict_to_list(req["data"]), 
                })

            elif req["request_type"] == "delete":
                _required_keys("Batched delete request", ['entity_id'], req)

                calls.append({
                    "request_type" : "delete",
                    "type" : req["entity_type"],
                    "id" : req["entity_id"],
                })
            
            else:
                raise ShotgunError("Invalid request_type '%s' for batch" % (
                    req["request_type"]))

        records = self._call_rpc("batch", calls)
        return self._parse_records(records)
        
    def schema_entity_read(self):
        """Gets all active entities defined in the schema. 
        
        :returns: dict of Entity Type to dict containing the display name. 
        """
        
        return self._call_rpc("schema_entity_read", None)
                
    def schema_read(self):
        """Gets the schema for all fields in all entities.
        
        :returns: nested dicts
        """
        
        return self._call_rpc("schema_read", None)

    def schema_field_read(self, entity_type, field_name=None):
        """Gets all schema for fields in the specified entity_type or one 
        field.
        
        :param entity_type: Required, entity type (string) to get the schema 
        for.
        
        :param field_name: Optional, name of the field to get the schema 
        definition for. If not supplied all fields for the entity type are 
        returned.
        
        :returns: dict of field name to nested dicts which describe the field 
        """
        
        params = {
            "type" : entity_type,
        }
        if field_name:
            params["field_name"] = field_name
            
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
                for k,v in (properties or {}).iteritems()
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

    def set_session_uuid(self, session_uuid):
        """Sets the browser session_uuid for this API session. 
        
        Once set events generated by this API session will include the 
        session_uuid in their EventLogEntries. 
        
        :param session_uuid: Session UUID to set. 
        """
        
        self.config.session_uuid = session_uuid
        return
        

    def upload_thumbnail(self, entity_type, entity_id, path, **kwargs):
        """Convenience function for uploading thumbnails, see upload.
        """
        return self.upload(entity_type, entity_id, path, 
            field_name="thumb_image", **kwargs)

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
        
        is_thumbnail = (field_name == "thumb_image")
        
        params = {
            "entity_type" : entity_type,
            "entity_id" : entity_id,
            "script_name" : self.config.script_name,
            "script_key" : self.config.api_key,
        }
        if self.config.session_uuid:
            params["session_uuid"] = self.config.session_uuid
        
        if is_thumbnail:
            url = urlparse.urlunparse((self.config.scheme, self.config.server,
                "/upload/publish_thumbnail", None, None, None))
            params["thumb_image"] = open(path, "rb")
            
        else:
            url = urlparse.urlunparse((self.config.scheme, self.config.server,
                "/upload/upload_file", None, None, None))
            if display_name is None:
                display_name = os.path.basename(path)
            # we allow linking to nothing for generic reference use cases
            if field_name is not None:
                params["field_name"] = field_name
            params["display_name"] = display_name
            params["tag_list"] = tag_list
            params["file"] = open(path, "rb")
        
        # Create opener with extended form post support
        opener = urllib2.build_opener(FormPostHandler)
        
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
        
        # we changed the result string in the middle of 1.8 to return the id
        # remove once everyone is > 1.8.3
        r = str(result).split(":")
        id = 0
        if len(r) > 1:
            id = int(str(result).split(":")[1].split("\n")[0])
        return id
    
    def download_attachment(self, attachment_id):
        """Gets the returns binary content of the specified attachment.
        
        :param attachment_id: id of the attachment to get. 
        
        :returns: binary data as a string
        """
        
        sid = self._get_session_token()
        cj = cookielib.LWPCookieJar()
        c = cookielib.Cookie('0', '_session_id', sid, None, False, 
            self.config.server, False, False, "/", True, False, None, True, 
            None, None, {})
        cj.set_cookie(c)
        cookie_handler = urllib2.HTTPCookieProcessor(cj)
        urllib2.install_opener(urllib2.build_opener(cookie_handler))
        url = urlparse.urlunparse((self.config.scheme, self.config.server, 
            "/file_serve/%s" % urllib.quote(str(attachment_id)), 
            None, None, None))
        
        try:
            request = urllib2.Request(url)
            request.add_header('User-agent',
                "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US; "\
                "rv:1.9.0.7) Gecko/2009021906 Firefox/3.0.7")
            attachment = urllib2.urlopen(request).read()
        
        except IOError, e:
            err = "Failed to open %s" % url
            if hasattr(e, 'code'):
                err += "\nWe failed with error code - %s." % e.code
            elif hasattr(e, 'reason'):
                err += "\nThe error object has the following 'reason' "\
                    "attribute :", e.reason
                err += "\nThis usually means the server doesn't exist, is "\
                    "down, or we don't have an internet connection."
            raise ShotgunError(err)
        else:
            if attachment.lstrip().startswith('<!DOCTYPE '):
                error_string = "\n%s\nThe server generated an error trying "\
                    "to download the Attachment. \nURL: %s\n"\
                    "Either the file doesn't exist, or it is a local file "\
                    "which isn't downloadable.\n%s\n" % ("="*30, url, "="*30)
                raise ShotgunError(error_string)
        return attachment

    def _get_session_token(self):
        """Hack to authenticate in order to download protected content
        like Attachments
        """
        if self.config.session_token:
            return self.config.session_token
        
        rv = self._call_rpc("get_session_token", None)
        session_token = (rv or {}).get("session_id")
        if not session_token:
            raise RuntimeError("Could not extract session_id from %s", rv)
        
        self.config.session_token = session_token
        return self.config.session_token
        
    # Deprecated methods from old wrapper
    def schema(self, entity_type):
        raise ShotgunError("Deprecated: use schema_field_read('type':'%s') "
            "instead" % entity_type)
    
    def entity_types(self):
        raise ShotgunError("Deprecated: use schema_entity_read() instead")        
    # ========================================================================
    # RPC Functions 

    def _call_rpc(self, method, params, include_script_name=True, 
        first=False):
        """Calls the specified method on the Shotgun Server sending the 
        supplied payload. 
        
        """
        
        log.debug("Starting rpc call to %s with params %s" % (
            method, params))
            
        params = self._transform_outbound(params)
        payload = self._build_payload(method, params, 
            include_script_name=include_script_name)
        encoded_payload = self._encode_payload(payload)
        
        req_headers = {
            "content-type" : "application/json; charset=utf-8",
            "connection" : "keep-alive"
        }
        http_status, resp_headers, body = self._make_call("POST", 
            self.config.api_path, encoded_payload, req_headers)
        log.info("Completed rpc call to %s" % (method))
                
        self._parse_http_status(http_status)
        response = self._decode_response(resp_headers, body)
        self._response_errors(response)
        response = self._transform_inbound(response)
        
        if not isinstance(response, dict) or "results" not in response:
            return response
            
        results = response.get("results")
        if first and isinstance(results, list):
            return results[0] 
        return results

    def _build_payload(self, method, params, include_script_name=True):
        """Builds the payload to be send to the rpc endpoint.
        
        """
        if not method:
            raise ValueError("method is empty")
        
        call_params = []
        if include_script_name:
            if not self.config.script_name:
                raise ValueError("script_name is empty")
            if not self.config.api_key:
                raise ValueError("api_key is empty")
            auth_params = {
                "script_name" : str(self.config.script_name), 
                "script_key" : str(self.config.api_key), 
            }
            if self.config.session_uuid:
                auth_params["session_uuid"] = self.config.session_uuid
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
            "user-agent" : "shotgun-json",
        }
        if self.config.authorization:
            req_headers["Authorization"] = self.config.authorization

        req_headers.update(headers or {})
        body = body or None
        
        max_rpc_attempts = self.config.max_rpc_attempts
        
        while (attempt < max_rpc_attempts):            
            attempt +=1
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
        log.debug("Request is %s:%s" % (verb, url))
        log.debug("Request headers are %s" % headers)
        log.debug("Request body is %s" % body)
        
        conn = self._get_connection()
        resp, content = conn.request(url,method=verb, body=body, 
            headers=headers)
        #http response code is handled else where
        http_status = (resp.status, resp.reason)
        resp_headers = dict(
            (k.lower(), v)
            for k,v in resp.iteritems()
        )
        resp_body = content
        
        log.debug("Response status is %s %s" % http_status)
        log.debug("Response headers are %s" % resp_headers)
        log.debug("Response body is %s" % resp_body)
        
        return (http_status, resp_headers, resp_body)
        
    def _parse_http_status(self, status):
        """Parse the status returned from the http request. 
        
        :raises: RuntimeError if the http status is non success.
         
        :param status: Tuple of (code, reason).
        """
        
        if status[0] >= 300:
            raise RuntimeError("HTTP error from server %s %s" % status)
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
        
        if ct.startswith("application/json") or \
            ct.startswith("text/javascript"):
            return json.loads(body)
            
        return body

    def _response_errors(self, sg_response):
        """Raises any API errors specified in the response.
        
        :raises ShotgunError: If the server response contains an exception.
        """
        
        if isinstance(sg_response, dict) and sg_response.get("exception"):
            raise Fault(sg_response.get("message", 
                "Unknown Error"))
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
                for k,v in data.iteritems()
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
                if value.tzinfo == None:
                    value = value.replace(tzinfo=sg_timezone.local)
                return value.astimezone(sg_timezone.utc)
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
            
            return value
            
        return self._visit_data(data, _outbound_visitor)

    def _transform_inbound(self, data):
        """Transforms data types or values after they are received from the 
        server."""
        
        #NOTE: The time zone is removed from the time after it is transformed 
        #to the local time, otherwise it will fail to compare to datetimes 
        #that do not have a time zone.
        if self.config.convert_datetimes_to_utc:
            _change_tz = lambda x: x.replace(tzinfo=sg_timezone.utc)\
                .astimezone(sg_timezone.local)\
                .replace(tzinfo=None)
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
            pi = ProxyInfo(PROXY_TYPE_HTTP, self.config.proxy_server, 
                self.config.proxy_port)
            self._connection = Http(timeout=self.config.timeout_secs, 
                proxy_info=pi)
        else:
            self._connection = Http(timeout=self.config.timeout_secs)
        
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
        """Parses 'records' returned from the api to insert thumbnail urls
        or local file paths.
        
        :param records: List of records (dicts) to process or a single record.
        
        :returns: A list of the records processed. 
        """
        
        if not records:
            return []
        
        if not isinstance(records, (list, tuple)):
            records=[records,]
            
        for rec in records:
            # skip results that aren't entity dictionaries
            if not isinstance(rec, dict):
                continue
                
            # iterate over each item and check each field for possible injection
            for k, v in rec.iteritems():
                if not v:
                    continue
                    
                # check for thumbnail
                if k == 'image':
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

        url = "/upload/get_thumbnail_url?entity_type=%s&entity_id=%s" % (
            urllib.quote(entity_type), urllib.quote(str(entity_id)))
            
        _, _, body = self._make_call("GET", url, None, None)
        
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
            for k,v in (d or {}).iteritems()
        ]







# ----------------------------------------------------------------------------
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
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            buffer.write('--%s\r\n' % boundary)
            buffer.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename))
            buffer.write('Content-Type: %s\r\n' % content_type)
            buffer.write('Content-Length: %s\r\n' % file_size)
            fd.seek(0)
            buffer.write('\r\n%s\r\n' % fd.read())
        buffer.write('--%s--\r\n\r\n' % boundary)
        buffer = buffer.getvalue()
        return boundary, buffer
    
    def https_request(self, request):
        return self.http_request(request)



# ----------------------------------------------------------------------------
#  SG_TIMEZONE module
#  this is rolled into the this shotgun api file to avoid having to require 
#  current users of api2 to install new modules and modify PYTHONPATH info.
# ----------------------------------------------------------------------------

class SgTimezone(object):
    from datetime import tzinfo, timedelta, datetime
    import time as _time

    ZERO = timedelta(0)
    STDOFFSET = timedelta(seconds = -_time.timezone)
    if _time.daylight:
        DSTOFFSET = timedelta(seconds = -_time.altzone)
    else:
        DSTOFFSET = STDOFFSET
    DSTDIFF = DSTOFFSET - STDOFFSET
    
    def __init__(self): 
        self.utc = self.UTC()
        self.local = self.LocalTimezone()
    
    class UTC(tzinfo):
        
        def utcoffset(self, dt):
            return SgTimezone.ZERO
        
        def tzname(self, dt):
            return "UTC"
        
        def dst(self, dt):
            return SgTimezone.ZERO
    
    class LocalTimezone(tzinfo):
        
        def utcoffset(self, dt):
            if self._isdst(dt):
                return SgTimezone.DSTOFFSET
            else:
                return SgTimezone.STDOFFSET
        
        def dst(self, dt):
            if self._isdst(dt):
                return SgTimezone.DSTDIFF
            else:
                return SgTimezone.ZERO
        
        def tzname(self, dt):
            return _time.tzname[self._isdst(dt)]
        
        def _isdst(self, dt):
            tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
            import time as _time
            stamp = _time.mktime(tt)
            tt = _time.localtime(stamp)
            return tt.tm_isdst > 0

sg_timezone = SgTimezone()















# ----------------------------------------------------------------------------
# Included external modules, left as is or otherwise noted here an in the code
# search for "amorton"
#
# - httplib2: contents from __init__.py and iri2uri.py
#       - removed reference to the socks module, it is included directly. 
#       - set TCP_NODELAY on the sockets see 
#           http://code.google.com/p/httplib2/issues/detail?id=28
#       - patch to handle socket not opening applied 
#       see http://code.google.com/p/httplib2/source/detail?r=0cff83696d
# - socks module from http://socksipy.sourceforge.net/
#

# ----------------------------------------------------------------------------
# httplib2/iri2uri.py

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
# 
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
   (0xA0, 0xD7FF ),
   (0xE000, 0xF8FF ),
   (0xF900, 0xFDCF ),
   (0xFDF0, 0xFFEF),
   (0x10000, 0x1FFFD ),
   (0x20000, 0x2FFFD ),
   (0x30000, 0x3FFFD),
   (0x40000, 0x4FFFD ),
   (0x50000, 0x5FFFD ),
   (0x60000, 0x6FFFD),
   (0x70000, 0x7FFFD ),
   (0x80000, 0x8FFFD ),
   (0x90000, 0x9FFFD),
   (0xA0000, 0xAFFFD ),
   (0xB0000, 0xBFFFD ),
   (0xC0000, 0xCFFFD),
   (0xD0000, 0xDFFFD ),
   (0xE1000, 0xEFFFD),
   (0xF0000, 0xFFFFD ),
   (0x100000, 0x10FFFD)
]
 
def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be 
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function.""" 
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8 
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri

# ----------------------------------------------------------------------------
# httplib2/__init__.py


#  HACK: Amorton: future import moved to top of file
"""
httplib2

A caching http interface that supports ETags and gzip
to conserve bandwidth. 

Requires Python 2.3 or later

Changelog:
2007-08-18, Rick: Modified so it's able to use a socks proxy if needed.

"""

__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = ["Thomas Broyer (t.broyer@ltgt.net)",
    "James Antill",
    "Xavier Verges Farrero",
    "Jonathan Feinberg",
    "Blair Zajac",
    "Sam Ruby",
    "Louis Nyffenegger"]
__license__ = "MIT"
__version__ = "$Rev$"

import re 
import sys 
import email
import email.Utils
import email.Message
import email.FeedParser
import StringIO
import gzip
import zlib
import httplib
import urlparse
import base64
import os
import copy
import calendar
import time
import random
# remove depracated warning in python2.6
try:
    from hashlib import sha1 as _sha, md5 as _md5
except ImportError:
    import sha
    import md5
    _sha = sha.new
    _md5 = md5.new
import hmac
from gettext import gettext as _
import socket

# HACK: amorton sock module is included in this file now
# try:
#     import socks
# except ImportError:
#     socks = None

# Build the appropriate socket wrapper for ssl
try:
    import ssl # python 2.6
    _ssl_wrap_socket = ssl.wrap_socket
except ImportError:
    def _ssl_wrap_socket(sock, key_file, cert_file):
        ssl_sock = socket.ssl(sock, key_file, cert_file)
        return httplib.FakeSocket(sock, ssl_sock)


if sys.version_info >= (2,3):
    # amorton: code pulled into this file, see above
    #from iri2uri import iri2uri
    pass
else:
    def iri2uri(uri):
        return uri

def has_timeout(timeout): # python 2.6
    if hasattr(socket, '_GLOBAL_DEFAULT_TIMEOUT'):
        return (timeout is not None and timeout is not socket._GLOBAL_DEFAULT_TIMEOUT)
    return (timeout is not None)

__all__ = ['Http', 'Response', 'ProxyInfo', 'HttpLib2Error',
  'RedirectMissingLocation', 'RedirectLimit', 'FailedToDecompressContent', 
  'UnimplementedDigestAuthOptionError', 'UnimplementedHmacDigestAuthOptionError',
  'debuglevel']


# The httplib debug level, set to a non-zero value to get debug output
debuglevel = 0


# Python 2.3 support
if sys.version_info < (2,4):
    def sorted(seq):
        seq.sort()
        return seq

# Python 2.3 support
def HTTPResponse__getheaders(self):
    """Return list of (header, value) tuples."""
    if self.msg is None:
        raise httplib.ResponseNotReady()
    return self.msg.items()

if not hasattr(httplib.HTTPResponse, 'getheaders'):
    httplib.HTTPResponse.getheaders = HTTPResponse__getheaders

# All exceptions raised here derive from HttpLib2Error
class HttpLib2Error(Exception): pass

# Some exceptions can be caught and optionally 
# be turned back into responses. 
class HttpLib2ErrorWithResponse(HttpLib2Error):
    def __init__(self, desc, response, content):
        self.response = response
        self.content = content
        HttpLib2Error.__init__(self, desc)

class RedirectMissingLocation(HttpLib2ErrorWithResponse): pass
class RedirectLimit(HttpLib2ErrorWithResponse): pass
class FailedToDecompressContent(HttpLib2ErrorWithResponse): pass
class UnimplementedDigestAuthOptionError(HttpLib2ErrorWithResponse): pass
class UnimplementedHmacDigestAuthOptionError(HttpLib2ErrorWithResponse): pass

class RelativeURIError(HttpLib2Error): pass
class ServerNotFoundError(HttpLib2Error): pass

# Open Items:
# -----------
# Proxy support

# Are we removing the cached content too soon on PUT (only delete on 200 Maybe?)

# Pluggable cache storage (supports storing the cache in
#   flat files by default. We need a plug-in architecture
#   that can support Berkeley DB and Squid)

# == Known Issues ==
# Does not handle a resource that uses conneg and Last-Modified but no ETag as a cache validator.
# Does not handle Cache-Control: max-stale
# Does not use Age: headers when calculating cache freshness.


# The number of redirections to follow before giving up.
# Note that only GET redirects are automatically followed.
# Will also honor 301 requests by saving that info and never
# requesting that URI again.
DEFAULT_MAX_REDIRECTS = 5

# Which headers are hop-by-hop headers by default
HOP_BY_HOP = ['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade']

def _get_end2end_headers(response):
    hopbyhop = list(HOP_BY_HOP)
    hopbyhop.extend([x.strip() for x in response.get('connection', '').split(',')])
    return [header for header in response.keys() if header not in hopbyhop]

URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")

def parse_uri(uri):
    """Parses a URI using the regex given in Appendix B of RFC 3986.

        (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    groups = URI.match(uri).groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])

def urlnorm(uri):
    (scheme, authority, path, query, fragment) = parse_uri(uri)
    if not scheme or not authority:
        raise RelativeURIError("Only absolute URIs are allowed. uri = %s" % uri)
    authority = authority.lower()
    scheme = scheme.lower()
    if not path: 
        path = "/"
    # Could do syntax based normalization of the URI before
    # computing the digest. See Section 6.2.2 of Std 66.
    request_uri = query and "?".join([path, query]) or path
    scheme = scheme.lower()
    defrag_uri = scheme + "://" + authority + request_uri
    return scheme, authority, request_uri, defrag_uri


# Cache filename construction (original borrowed from Venus http://intertwingly.net/code/venus/)
re_url_scheme    = re.compile(r'^\w+://')
re_slash         = re.compile(r'[?/:|]+')

def safename(filename):
    """Return a filename suitable for the cache.

    Strips dangerous and common characters to create a filename we
    can use to store the cache in.
    """

    try:
        if re_url_scheme.match(filename):
            if isinstance(filename,str):
                filename = filename.decode('utf-8')
                filename = filename.encode('idna')
            else:
                filename = filename.encode('idna')
    except UnicodeError:
        pass
    if isinstance(filename,unicode):
        filename=filename.encode('utf-8')
    filemd5 = _md5(filename).hexdigest()
    filename = re_url_scheme.sub("", filename)
    filename = re_slash.sub(",", filename)

    # limit length of filename
    if len(filename)>200:
        filename=filename[:200]
    return ",".join((filename, filemd5))

NORMALIZE_SPACE = re.compile(r'(?:\r\n)?[ \t]+')
def _normalize_headers(headers):
    return dict([ (key.lower(), NORMALIZE_SPACE.sub(value, ' ').strip())  for (key, value) in headers.iteritems()])

def _parse_cache_control(headers):
    retval = {}
    if headers.has_key('cache-control'):
        parts =  headers['cache-control'].split(',')
        parts_with_args = [tuple([x.strip().lower() for x in part.split("=", 1)]) for part in parts if -1 != part.find("=")]
        parts_wo_args = [(name.strip().lower(), 1) for name in parts if -1 == name.find("=")]
        retval = dict(parts_with_args + parts_wo_args)
    return retval 

# Whether to use a strict mode to parse WWW-Authenticate headers
# Might lead to bad results in case of ill-formed header value,
# so disabled by default, falling back to relaxed parsing.
# Set to true to turn on, usefull for testing servers.
USE_WWW_AUTH_STRICT_PARSING = 0

# In regex below:
#    [^\0-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+             matches a "token" as defined by HTTP
#    "(?:[^\0-\x08\x0A-\x1f\x7f-\xff\\\"]|\\[\0-\x7f])*?"    matches a "quoted-string" as defined by HTTP, when LWS have already been replaced by a single space
# Actually, as an auth-param value can be either a token or a quoted-string, they are combined in a single pattern which matches both:
#    \"?((?<=\")(?:[^\0-\x1f\x7f-\xff\\\"]|\\[\0-\x7f])*?(?=\")|(?<!\")[^\0-\x08\x0A-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+(?!\"))\"?
WWW_AUTH_STRICT = re.compile(r"^(?:\s*(?:,\s*)?([^\0-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+)\s*=\s*\"?((?<=\")(?:[^\0-\x08\x0A-\x1f\x7f-\xff\\\"]|\\[\0-\x7f])*?(?=\")|(?<!\")[^\0-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+(?!\"))\"?)(.*)$")
WWW_AUTH_RELAXED = re.compile(r"^(?:\s*(?:,\s*)?([^ \t\r\n=]+)\s*=\s*\"?((?<=\")(?:[^\\\"]|\\.)*?(?=\")|(?<!\")[^ \t\r\n,]+(?!\"))\"?)(.*)$")
UNQUOTE_PAIRS = re.compile(r'\\(.)')
def _parse_www_authenticate(headers, headername='www-authenticate'):
    """Returns a dictionary of dictionaries, one dict
    per auth_scheme."""
    retval = {}
    if headers.has_key(headername):
        authenticate = headers[headername].strip()
        www_auth = USE_WWW_AUTH_STRICT_PARSING and WWW_AUTH_STRICT or WWW_AUTH_RELAXED
        while authenticate:
            # Break off the scheme at the beginning of the line
            if headername == 'authentication-info':
                (auth_scheme, the_rest) = ('digest', authenticate)                
            else:
                (auth_scheme, the_rest) = authenticate.split(" ", 1)
            # Now loop over all the key value pairs that come after the scheme, 
            # being careful not to roll into the next scheme
            match = www_auth.search(the_rest)
            auth_params = {}
            while match:
                if match and len(match.groups()) == 3:
                    (key, value, the_rest) = match.groups()
                    auth_params[key.lower()] = UNQUOTE_PAIRS.sub(r'\1', value) # '\\'.join([x.replace('\\', '') for x in value.split('\\\\')])
                match = www_auth.search(the_rest)
            retval[auth_scheme.lower()] = auth_params
            authenticate = the_rest.strip()
    return retval


def _entry_disposition(response_headers, request_headers):
    """Determine freshness from the Date, Expires and Cache-Control headers.

    We don't handle the following:

    1. Cache-Control: max-stale
    2. Age: headers are not used in the calculations.

    Not that this algorithm is simpler than you might think 
    because we are operating as a private (non-shared) cache.
    This lets us ignore 's-maxage'. We can also ignore
    'proxy-invalidate' since we aren't a proxy.
    We will never return a stale document as 
    fresh as a design decision, and thus the non-implementation 
    of 'max-stale'. This also lets us safely ignore 'must-revalidate' 
    since we operate as if every server has sent 'must-revalidate'.
    Since we are private we get to ignore both 'public' and
    'private' parameters. We also ignore 'no-transform' since
    we don't do any transformations.    
    The 'no-store' parameter is handled at a higher level.
    So the only Cache-Control parameters we look at are:

    no-cache
    only-if-cached
    max-age
    min-fresh
    """
    
    retval = "STALE"
    cc = _parse_cache_control(request_headers)
    cc_response = _parse_cache_control(response_headers)

    if request_headers.has_key('pragma') and request_headers['pragma'].lower().find('no-cache') != -1:
        retval = "TRANSPARENT"
        if 'cache-control' not in request_headers:
            request_headers['cache-control'] = 'no-cache'
    elif cc.has_key('no-cache'):
        retval = "TRANSPARENT"
    elif cc_response.has_key('no-cache'):
        retval = "STALE"
    elif cc.has_key('only-if-cached'):
        retval = "FRESH"
    elif response_headers.has_key('date'):
        date = calendar.timegm(email.Utils.parsedate_tz(response_headers['date']))
        now = time.time()
        current_age = max(0, now - date)
        if cc_response.has_key('max-age'):
            try:
                freshness_lifetime = int(cc_response['max-age'])
            except ValueError:
                freshness_lifetime = 0
        elif response_headers.has_key('expires'):
            expires = email.Utils.parsedate_tz(response_headers['expires'])
            if None == expires:
                freshness_lifetime = 0
            else:
                freshness_lifetime = max(0, calendar.timegm(expires) - date)
        else:
            freshness_lifetime = 0
        if cc.has_key('max-age'):
            try:
                freshness_lifetime = int(cc['max-age'])
            except ValueError:
                freshness_lifetime = 0
        if cc.has_key('min-fresh'):
            try:
                min_fresh = int(cc['min-fresh'])
            except ValueError:
                min_fresh = 0
            current_age += min_fresh 
        if freshness_lifetime > current_age:
            retval = "FRESH"
    return retval 

def _decompressContent(response, new_content):
    content = new_content
    try:
        encoding = response.get('content-encoding', None)
        if encoding in ['gzip', 'deflate']:
            if encoding == 'gzip':
                content = gzip.GzipFile(fileobj=StringIO.StringIO(new_content)).read()
            if encoding == 'deflate':
                content = zlib.decompress(content)
            response['content-length'] = str(len(content))
            # Record the historical presence of the encoding in a way the won't interfere.
            response['-content-encoding'] = response['content-encoding']
            del response['content-encoding']
    except IOError:
        content = ""
        raise FailedToDecompressContent(_("Content purported to be compressed with %s but failed to decompress.") % response.get('content-encoding'), response, content)
    return content

def _updateCache(request_headers, response_headers, content, cache, cachekey):
    if cachekey:
        cc = _parse_cache_control(request_headers)
        cc_response = _parse_cache_control(response_headers)
        if cc.has_key('no-store') or cc_response.has_key('no-store'):
            cache.delete(cachekey)
        else:
            info = email.Message.Message()
            for key, value in response_headers.iteritems():
                if key not in ['status','content-encoding','transfer-encoding']:
                    info[key] = value

            # Add annotations to the cache to indicate what headers
            # are variant for this request.
            vary = response_headers.get('vary', None)
            if vary:
                vary_headers = vary.lower().replace(' ', '').split(',')
                for header in vary_headers:
                    key = '-varied-%s' % header
                    try:
                        info[key] = request_headers[header]
                    except KeyError:
                        pass

            status = response_headers.status
            if status == 304:
                status = 200

            status_header = 'status: %d\r\n' % response_headers.status

            header_str = info.as_string()

            header_str = re.sub("\r(?!\n)|(?<!\r)\n", "\r\n", header_str)
            text = "".join([status_header, header_str, content])

            cache.set(cachekey, text)

def _cnonce():
    dig = _md5("%s:%s" % (time.ctime(), ["0123456789"[random.randrange(0, 9)] for i in range(20)])).hexdigest()
    return dig[:16]

def _wsse_username_token(cnonce, iso_now, password):
    return base64.b64encode(_sha("%s%s%s" % (cnonce, iso_now, password)).digest()).strip()


# For credentials we need two things, first 
# a pool of credential to try (not necesarily tied to BAsic, Digest, etc.)
# Then we also need a list of URIs that have already demanded authentication
# That list is tricky since sub-URIs can take the same auth, or the 
# auth scheme may change as you descend the tree.
# So we also need each Auth instance to be able to tell us
# how close to the 'top' it is.

class Authentication(object):
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        (scheme, authority, path, query, fragment) = parse_uri(request_uri)
        self.path = path
        self.host = host
        self.credentials = credentials
        self.http = http

    def depth(self, request_uri):
        (scheme, authority, path, query, fragment) = parse_uri(request_uri)
        return request_uri[len(self.path):].count("/")

    def inscope(self, host, request_uri):
        # XXX Should we normalize the request_uri?
        (scheme, authority, path, query, fragment) = parse_uri(request_uri)
        return (host == self.host) and path.startswith(self.path)

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header. Over-rise this in sub-classes."""
        pass

    def response(self, response, content):
        """Gives us a chance to update with new nonces
        or such returned from the last authorized response.
        Over-rise this in sub-classes if necessary.

        Return TRUE is the request is to be retried, for 
        example Digest may return stale=true.
        """
        return False



class BasicAuthentication(Authentication):
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header."""
        headers['authorization'] = 'Basic ' + base64.b64encode("%s:%s" % self.credentials).strip()


class DigestAuthentication(Authentication):
    """Only do qop='auth' and MD5, since that 
    is all Apache currently implements"""
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)
        challenge = _parse_www_authenticate(response, 'www-authenticate')
        self.challenge = challenge['digest']
        qop = self.challenge.get('qop', 'auth')
        self.challenge['qop'] = ('auth' in [x.strip() for x in qop.split()]) and 'auth' or None
        if self.challenge['qop'] is None:
            raise UnimplementedDigestAuthOptionError( _("Unsupported value for qop: %s." % qop))
        self.challenge['algorithm'] = self.challenge.get('algorithm', 'MD5').upper()
        if self.challenge['algorithm'] != 'MD5':
            raise UnimplementedDigestAuthOptionError( _("Unsupported value for algorithm: %s." % self.challenge['algorithm']))
        self.A1 = "".join([self.credentials[0], ":", self.challenge['realm'], ":", self.credentials[1]])   
        self.challenge['nc'] = 1

    def request(self, method, request_uri, headers, content, cnonce = None):
        """Modify the request headers"""
        H = lambda x: _md5(x).hexdigest()
        KD = lambda s, d: H("%s:%s" % (s, d))
        A2 = "".join([method, ":", request_uri])
        self.challenge['cnonce'] = cnonce or _cnonce() 
        request_digest  = '"%s"' % KD(H(self.A1), "%s:%s:%s:%s:%s" % (self.challenge['nonce'], 
                    '%08x' % self.challenge['nc'], 
                    self.challenge['cnonce'], 
                    self.challenge['qop'], H(A2)
                    )) 
        headers['Authorization'] = 'Digest username="%s", realm="%s", nonce="%s", uri="%s", algorithm=%s, response=%s, qop=%s, nc=%08x, cnonce="%s"' % (
                self.credentials[0], 
                self.challenge['realm'],
                self.challenge['nonce'],
                request_uri, 
                self.challenge['algorithm'],
                request_digest,
                self.challenge['qop'],
                self.challenge['nc'],
                self.challenge['cnonce'],
                )
        self.challenge['nc'] += 1

    def response(self, response, content):
        if not response.has_key('authentication-info'):
            challenge = _parse_www_authenticate(response, 'www-authenticate').get('digest', {})
            if 'true' == challenge.get('stale'):
                self.challenge['nonce'] = challenge['nonce']
                self.challenge['nc'] = 1 
                return True
        else:
            updated_challenge = _parse_www_authenticate(response, 'authentication-info').get('digest', {})

            if updated_challenge.has_key('nextnonce'):
                self.challenge['nonce'] = updated_challenge['nextnonce']
                self.challenge['nc'] = 1 
        return False


class HmacDigestAuthentication(Authentication):
    """Adapted from Robert Sayre's code and DigestAuthentication above."""
    __author__ = "Thomas Broyer (t.broyer@ltgt.net)"

    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)
        challenge = _parse_www_authenticate(response, 'www-authenticate')
        self.challenge = challenge['hmacdigest']
        # TODO: self.challenge['domain']
        self.challenge['reason'] = self.challenge.get('reason', 'unauthorized')
        if self.challenge['reason'] not in ['unauthorized', 'integrity']:
            self.challenge['reason'] = 'unauthorized'
        self.challenge['salt'] = self.challenge.get('salt', '')
        if not self.challenge.get('snonce'):
            raise UnimplementedHmacDigestAuthOptionError( _("The challenge doesn't contain a server nonce, or this one is empty."))
        self.challenge['algorithm'] = self.challenge.get('algorithm', 'HMAC-SHA-1')
        if self.challenge['algorithm'] not in ['HMAC-SHA-1', 'HMAC-MD5']:
            raise UnimplementedHmacDigestAuthOptionError( _("Unsupported value for algorithm: %s." % self.challenge['algorithm']))
        self.challenge['pw-algorithm'] = self.challenge.get('pw-algorithm', 'SHA-1')
        if self.challenge['pw-algorithm'] not in ['SHA-1', 'MD5']:
            raise UnimplementedHmacDigestAuthOptionError( _("Unsupported value for pw-algorithm: %s." % self.challenge['pw-algorithm']))
        if self.challenge['algorithm'] == 'HMAC-MD5':
            self.hashmod = _md5
        else:
            self.hashmod = _sha
        if self.challenge['pw-algorithm'] == 'MD5':
            self.pwhashmod = _md5
        else:
            self.pwhashmod = _sha
        self.key = "".join([self.credentials[0], ":",
                    self.pwhashmod.new("".join([self.credentials[1], self.challenge['salt']])).hexdigest().lower(),
                    ":", self.challenge['realm']
                    ])
        self.key = self.pwhashmod.new(self.key).hexdigest().lower()

    def request(self, method, request_uri, headers, content):
        """Modify the request headers"""
        keys = _get_end2end_headers(headers)
        keylist = "".join(["%s " % k for k in keys])
        headers_val = "".join([headers[k] for k in keys])
        created = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        cnonce = _cnonce()
        request_digest = "%s:%s:%s:%s:%s" % (method, request_uri, cnonce, self.challenge['snonce'], headers_val)
        request_digest  = hmac.new(self.key, request_digest, self.hashmod).hexdigest().lower()
        headers['Authorization'] = 'HMACDigest username="%s", realm="%s", snonce="%s", cnonce="%s", uri="%s", created="%s", response="%s", headers="%s"' % (
                self.credentials[0], 
                self.challenge['realm'],
                self.challenge['snonce'],
                cnonce,
                request_uri, 
                created,
                request_digest,
                keylist,
                )

    def response(self, response, content):
        challenge = _parse_www_authenticate(response, 'www-authenticate').get('hmacdigest', {})
        if challenge.get('reason') in ['integrity', 'stale']:
            return True
        return False


class WsseAuthentication(Authentication):
    """This is thinly tested and should not be relied upon.
    At this time there isn't any third party server to test against.
    Blogger and TypePad implemented this algorithm at one point
    but Blogger has since switched to Basic over HTTPS and 
    TypePad has implemented it wrong, by never issuing a 401
    challenge but instead requiring your client to telepathically know that
    their endpoint is expecting WSSE profile="UsernameToken"."""
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header."""
        headers['Authorization'] = 'WSSE profile="UsernameToken"'
        iso_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cnonce = _cnonce()
        password_digest = _wsse_username_token(cnonce, iso_now, self.credentials[1])
        headers['X-WSSE'] = 'UsernameToken Username="%s", PasswordDigest="%s", Nonce="%s", Created="%s"' % (
                self.credentials[0],
                password_digest,
                cnonce,
                iso_now)

class GoogleLoginAuthentication(Authentication):
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        from urllib import urlencode
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)
        challenge = _parse_www_authenticate(response, 'www-authenticate')
        service = challenge['googlelogin'].get('service', 'xapi')
        # Bloggger actually returns the service in the challenge
        # For the rest we guess based on the URI
        if service == 'xapi' and  request_uri.find("calendar") > 0:
            service = "cl"
        # No point in guessing Base or Spreadsheet
        #elif request_uri.find("spreadsheets") > 0:
        #    service = "wise"

        auth = dict(Email=credentials[0], Passwd=credentials[1], service=service, source=headers['user-agent'])
        resp, content = self.http.request("https://www.google.com/accounts/ClientLogin", method="POST", body=urlencode(auth), headers={'Content-Type': 'application/x-www-form-urlencoded'})
        lines = content.split('\n')
        d = dict([tuple(line.split("=", 1)) for line in lines if line])
        if resp.status == 403:
            self.Auth = ""
        else:
            self.Auth = d['Auth']

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header."""
        headers['authorization'] = 'GoogleLogin Auth=' + self.Auth 


AUTH_SCHEME_CLASSES = {
    "basic": BasicAuthentication,
    "wsse": WsseAuthentication,
    "digest": DigestAuthentication,
    "hmacdigest": HmacDigestAuthentication,
    "googlelogin": GoogleLoginAuthentication
}

AUTH_SCHEME_ORDER = ["hmacdigest", "googlelogin", "digest", "wsse", "basic"]

class FileCache(object):
    """Uses a local directory as a store for cached files.
    Not really safe to use if multiple threads or processes are going to 
    be running on the same cache.
    """
    def __init__(self, cache, safe=safename): # use safe=lambda x: md5.new(x).hexdigest() for the old behavior
        self.cache = cache
        self.safe = safe
        if not os.path.exists(cache): 
            os.makedirs(self.cache)

    def get(self, key):
        retval = None
        cacheFullPath = os.path.join(self.cache, self.safe(key))
        try:
            f = file(cacheFullPath, "rb")
            retval = f.read()
            f.close()
        except IOError:
            pass
        return retval

    def set(self, key, value):
        cacheFullPath = os.path.join(self.cache, self.safe(key))
        f = file(cacheFullPath, "wb")
        f.write(value)
        f.close()

    def delete(self, key):
        cacheFullPath = os.path.join(self.cache, self.safe(key))
        if os.path.exists(cacheFullPath):
            os.remove(cacheFullPath)

class Credentials(object):
    def __init__(self):
        self.credentials = []

    def add(self, name, password, domain=""):
        self.credentials.append((domain.lower(), name, password))

    def clear(self):
        self.credentials = []

    def iter(self, domain):
        for (cdomain, name, password) in self.credentials:
            if cdomain == "" or domain == cdomain:
                yield (name, password) 

class KeyCerts(Credentials):
    """Identical to Credentials except that
    name/password are mapped to key/cert."""
    pass


class ProxyInfo(object):
  """Collect information required to use a proxy."""
  def __init__(self, proxy_type, proxy_host, proxy_port, proxy_rdns=None, proxy_user=None, proxy_pass=None):
      """The parameter proxy_type must be set to one of socks.PROXY_TYPE_XXX
      constants. For example:

p = ProxyInfo(proxy_type=socks.PROXY_TYPE_HTTP, proxy_host='localhost', proxy_port=8000)
      """
      self.proxy_type, self.proxy_host, self.proxy_port, self.proxy_rdns, self.proxy_user, self.proxy_pass = proxy_type, proxy_host, proxy_port, proxy_rdns, proxy_user, proxy_pass

  def astuple(self):
    return (self.proxy_type, self.proxy_host, self.proxy_port, self.proxy_rdns,
        self.proxy_user, self.proxy_pass)

  def isgood(self):
      # HACK: amorton socks module is included in this file now
    #return socks and (self.proxy_host != None) and (self.proxy_port != None)
    return (self.proxy_host != None) and (self.proxy_port != None)

class HTTPConnectionWithTimeout(httplib.HTTPConnection):
    """HTTPConnection subclass that supports timeouts"""

    def __init__(self, host, port=None, strict=None, timeout=None, proxy_info=None):
        httplib.HTTPConnection.__init__(self, host, port, strict)
        self.timeout = timeout
        self.proxy_info = proxy_info

    def connect(self):
        """Connect to the host and port specified in __init__."""
        # Mostly verbatim from httplib.py.
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(self.host, self.port, 0,
                socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                if self.proxy_info and self.proxy_info.isgood():
                    # HACK: amorton socks module is included in the file
                    # self.sock = socks.socksocket(af, socktype, proto)
                    self.sock = socksocket(af, socktype, proto)
                    # HACK: amorton enabled TCP_NODLEAY on socket
                    self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    self.sock.setproxy(*self.proxy_info.astuple())
                else:
                    self.sock = socket.socket(af, socktype, proto)
                    # HACK: amorton enabled TCP_NODLEAY on socket
                    self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                # Different from httplib: support timeouts.
                if has_timeout(self.timeout):
                    self.sock.settimeout(self.timeout)
                    # End of difference from httplib.
                if self.debuglevel > 0:
                    print "connect: (%s, %s)" % (self.host, self.port)

                self.sock.connect(sa)
            except socket.error, msg:
                if self.debuglevel > 0:
                    print 'connect fail:', (self.host, self.port)
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg

class HTTPSConnectionWithTimeout(httplib.HTTPSConnection):
    "This class allows communication via SSL."

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                 strict=None, timeout=None, proxy_info=None):
        httplib.HTTPSConnection.__init__(self, host, port=port, key_file=key_file,
                cert_file=cert_file, strict=strict)
        self.timeout = timeout
        self.proxy_info = proxy_info

    def connect(self):
        "Connect to a host on a given (SSL) port."

        if self.proxy_info and self.proxy_info.isgood():
            # HACK: amorton sock module is included in this file now
            #sock = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
            sock = socksocket(socket.AF_INET, socket.SOCK_STREAM)
            # HACK: amorton enabled TCP_NODLEAY on socket
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setproxy(*self.proxy_info.astuple())
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # HACK: amorton enabled TCP_NODLEAY on socket
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        if has_timeout(self.timeout):
            sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        self.sock =_ssl_wrap_socket(sock, self.key_file, self.cert_file)



class Http(object):
    """An HTTP client that handles:
- all methods
- caching
- ETags
- compression,
- HTTPS
- Basic
- Digest
- WSSE

and more.
    """
    def __init__(self, cache=None, timeout=None, proxy_info=None):
        """The value of proxy_info is a ProxyInfo instance.

If 'cache' is a string then it is used as a directory name
for a disk cache. Otherwise it must be an object that supports
the same interface as FileCache."""
        self.proxy_info = proxy_info
        # Map domain name to an httplib connection
        self.connections = {}
        # The location of the cache, for now a directory
        # where cached responses are held.
        if cache and isinstance(cache, str):
            self.cache = FileCache(cache)
        else:
            self.cache = cache

        # Name/password
        self.credentials = Credentials()

        # Key/cert
        self.certificates = KeyCerts()

        # authorization objects
        self.authorizations = []

        # If set to False then no redirects are followed, even safe ones.
        self.follow_redirects = True
        
        # Which HTTP methods do we apply optimistic concurrency to, i.e.
        # which methods get an "if-match:" etag header added to them.
        self.optimistic_concurrency_methods = ["PUT"]

        # If 'follow_redirects' is True, and this is set to True then
        # all redirecs are followed, including unsafe ones.
        self.follow_all_redirects = False

        self.ignore_etag = False

        self.force_exception_to_status_code = False 

        self.timeout = timeout

    def _auth_from_challenge(self, host, request_uri, headers, response, content):
        """A generator that creates Authorization objects
           that can be applied to requests.
        """
        challenges = _parse_www_authenticate(response, 'www-authenticate')
        for cred in self.credentials.iter(host):
            for scheme in AUTH_SCHEME_ORDER:
                if challenges.has_key(scheme):
                    yield AUTH_SCHEME_CLASSES[scheme](cred, host, request_uri, headers, response, content, self)

    def add_credentials(self, name, password, domain=""):
        """Add a name and password that will be used
        any time a request requires authentication."""
        self.credentials.add(name, password, domain)

    def add_certificate(self, key, cert, domain):
        """Add a key and cert that will be used
        any time a request requires authentication."""
        self.certificates.add(key, cert, domain)

    def clear_credentials(self):
        """Remove all the names and passwords
        that are used for authentication"""
        self.credentials.clear()
        self.authorizations = []

    def _conn_request(self, conn, request_uri, method, body, headers):
        for i in range(2):
            try:
                conn.request(method, request_uri, body, headers)
            except socket.gaierror:
                conn.close()
                raise ServerNotFoundError("Unable to find the server at %s" % conn.host)
            except (socket.error, httplib.HTTPException):
                # Just because the server closed the connection doesn't apparently mean
                # that the server didn't send a response.
                # amorton: patch from http://code.google.com/p/httplib2/source/detail?r=0cff83696d
                if conn.sock is None:
                    if i == 0:
                        conn.close()
                        conn.connect()
                        continue
                    else:
                        conn.close()
                        raise
                if i == 0:
                    conn.close()
                    conn.connect()
                    continue
                pass
            try:
                response = conn.getresponse()
            except (socket.error, httplib.HTTPException):
                if i == 0:
                    conn.close()
                    conn.connect()
                    continue
                else:
                    raise
            else:
                content = ""
                if method == "HEAD":
                    response.close()
                else:
                    content = response.read()
                response = Response(response)
                if method != "HEAD":
                    content = _decompressContent(response, content)
            break
        return (response, content)


    def _request(self, conn, host, absolute_uri, request_uri, method, body, headers, redirections, cachekey):
        """Do the actual request using the connection object
        and also follow one level of redirects if necessary"""

        auths = [(auth.depth(request_uri), auth) for auth in self.authorizations if auth.inscope(host, request_uri)]
        auth = auths and sorted(auths)[0][1] or None
        if auth: 
            auth.request(method, request_uri, headers, body)

        (response, content) = self._conn_request(conn, request_uri, method, body, headers)

        if auth: 
            if auth.response(response, body):
                auth.request(method, request_uri, headers, body)
                (response, content) = self._conn_request(conn, request_uri, method, body, headers )
                response._stale_digest = 1

        if response.status == 401:
            for authorization in self._auth_from_challenge(host, request_uri, headers, response, content):
                authorization.request(method, request_uri, headers, body) 
                (response, content) = self._conn_request(conn, request_uri, method, body, headers, )
                if response.status != 401:
                    self.authorizations.append(authorization)
                    authorization.response(response, body)
                    break

        if (self.follow_all_redirects or (method in ["GET", "HEAD"]) or response.status == 303):
            if self.follow_redirects and response.status in [300, 301, 302, 303, 307]:
                # Pick out the location header and basically start from the beginning
                # remembering first to strip the ETag header and decrement our 'depth'
                if redirections:
                    if not response.has_key('location') and response.status != 300:
                        raise RedirectMissingLocation( _("Redirected but the response is missing a Location: header."), response, content)
                    # Fix-up relative redirects (which violate an RFC 2616 MUST)
                    if response.has_key('location'):
                        location = response['location']
                        (scheme, authority, path, query, fragment) = parse_uri(location)
                        if authority == None:
                            response['location'] = urlparse.urljoin(absolute_uri, location)
                    if response.status == 301 and method in ["GET", "HEAD"]:
                        response['-x-permanent-redirect-url'] = response['location']
                        if not response.has_key('content-location'):
                            response['content-location'] = absolute_uri 
                        _updateCache(headers, response, content, self.cache, cachekey)
                    if headers.has_key('if-none-match'):
                        del headers['if-none-match']
                    if headers.has_key('if-modified-since'):
                        del headers['if-modified-since']
                    if response.has_key('location'):
                        location = response['location']
                        old_response = copy.deepcopy(response)
                        if not old_response.has_key('content-location'):
                            old_response['content-location'] = absolute_uri 
                        redirect_method = ((response.status == 303) and (method not in ["GET", "HEAD"])) and "GET" or method
                        (response, content) = self.request(location, redirect_method, body=body, headers = headers, redirections = redirections - 1)
                        response.previous = old_response
                else:
                    raise RedirectLimit( _("Redirected more times than rediection_limit allows."), response, content)
            elif response.status in [200, 203] and method == "GET":
                # Don't cache 206's since we aren't going to handle byte range requests
                if not response.has_key('content-location'):
                    response['content-location'] = absolute_uri 
                _updateCache(headers, response, content, self.cache, cachekey)

        return (response, content)

    def _normalize_headers(self, headers):
        return _normalize_headers(headers)

# Need to catch and rebrand some exceptions
# Then need to optionally turn all exceptions into status codes
# including all socket.* and httplib.* exceptions.


    def request(self, uri, method="GET", body=None, headers=None, redirections=DEFAULT_MAX_REDIRECTS, connection_type=None):
        """ Performs a single HTTP request.
The 'uri' is the URI of the HTTP resource and can begin 
with either 'http' or 'https'. The value of 'uri' must be an absolute URI.

The 'method' is the HTTP method to perform, such as GET, POST, DELETE, etc. 
There is no restriction on the methods allowed.

The 'body' is the entity body to be sent with the request. It is a string
object.

Any extra headers that are to be sent with the request should be provided in the
'headers' dictionary.

The maximum number of redirect to follow before raising an 
exception is 'redirections. The default is 5.

The return value is a tuple of (response, content), the first 
being and instance of the 'Response' class, the second being 
a string that contains the response entity body.
        """
        try:
            if headers is None:
                headers = {}
            else:
                headers = self._normalize_headers(headers)

            if not headers.has_key('user-agent'):
                headers['user-agent'] = "Python-httplib2/%s" % __version__

            uri = iri2uri(uri)

            (scheme, authority, request_uri, defrag_uri) = urlnorm(uri)
            domain_port = authority.split(":")[0:2]
            if len(domain_port) == 2 and domain_port[1] == '443' and scheme == 'http':
                scheme = 'https'
                authority = domain_port[0]

            conn_key = scheme+":"+authority
            if conn_key in self.connections:
                conn = self.connections[conn_key]
            else:
                if not connection_type:
                    connection_type = (scheme == 'https') and HTTPSConnectionWithTimeout or HTTPConnectionWithTimeout
                certs = list(self.certificates.iter(authority))
                if scheme == 'https' and certs:
                    conn = self.connections[conn_key] = connection_type(authority, key_file=certs[0][0],
                        cert_file=certs[0][1], timeout=self.timeout, proxy_info=self.proxy_info)
                else:
                    conn = self.connections[conn_key] = connection_type(authority, timeout=self.timeout, proxy_info=self.proxy_info)
                conn.set_debuglevel(debuglevel)

            if method in ["GET", "HEAD"] and 'range' not in headers and 'accept-encoding' not in headers:
                headers['accept-encoding'] = 'gzip, deflate'

            info = email.Message.Message()
            cached_value = None
            if self.cache:
                cachekey = defrag_uri
                cached_value = self.cache.get(cachekey)
                if cached_value:
                    # info = email.message_from_string(cached_value)
                    #
                    # Need to replace the line above with the kludge below
                    # to fix the non-existent bug not fixed in this
                    # bug report: http://mail.python.org/pipermail/python-bugs-list/2005-September/030289.html
                    try:
                        info, content = cached_value.split('\r\n\r\n', 1)
                        feedparser = email.FeedParser.FeedParser()
                        feedparser.feed(info)
                        info = feedparser.close()
                        feedparser._parse = None
                    except IndexError:
                        self.cache.delete(cachekey)
                        cachekey = None
                        cached_value = None
            else:
                cachekey = None

            if method in self.optimistic_concurrency_methods and self.cache and info.has_key('etag') and not self.ignore_etag and 'if-match' not in headers:
                # http://www.w3.org/1999/04/Editing/
                headers['if-match'] = info['etag']

            if method not in ["GET", "HEAD"] and self.cache and cachekey:
                # RFC 2616 Section 13.10
                self.cache.delete(cachekey)

            # Check the vary header in the cache to see if this request
            # matches what varies in the cache.
            if method in ['GET', 'HEAD'] and 'vary' in info:
                vary = info['vary']
                vary_headers = vary.lower().replace(' ', '').split(',')
                for header in vary_headers:
                    key = '-varied-%s' % header
                    value = info[key]
                    if headers.get(header, '') != value:
                            cached_value = None
                            break

            if cached_value and method in ["GET", "HEAD"] and self.cache and 'range' not in headers:
                if info.has_key('-x-permanent-redirect-url'):
                    # Should cached permanent redirects be counted in our redirection count? For now, yes.
                    (response, new_content) = self.request(info['-x-permanent-redirect-url'], "GET", headers = headers, redirections = redirections - 1)
                    response.previous = Response(info)
                    response.previous.fromcache = True
                else:
                    # Determine our course of action:
                    #   Is the cached entry fresh or stale?
                    #   Has the client requested a non-cached response?
                    #   
                    # There seems to be three possible answers: 
                    # 1. [FRESH] Return the cache entry w/o doing a GET
                    # 2. [STALE] Do the GET (but add in cache validators if available)
                    # 3. [TRANSPARENT] Do a GET w/o any cache validators (Cache-Control: no-cache) on the request
                    entry_disposition = _entry_disposition(info, headers) 
                    
                    if entry_disposition == "FRESH":
                        if not cached_value:
                            info['status'] = '504'
                            content = ""
                        response = Response(info)
                        if cached_value:
                            response.fromcache = True
                        return (response, content)

                    if entry_disposition == "STALE":
                        if info.has_key('etag') and not self.ignore_etag and not 'if-none-match' in headers:
                            headers['if-none-match'] = info['etag']
                        if info.has_key('last-modified') and not 'last-modified' in headers:
                            headers['if-modified-since'] = info['last-modified']
                    elif entry_disposition == "TRANSPARENT":
                        pass

                    (response, new_content) = self._request(conn, authority, uri, request_uri, method, body, headers, redirections, cachekey)

                if response.status == 304 and method == "GET":
                    # Rewrite the cache entry with the new end-to-end headers
                    # Take all headers that are in response 
                    # and overwrite their values in info.
                    # unless they are hop-by-hop, or are listed in the connection header.

                    for key in _get_end2end_headers(response):
                        info[key] = response[key]
                    merged_response = Response(info)
                    if hasattr(response, "_stale_digest"):
                        merged_response._stale_digest = response._stale_digest
                    _updateCache(headers, merged_response, content, self.cache, cachekey)
                    response = merged_response
                    response.status = 200
                    response.fromcache = True 

                elif response.status == 200:
                    content = new_content
                else:
                    self.cache.delete(cachekey)
                    content = new_content 
            else: 
                cc = _parse_cache_control(headers)
                if cc.has_key('only-if-cached'):
                    info['status'] = '504'
                    response = Response(info)
                    content = ""
                else:
                    (response, content) = self._request(conn, authority, uri, request_uri, method, body, headers, redirections, cachekey)
        except Exception, e:
            if self.force_exception_to_status_code:
                if isinstance(e, HttpLib2ErrorWithResponse):
                    response = e.response
                    content = e.content
                    response.status = 500
                    response.reason = str(e) 
                elif isinstance(e, socket.timeout):
                    content = "Request Timeout"
                    response = Response( {
                            "content-type": "text/plain",
                            "status": "408",
                            "content-length": len(content)
                            })
                    response.reason = "Request Timeout"
                else:
                    content = str(e) 
                    response = Response( {
                            "content-type": "text/plain",
                            "status": "400",
                            "content-length": len(content)
                            })
                    response.reason = "Bad Request" 
            else:
                raise

 
        return (response, content)

 

class Response(dict):
    """An object more like email.Message than httplib.HTTPResponse."""
   
    """Is this response from our local cache"""
    fromcache = False

    """HTTP protocol version used by server. 10 for HTTP/1.0, 11 for HTTP/1.1. """
    version = 11

    "Status code returned by server. "
    status = 200

    """Reason phrase returned by server."""
    reason = "Ok"

    previous = None

    def __init__(self, info):
        # info is either an email.Message or 
        # an httplib.HTTPResponse object.
        if isinstance(info, httplib.HTTPResponse):
            for key, value in info.getheaders(): 
                self[key.lower()] = value 
            self.status = info.status
            self['status'] = str(self.status)
            self.reason = info.reason
            self.version = info.version
        elif isinstance(info, email.Message.Message):
            for key, value in info.items(): 
                self[key] = value 
            self.status = int(self['status'])
        else:
            for key, value in info.iteritems(): 
                self[key] = value 
            self.status = int(self.get('status', self.status))


    def __getattr__(self, name):
        if name == 'dict':
            return self 
        else:  
            raise AttributeError, name 


















# ----------------------------------------------------------------------------
# SocksiPy/socks.py

"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.
   
THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

import socket
import struct

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class GeneralProxyError(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Socks5AuthError(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Socks5Error(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Socks4Error(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class HTTPError(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

_generalerrors = ("success",
		   "invalid data",
		   "not connected",
		   "not available",
		   "bad proxy type",
		   "bad input")

_socks5errors = ("succeeded",
		  "general SOCKS server failure",
		  "connection not allowed by ruleset",
		  "Network unreachable",
		  "Host unreachable",
		  "Connection refused",
		  "TTL expired",
		  "Command not supported",
		  "Address type not supported",
		  "Unknown error")

_socks5autherrors = ("succeeded",
		      "authentication is required",
		      "all offered authentication methods were rejected",
		      "unknown username or invalid password",
		      "unknown error")

_socks4errors = ("request granted",
		  "request rejected or failed",
		  "request rejected because SOCKS server cannot connect to identd on the client",
		  "request rejected because the client program and identd report different user-ids",
		  "unknown error")

def setdefaultproxy(proxytype=None,addr=None,port=None,rdns=True,username=None,password=None):
	"""setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
	Sets a default proxy which all further socksocket objects will use,
	unless explicitly changed.
	"""
	global _defaultproxy
	_defaultproxy = (proxytype,addr,port,rdns,username,password)
	
class socksocket(socket.socket):
	"""socksocket([family[, type[, proto]]]) -> socket object
	
	Open a SOCKS enabled socket. The parameters are the same as
	those of the standard socket init. In order for SOCKS to work,
	you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
	"""
	
	def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
		_orgsocket.__init__(self,family,type,proto,_sock)
		if _defaultproxy != None:
			self.__proxy = _defaultproxy
		else:
			self.__proxy = (None, None, None, None, None, None)
		self.__proxysockname = None
		self.__proxypeername = None
	
	def __recvall(self, bytes):
		"""__recvall(bytes) -> data
		Receive EXACTLY the number of bytes requested from the socket.
		Blocks until the required number of bytes have been received.
		"""
		data = ""
		while len(data) < bytes:
			data = data + self.recv(bytes-len(data))
		return data
	
	def setproxy(self,proxytype=None,addr=None,port=None,rdns=True,username=None,password=None):
		"""setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
		Sets the proxy to be used.
		proxytype -	The type of the proxy to be used. Three types
				are supported: PROXY_TYPE_SOCKS4 (including socks4a),
				PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
		addr -		The address of the server (IP or DNS).
		port -		The port of the server. Defaults to 1080 for SOCKS
				servers and 8080 for HTTP proxy servers.
		rdns -		Should DNS queries be preformed on the remote side
				(rather than the local side). The default is True.
				Note: This has no effect with SOCKS4 servers.
		username -	Username to authenticate with to the server.
				The default is no authentication.
		password -	Password to authenticate with to the server.
				Only relevant when username is also provided.
		"""
		self.__proxy = (proxytype,addr,port,rdns,username,password)
	
	def __negotiatesocks5(self,destaddr,destport):
		"""__negotiatesocks5(self,destaddr,destport)
		Negotiates a connection through a SOCKS5 server.
		"""
		# First we'll send the authentication packages we support.
		if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
			# The username/password details were supplied to the
			# setproxy method so we support the USERNAME/PASSWORD
			# authentication (in addition to the standard none).
			self.sendall("\x05\x02\x00\x02")
		else:
			# No username/password were entered, therefore we
			# only support connections with no authentication.
			self.sendall("\x05\x01\x00")
		# We'll receive the server's response to determine which
		# method was selected
		chosenauth = self.__recvall(2)
		if chosenauth[0] != "\x05":
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		# Check the chosen authentication method
		if chosenauth[1] == "\x00":
			# No authentication is required
			pass
		elif chosenauth[1] == "\x02":
			# Okay, we need to perform a basic username/password
			# authentication.
			self.sendall("\x01" + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.proxy[5])) + self.__proxy[5])
			authstat = self.__recvall(2)
			if authstat[0] != "\x01":
				# Bad response
				self.close()
				raise GeneralProxyError((1,_generalerrors[1]))
			if authstat[1] != "\x00":
				# Authentication failed
				self.close()
				raise Socks5AuthError,((3,_socks5autherrors[3]))
			# Authentication succeeded
		else:
			# Reaching here is always bad
			self.close()
			if chosenauth[1] == "\xFF":
				raise Socks5AuthError((2,_socks5autherrors[2]))
			else:
				raise GeneralProxyError((1,_generalerrors[1]))
		# Now we can request the actual connection
		req = "\x05\x01\x00"
		# If the given destination address is an IP address, we'll
		# use the IPv4 address request even if remote resolving was specified.
		try:
			ipaddr = socket.inet_aton(destaddr)
			req = req + "\x01" + ipaddr
		except socket.error:
			# Well it's not an IP number,  so it's probably a DNS name.
			if self.__proxy[3]==True:
				# Resolve remotely
				ipaddr = None
				req = req + "\x03" + chr(len(destaddr)) + destaddr
			else:
				# Resolve locally
				ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
				req = req + "\x01" + ipaddr
		req = req + struct.pack(">H",destport)
		self.sendall(req)
		# Get the response
		resp = self.__recvall(4)
		if resp[0] != "\x05":
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		elif resp[1] != "\x00":
			# Connection failed
			self.close()
			if ord(resp[1])<=8:
				raise Socks5Error(ord(resp[1]),_generalerrors[ord(resp[1])])
			else:
				raise Socks5Error(9,_generalerrors[9])
		# Get the bound address/port
		elif resp[3] == "\x01":
			boundaddr = self.__recvall(4)
		elif resp[3] == "\x03":
			resp = resp + self.recv(1)
			boundaddr = self.__recvall(resp[4])
		else:
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		boundport = struct.unpack(">H",self.__recvall(2))[0]
		self.__proxysockname = (boundaddr,boundport)
		if ipaddr != None:
			self.__proxypeername = (socket.inet_ntoa(ipaddr),destport)
		else:
			self.__proxypeername = (destaddr,destport)
	
	def getproxysockname(self):
		"""getsockname() -> address info
		Returns the bound IP address and port number at the proxy.
		"""
		return self.__proxysockname
	
	def getproxypeername(self):
		"""getproxypeername() -> address info
		Returns the IP and port number of the proxy.
		"""
		return _orgsocket.getpeername(self)
	
	def getpeername(self):
		"""getpeername() -> address info
		Returns the IP address and port number of the destination
		machine (note: getproxypeername returns the proxy)
		"""
		return self.__proxypeername
	
	def __negotiatesocks4(self,destaddr,destport):
		"""__negotiatesocks4(self,destaddr,destport)
		Negotiates a connection through a SOCKS4 server.
		"""
		# Check if the destination address provided is an IP address
		rmtrslv = False
		try:
			ipaddr = socket.inet_aton(destaddr)
		except socket.error:
			# It's a DNS name. Check where it should be resolved.
			if self.__proxy[3]==True:
				ipaddr = "\x00\x00\x00\x01"
				rmtrslv = True
			else:
				ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
		# Construct the request packet
		req = "\x04\x01" + struct.pack(">H",destport) + ipaddr
		# The username parameter is considered userid for SOCKS4
		if self.__proxy[4] != None:
			req = req + self.__proxy[4]
		req = req + "\x00"
		# DNS name if remote resolving is required
		# NOTE: This is actually an extension to the SOCKS4 protocol
		# called SOCKS4A and may not be supported in all cases.
		if rmtrslv==True:
			req = req + destaddr + "\x00"
		self.sendall(req)
		# Get the response from the server
		resp = self.__recvall(8)
		if resp[0] != "\x00":
			# Bad data
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		if resp[1] != "\x5A":
			# Server returned an error
			self.close()
			if ord(resp[1]) in (91,92,93):
				self.close()
				raise Socks4Error((ord(resp[1]),_socks4errors[ord(resp[1])-90]))
			else:
				raise Socks4Error((94,_socks4errors[4]))
		# Get the bound address/port
		self.__proxysockname = (socket.inet_ntoa(resp[4:]),struct.unpack(">H",resp[2:4])[0])
		if rmtrslv != None:
			self.__proxypeername = (socket.inet_ntoa(ipaddr),destport)
		else:
			self.__proxypeername = (destaddr,destport)
	
	def __negotiatehttp(self,destaddr,destport):
		"""__negotiatehttp(self,destaddr,destport)
		Negotiates a connection through an HTTP server.
		"""
		# If we need to resolve locally, we do this now
		if self.__proxy[3] == False:
			addr = socket.gethostbyname(destaddr)
		else:
			addr = destaddr
		self.sendall("CONNECT " + addr + ":" + str(destport) + " HTTP/1.1\r\n" + "Host: " + destaddr + "\r\n\r\n")
		# We read the response until we get the string "\r\n\r\n"
		resp = self.recv(1)
		while resp.find("\r\n\r\n")==-1:
			resp = resp + self.recv(1)
		# We just need the first line to check if the connection
		# was successful
		statusline = resp.splitlines()[0].split(" ",2)
		if statusline[0] not in ("HTTP/1.0","HTTP/1.1"):
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		try:
			statuscode = int(statusline[1])
		except ValueError:
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		if statuscode != 200:
			self.close()
			raise HTTPError((statuscode,statusline[2]))
		self.__proxysockname = ("0.0.0.0",0)
		self.__proxypeername = (addr,destport)
	
	def connect(self,destpair):
		"""connect(self,despair)
		Connects to the specified destination through a proxy.
		destpar - A tuple of the IP/DNS address and the port number.
		(identical to socket's connect).
		To select the proxy server use setproxy().
		"""
		# Do a minimal input check first
		if (type(destpair) in (list,tuple)==False) or (len(destpair)<2) or (type(destpair[0])!=str) or (type(destpair[1])!=int):
			raise GeneralProxyError((5,_generalerrors[5]))
		if self.__proxy[0] == PROXY_TYPE_SOCKS5:
			if self.__proxy[2] != None:
				portnum = self.__proxy[2]
			else:
				portnum = 1080
			_orgsocket.connect(self,(self.__proxy[1],portnum))
			self.__negotiatesocks5(destpair[0],destpair[1])
		elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
			if self.__proxy[2] != None:
				portnum = self.__proxy[2]
			else:
				portnum = 1080
			_orgsocket.connect(self,(self.__proxy[1],portnum))
			self.__negotiatesocks4(destpair[0],destpair[1])
		elif self.__proxy[0] == PROXY_TYPE_HTTP:
			if self.__proxy[2] != None:
				portnum = self.__proxy[2]
			else:
				portnum = 8080
			_orgsocket.connect(self,(self.__proxy[1],portnum))
			self.__negotiatehttp(destpair[0],destpair[1])
		elif self.__proxy[0] == None:
			_orgsocket.connect(self,(destpair[0],destpair[1]))
		else:
			raise GeneralProxyError((4,_generalerrors[4]))
