#!/usr/bin/env python
# ---------------------------------------------------------------------------------------------
# Copyright (c) 2009-2010, Shotgun Software Inc
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
#
# ---------------------------------------------------------------------------------------------
# docs and latest version available for download at
#   https://support.shotgunsoftware.com/forums/48807-developer-api-info
# ---------------------------------------------------------------------------------------------

__version__ = "3.0.3"

# ---------------------------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------------------------
"""
Python Shotgun API library.
"""

# ---------------------------------------------------------------------------------------------
# TODO
# ---------------------------------------------------------------------------------------------
"""
 - add a configurable timeout duration (python xml-rpc lib never times out by default)
 - include a native python https implementation, when native https is not available (e.g. maya's python)
 - convert duration fields to/from a native python object?
 - make file fields an http link to the file
 - add logging functionality
 - add scrubbing to text data sent to server to make sure it is all valid unicode
 - support removing thumbnails / files (can only create or replace them now)
"""

# ---------------------------------------------------------------------------------------------
# CHANGELOG
# ---------------------------------------------------------------------------------------------
"""
+v3.0.3 - 2010 Oct 21
  + add support for local files. injects convenience info into returned hash for local file links
  + add schema cache support for client API functions. Expires every hour by default (for long-running
     scripts)

+v3.0.2 - 2010 May 10
  + add revive() method to revive deleted entities

v3.0.1 - 2010 May 10
  + find(): default sorting to ascending, if not set (instead of requiring ascending/descending)
  + upload() and upload_thumbnail(): pass auth info through

v3.0 - 2010 May 5
  + add batch() method to do multiple create, update, and delete requests in one
    request to the server (requires Shotgun server to be v1.13.0 or higher)

v3.0b8 - 2010 Feb 19
  + fix python gotcha about using lists / dictionaries as defaults.  See:
     http://www.ferg.org/projects/python_gotchas.html#contents_item_6
  + add schema_read method

v3.0b7 - 2009 November 30
  + add additional retries for connection errors and a catch for broken pipe exceptions

v3.0b6 - 2009 October 20
  + add support for HTTP/1.1 keepalive, which greatly improves performance for multiple requests
  + add more helpful error if server entered is not http or https
  + add support assigning tags to file uploads (for Shotgun version >= 1.10.6)

v3.0b5 - 2009 Sept 29
  + fixed deprecation warnings to raise Exception class for python 2.5

v3.0b4 - 2009 July 3
  + made upload() and upload_thumbnail() methods more backwards compatible
  + changes to find_one():
    + now defaults to no filter_operators

v3.0b3 - 2009 June 24
  + fixed upload() and upload_thumbnail() methods
  + added download_attachment() method
  + added schema_* methods for accessing entities and fields
  + added support for http proxy servers
  + added __version__ string
  + removed RECORDS_PER_PAGE global (can just set records_per_page on the Shotgun object after initializing it)
  + removed api_ver from the constructor, as this class is only designed to work with api v3

v3.0b2 - 2009 June 2
  + added preliminary support for http proxy servers

v3.0b1 - 2009 May 25
  + updated to use v3 of the XML-RPC API to communicate with the Shotgun server
  + the "limit" option for find() now works fully
  + errors from the server are now raised as xml-rpc Fault exceptions (previously just wrote the error into the
    results, and you had to check for it explicitly -- which most people didn't do, so they didn't see the errors)
  + changes to find():
    + in the "order" param "column" has been renamed to "field_name" to be consistent
    + new option for complex filters that allow grouping
    + supports linked fields ("sg_project.Project.name")
  + changes to create():
    + now accepts "return_fields" param, which is an array of field names to return when creating the entity.
      Previously returned only the id.

v1.2 - 2009 Apr 28
  + updated compatibility for Python 2.4+
  + added convert_datetimes_to_utc flag to assume all datetimes are in local time (disabled by default to maintain
    current behavior)
  + upload() now returns id of Attachment created

v1.1 - 2009 Mar 27
  + added retired_only parameter to find()
  + fixed bug preventing attachments from being uploaded without linking to a specific field
  + minor error message formatting tweaks
"""

# ---------------------------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------------------------
import cookielib
import cStringIO
import mimetools
import mimetypes
import os
import platform
import re
import stat
import sys
import time
import urllib
import urllib2
from urlparse import urlparse

# ---------------------------------------------------------------------------------------------
# Shotgun Object
# ---------------------------------------------------------------------------------------------
class ShotgunError(Exception): pass

class Shotgun:
    # Used to split up requests into batches of records_per_page when doing requests.  this helps speed tremendously
    # when getting lots of results back.  doesn't affect the interface of the api at all (you always get the full set
    # of results back as one array) but just how the client class communicates with the server.
    records_per_page = 500
    schema_expire_mins = 60
    
    def __init__(self, base_url, script_name, api_key, convert_datetimes_to_utc=True, http_proxy=None):
        """
        Initialize Shotgun.
        """
        self.server = None
        if base_url.split("/")[0] not in ("http:","https:"):
            raise ShotgunError("URL protocol must be http or https.  Value was '%s'" % base_url)
        self.base_url = "/".join(base_url.split("/")[0:3]) # cheesy way to strip off anything past the domain name, so:
                                                           # http://blah.com/asd => http://blah.com
        self.script_name = script_name
        self.api_key = api_key
        self.api_ver = 'api3_preview' # keep using api3_preview to be compatible with older servers
        self.api_url = "%s/%s/" % (self.base_url, self.api_ver)
        self.convert_datetimes_to_utc = convert_datetimes_to_utc
        self.sid = None # only load this if needed
        self.http_proxy = http_proxy
        
        server_options = {
            'server_url': self.api_url,
            'script_name': self.script_name,
            'script_key': self.api_key,
            'http_proxy' : self.http_proxy,
            'convert_datetimes_to_utc': self.convert_datetimes_to_utc
        }
        
        self._api3 = ShotgunCRUD(server_options)
        
        self.schema_expire = datetime.datetime.now()
        self.schema = self.schema_read() # automatically resets the schema_expire time
        self.local_path_string = None
        self.platform = self._determine_platform()
        if self.platform:
            self.local_path_string = "local_path_%s" % (self.platform)
    
    def _determine_platform(self):
        s = platform.system().lower()
        if s in ['windows','linux','darwin']:
            if s == 'darwin':
                return 'mac'
            else:
                return s
        return None
    
    def _lookup_url_fields(self, entity_type, fields):
        url_fields = []
        for field in set(fields):
            # check for bubbled fields
            is_linked_field = re.search("\.(.*)\.(.*)$", field)
            if is_linked_field:
                et, f = is_linked_field.group(1), is_linked_field.group(2)
            else:
                et, f = entity_type, field
            if self.schema[et][f]['data_type']['value'] == 'url':
                url_fields.append(field)
        return url_fields
    
    def _inject_field_values(self, records, is_batch=False):
        """
        Inject additional information into server results for convenience before returning
        records back to the client. Currently this includes:
        - 'image' value is rewritten to provide url to thumbnail image
        - any local file link fields
            'local_file' key is set to match the current platform's path
            'url' key is set to match the current platform's url
        """
        if len(records) == 0:
            return records
        
        # check if we need to proceed with iteration if this isn't a batch result
        if not is_batch:
            entity_type = records[0]['type']
            fields = records[0].keys()
            fields.remove('type')
            url_fields = self._lookup_url_fields(entity_type, fields)
            if ( len(url_fields) == 0 or not self.platform ) and ( 'image' not in set(fields) ):
                return records
        
        for i,r in enumerate(records):
            # skip results that aren't entity dictionaries
            if type(r) is not dict:
                continue
            
            # since results from batch() can be anything, need to look up each record
            if is_batch:
                entity_type = r['type']
                fields = r.keys()
                fields.remove('type')
                url_fields = self._lookup_url_fields(entity_type, fields)
            
            if ( len(url_fields) > 0 and self.platform ) or ( 'image' in set(fields) ):
                for fk in url_fields:
                    if fk in r and r[fk] and 'link_type' in r[fk] and \
                    r[fk]['link_type'] == 'local' and self.platform:
                        records[i][fk]['local_path'] = r[fk][self.local_path_string]
                        records[i][fk]['url'] = "file://%s" % (r[fk]['local_path'])
            if 'image' in r and r['image']:
                records[i]['image'] = self._get_thumb_url(entity_type,r['id'])
        return records
    
    # check the schema cache for long running scripts and reload if it has expired
    def check_schema_cache(fn):
        def f(self, *args, **kwargs):
            if self.schema_expire < datetime.datetime.now():
                self.schema = self.schema_read()
                self.schema_expire = datetime.datetime.now() + datetime.timedelta(minutes=self.schema_expire_mins)
            return fn(self, *args, **kwargs)
        return f
    
    def _get_thumb_url(self, entity_type, entity_id):
        """
        Returns the URL for the thumbnail of an entity given the
        entity type and the entity id
        """
        url = self.base_url + "/upload/get_thumbnail_url?entity_type=%s&entity_id=%d"%(entity_type,entity_id)
        for i in range(3):
            f = urllib.urlopen(url)
            response_code = f.readline().strip()
            # something else happened. try again. found occasional connection errors still spit out html but not
            # the correct response codes. usually trying again will right the ship. if not, we catch for it later.
            if response_code not in ('0','1'):
                continue
            elif response_code == '1':
                path = f.readline().strip()
                if path:
                    return self.base_url + path
            elif response_code == '0':
                break
        # if it's an error, message is printed on second line
        raise ValueError, "%s:%s " % (entity_type,entity_id)+f.read().strip()
    
    def schema_read(self):
        resp = self._api3.schema_read()
        self.schema = resp["results"]
        self.schema_expire = datetime.datetime.now() + datetime.timedelta(minutes=self.schema_expire_mins)
        return resp["results"]
    
    def schema_field_read(self, entity_type, field_name=None):
        args = {
            "type":entity_type
        }
        if field_name:
            args["field_name"] = field_name
        resp = self._api3.schema_field_read(args)
        return resp["results"]
    
    def schema_field_create(self, entity_type, data_type, display_name, properties=None):
        if properties == None:
            properties = {}
        
        args = {
            "type":entity_type,
            "data_type":data_type,
            "properties":[{'property_name': 'name', 'value': display_name}]
        }
        for f,v in properties.items():
            args["properties"].append( {"property_name":f,"value":v} )
        resp = self._api3.schema_field_create(args)
        return resp["results"]
    
    def schema_field_update(self, entity_type, field_name, properties):
        args = {
            "type":entity_type,
            "field_name":field_name,
            "properties":[]
        }
        for f,v in properties.items():
            args["properties"].append( {"property_name":f,"value":v} )
        resp = self._api3.schema_field_update(args)
        return resp["results"]
    
    def schema_field_delete(self, entity_type, field_name):
        args = {
            "type":entity_type,
            "field_name":field_name
        }
        resp = self._api3.schema_field_delete(args)
        return resp["results"]
    
    def schema_entity_read(self):
        resp = self._api3.schema_entity_read()
        return resp["results"]
    
    @check_schema_cache
    def find(self, entity_type, filters, fields=None, order=None, filter_operator=None, limit=0, retired_only=False):
        """
        Find entities of entity_type matching the given filters.
        
        The columns returned for each entity match the 'fields'
        parameter provided, or just the id if nothing is specified.
        
        Limit constrains the total results to its value.
        
        Returns an array of dict entities sorted by the optional
        'order' parameter.
        """
        if fields == None:
            fields = ['id']
        if order == None:
            order = []
        
        if type(filters) == type([]):
            new_filters = {}
            if not filter_operator or filter_operator == "all":
                new_filters["logical_operator"] = "and"
            else:
                new_filters["logical_operator"] = "or"
            
            new_filters["conditions"] = []
            for f in filters:
                new_filters["conditions"].append( {"path":f[0],"relation":f[1],"values":f[2:]} )
            
            filters = new_filters
        elif filter_operator:
            raise ShotgunError("Deprecated: Use of filter_operator for find() is not valid any more.  See the documention on find()")
        
        if retired_only:
            return_only = 'retired'
        else:
            return_only = 'active'
        
        req = {
            "type": entity_type,
            "return_fields": fields,
            "filters": filters,
            "return_only" : return_only,
            "paging": {"entities_per_page": self.records_per_page, "current_page": 1}
        }
        
        if order:
           req['sorts'] = []
           for sort in order:
               if sort.has_key('column'):
                   # TODO: warn about deprecation of 'column' param name
                   sort['field_name'] = sort['column']
               if not sort.has_key('direction'):
                   sort['direction'] = 'asc'
               req['sorts'].append({'field_name': sort['field_name'],'direction' : sort['direction']})
        
        if (limit and limit > 0 and limit < self.records_per_page):
            req["paging"]["entities_per_page"] = limit
        
        records = []
        done = False
        while not done:
            resp = self._api3.read(req)
            results = resp["results"]["entities"]
            if results:
                records.extend(results)
                if ( len(records) >= limit and limit > 0 ):
                    records = records[:limit]
                    done = True
                elif len(records) == resp["results"]["paging_info"]["entity_count"]:
                    done = True
                else:
                    req['paging']['current_page'] += 1
            else:
                done = True
        
        records = self._inject_field_values(records)
        
        return records
    
    def find_one(self, entity_type, filters, fields=None, order=None, filter_operator=None, retired_only=False):
        """
        Same as find, but only returns 1 result as a dict
        """
        result = self.find(entity_type, filters, fields, order, filter_operator, 1, retired_only)
        if len(result) > 0:
            return result[0]
        else:
            return None
    
    def _required_keys(self, message, required_keys, data):
        missing = set(required_keys) - set(data.keys())
        if missing:
            raise ShotgunError("%s missing required key: %s. Value was: %s." % (message, ", ".join(missing), data))
    
    @check_schema_cache
    def batch(self, requests):
        if type(requests) != type([]):
            raise ShotgunError("batch() expects a list.  Instead was sent a %s"%type(requests))
        
        reqs = []
        
        for r in requests:
            self._required_keys("Batched request",['request_type','entity_type'],r)
            
            if r["request_type"] == "create":
                self._required_keys("Batched create request",['data'],r)
                
                nr = {
                    "request_type": "create",
                    "type": r["entity_type"],
                    "fields": []
                }
                
                if "return_fields" in r:
                    nr["return_fields"] = r
                
                for f,v in r["data"].items():
                    nr["fields"].append( { "field_name": f, "value": v } )
                
                reqs.append(nr)
            elif r["request_type"] == "update":
                self._required_keys("Batched create request",['entity_id','data'],r)
                
                nr = {
                    "request_type": "update",
                    "type": r["entity_type"],
                    "id": r["entity_id"],
                    "fields": []
                }
                
                for f,v in r["data"].items():
                    nr["fields"].append( { "field_name": f, "value": v } )
                
                reqs.append(nr)
            elif r["request_type"] == "delete":
                self._required_keys("Batched delete request",['entity_id'],r)
                
                nr = {
                    "request_type": "delete",
                    "type": r["entity_type"],
                    "id": r["entity_id"]
                }
                
                reqs.append(nr)
            else:
                raise ShotgunError("Invalid request_type for batch")
        
        resp = self._api3.batch(reqs)
        records = self._inject_field_values(resp["results"], True)
        
        return records
    
    @check_schema_cache
    def create(self, entity_type, data, return_fields=None):
        """
        Create a new entity of entity_type type.
        
        'data' is a dict of key=>value pairs of fieldname and value
        to set the field to.
        """
        if return_fields == None:
            return_fields = ['id']
        
        args = {
            "type":entity_type,
            "fields":[],
            "return_fields":return_fields
        }
        for f,v in data.items():
            args["fields"].append( {"field_name":f,"value":v} )
        
        resp = self._api3.create(args)
        records = self._inject_field_values([resp["results"]])
        return records
    
    @check_schema_cache
    def update(self, entity_type, entity_id, data):
        """
        Update an entity given the entity_type, and entity_id
        
        'data' is a dict of key=>value pairs of fieldname and value
        to set the field to.
        """
        args = {"type":entity_type,"id":entity_id,"fields":[]}
        for f,v in data.items():
            args["fields"].append( {"field_name":f,"value":v} )
        
        resp = self._api3.update(args)
        records = self._inject_field_values([resp["results"]])
        return records
    
    @check_schema_cache
    def delete(self, entity_type, entity_id):
        """
        Retire an entity given the entity_type, and entity_id
        """
        resp = self._api3.delete( {"type":entity_type, "id":entity_id} )
        return resp["results"]
    
    @check_schema_cache
    def revive(self, entity_type, entity_id):
        """
        Revive an entity given the entity_type, and entity_id
        """
        resp = self._api3.revive( {"type":entity_type, "id":entity_id} )
        return resp["results"]
    
    @check_schema_cache
    def upload(self, entity_type, entity_id, path, field_name=None, display_name=None, tag_list=None):
        """
        Upload a file as an attachment/thumbnail to the entity_type and entity_id
        
        @param entity_type: the entity type
        @param entity_id: id for given entity to attach to
        @param path: path to file on disk
        @param field_name: the field on the entity to upload to (ignored if thumbnail)
        @param display_name: the display name to use for the file in the ui (ignored if thumbnail)
        @param tag_list: comma-separated string of tags to assign to the file
        """
        is_thumbnail = (field_name == "thumb_image")
        
        params = {}
        params["entity_type"] = entity_type
        params["entity_id"] = entity_id
        
        # send auth, so server knows which
        # script uploaded the file
        params["script_name"] = self.script_name
        params["script_key"] = self.api_key
        
        if not os.path.isfile(path):
            raise ShotgunError("Path must be a valid file.")
        
        url = "%s/upload/upload_file" % (self.base_url)
        if is_thumbnail:
            url = "%s/upload/publish_thumbnail" % (self.base_url)
            params["thumb_image"] = open(path, "rb")
        else:
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
                raise ShotgunError("Server encountered an internal error. \n%s\n(%s)\n%s\n\n" % (url, params, e))
            else:
                raise ShotgunError("Unanticipated error occurred uploading %s: %s" % (path, e))
        else:
            if not str(result).startswith("1"):
                raise ShotgunError("Could not upload file successfully, but not sure why.\nPath: %s\nUrl: %s\nError: %s" % (path, url, str(result)))
        
        # we changed the result string in the middle of 1.8 to return the id
        # remove once everyone is > 1.8.3
        r = str(result).split(":")
        id = 0
        if len(r) > 1:
            id = int(str(result).split(":")[1].split("\n")[0])
        return id
    
    @check_schema_cache
    def upload_thumbnail(self, entity_type, entity_id, path, **kwargs):
        """
        Convenience function for thumbnail uploads.
        """
        result = self.upload(entity_type, entity_id, path, field_name="thumb_image", **kwargs)
        return result
    
    @check_schema_cache
    def download_attachment(self, entity_id):
        """
        Gets session authentication and returns binary content of Attachment data
        """
        sid = self._get_session_token()
        domain = urlparse(self.base_url)[1].split(':',1)[0]
        cj = cookielib.LWPCookieJar()
        c = cookielib.Cookie('0', '_session_id', sid, None, False, domain, False, False, "/", True, False, None, True, None, None, {})
        cj.set_cookie(c)
        cookie_handler = urllib2.HTTPCookieProcessor(cj)
        urllib2.install_opener(urllib2.build_opener(cookie_handler))
        url = '%s/file_serve/attachment/%s' % (self.base_url, entity_id)
        
        try:
            request = urllib2.Request(url)
            request.add_header('User-agent','Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US; rv:1.9.0.7) Gecko/2009021906 Firefox/3.0.7')
            attachment = urllib2.urlopen(request).read()
        
        except IOError, e:
            err = "Failed to open %s" % url
            if hasattr(e, 'code'):
                err += "\nWe failed with error code - %s." % e.code
            elif hasattr(e, 'reason'):
                err += "\nThe error object has the following 'reason' attribute :", e.reason
                err += "\nThis usually means the server doesn't exist, is down, or we don't have an internet connection."
            raise ShotgunError(err)
        else:
            if attachment.lstrip().startswith('<!DOCTYPE '):
                error_string = "\n%s\nThe server generated an error trying to download the Attachment. \nURL: %s\n" \
                    "Either the file doesn't exist, or it is a local file which isn't downloadable.\n%s\n" % ("="*30, url, "="*30)
                raise ShotgunError(error_string)
        return attachment
    
    def _get_session_token(self):
        """
        Hack to authenticate in order to download protected content
        like Attachments
        """
        if self.sid == None:
            # HACK: use API2 to get token for now until we better resolve how we manage Attachments in general
            api2_url = "%s/%s/" % (self.base_url, 'api2')
            conn = ServerProxy(api2_url)
            self.sid = conn.getSessionToken([self.script_name, self.api_key])['session_id']
        return self.sid
    
    # Deprecated methods from old wrapper
    def schema(self, entity_type):
        raise ShotgunError("Deprecated: use schema_field_read('type':'%s') instead" % entity_type)
    
    def entity_types(self):
        raise ShotgunError("Deprecated: use schema_entity_read() instead")

class ShotgunCRUD:
    def __init__(self, options):
        self.__sg_url = options['server_url']
        self.__auth_args = {'script_name': options['script_name'], 'script_key': options['script_key']}
        if 'convert_datetimes_to_utc' in options:
            convert_datetimes_to_utc = options['convert_datetimes_to_utc']
        else:
            convert_datetimes_to_utc = 1
        if 'error_stream' in options:
            self.__err_stream = options['error_stream']
        else:
            self.__err_stream = 'sys.stderr'
        if 'http_proxy' in options and options['http_proxy']:
            p = ProxiedTransport()
            p.set_proxy( options['http_proxy'] )
            self.__sg = ServerProxy(self.__sg_url, convert_datetimes_to_utc = convert_datetimes_to_utc, transport=p)
        else:
            self.__sg = ServerProxy(self.__sg_url, convert_datetimes_to_utc = convert_datetimes_to_utc)
    
    def __getattr__(self, attr):
        def callable(*args, **kwargs):
            return self.meta_caller(attr, *args, **kwargs)
        return callable
    
    def meta_caller(self, attr, *args, **kwargs):
        try:
            return eval(
                'self._%s__sg.%s(self._%s__auth_args, *args, **kwargs)' %
                (self.__class__.__name__, attr, self.__class__.__name__)
            )
        except Fault, e:
            if self.__err_stream:
                eval('%s.write("\\n" + "-"*80 + "\\n")' % self.__err_stream)
                eval('%s.write("XMLRPC Fault %s:\\n")' % (self.__err_stream, e.faultCode))
                eval('%s.write(e.faultString)' % self.__err_stream)
                eval('%s.write("\\n" + "-"*80 + "\\n")' % self.__err_stream)
            raise



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




# ---------------------------------------------------------------------------------------------
#  SG_TIMEZONE module
#  this is rolled into the this shotgun api file to avoid having to require current users of
#  api2 to install new modules and modify PYTHONPATH info.
# ---------------------------------------------------------------------------------------------
from datetime import tzinfo, timedelta, datetime
import time as _time

ZERO = timedelta(0)
STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET
DSTDIFF = DSTOFFSET - STDOFFSET

class SgTimezone:
    
    def __init__(self):
        self.utc = self.UTC()
        self.local = self.LocalTimezone()
    
    class UTC(tzinfo):
        
        def utcoffset(self, dt):
            return ZERO
        
        def tzname(self, dt):
            return "UTC"
        
        def dst(self, dt):
            return ZERO
    
    class LocalTimezone(tzinfo):
        
        def utcoffset(self, dt):
            if self._isdst(dt):
                return DSTOFFSET
            else:
                return STDOFFSET
        
        def dst(self, dt):
            if self._isdst(dt):
                return DSTDIFF
            else:
                return ZERO
        
        def tzname(self, dt):
            return _time.tzname[self._isdst(dt)]
        
        def _isdst(self, dt):
            tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
            stamp = _time.mktime(tt)
            tt = _time.localtime(stamp)
            return tt.tm_isdst > 0

sg_timezone = SgTimezone()





#
# XML-RPC CLIENT LIBRARY
# $Id: xmlrpclib.py 41594 2005-12-04 19:11:17Z andrew.kuchling $
#
# an XML-RPC client interface for Python.
#
# the marshalling and response parser code can also be used to
# implement XML-RPC servers.
#
# Notes:
# this version is designed to work with Python 2.1 or newer.
#
# History:
# 1999-01-14 fl  Created
# 1999-01-15 fl  Changed dateTime to use localtime
# 1999-01-16 fl  Added Binary/base64 element, default to RPC2 service
# 1999-01-19 fl  Fixed array data element (from Skip Montanaro)
# 1999-01-21 fl  Fixed dateTime constructor, etc.
# 1999-02-02 fl  Added fault handling, handle empty sequences, etc.
# 1999-02-10 fl  Fixed problem with empty responses (from Skip Montanaro)
# 1999-06-20 fl  Speed improvements, pluggable parsers/transports (0.9.8)
# 2000-11-28 fl  Changed boolean to check the truth value of its argument
# 2001-02-24 fl  Added encoding/Unicode/SafeTransport patches
# 2001-02-26 fl  Added compare support to wrappers (0.9.9/1.0b1)
# 2001-03-28 fl  Make sure response tuple is a singleton
# 2001-03-29 fl  Don't require empty params element (from Nicholas Riley)
# 2001-06-10 fl  Folded in _xmlrpclib accelerator support (1.0b2)
# 2001-08-20 fl  Base xmlrpclib.Error on built-in Exception (from Paul Prescod)
# 2001-09-03 fl  Allow Transport subclass to override getparser
# 2001-09-10 fl  Lazy import of urllib, cgi, xmllib (20x import speedup)
# 2001-10-01 fl  Remove containers from memo cache when done with them
# 2001-10-01 fl  Use faster escape method (80% dumps speedup)
# 2001-10-02 fl  More dumps microtuning
# 2001-10-04 fl  Make sure import expat gets a parser (from Guido van Rossum)
# 2001-10-10 sm  Allow long ints to be passed as ints if they don't overflow
# 2001-10-17 sm  Test for int and long overflow (allows use on 64-bit systems)
# 2001-11-12 fl  Use repr() to marshal doubles (from Paul Felix)
# 2002-03-17 fl  Avoid buffered read when possible (from James Rucker)
# 2002-04-07 fl  Added pythondoc comments
# 2002-04-16 fl  Added __str__ methods to datetime/binary wrappers
# 2002-05-15 fl  Added error constants (from Andrew Kuchling)
# 2002-06-27 fl  Merged with Python CVS version
# 2002-10-22 fl  Added basic authentication (based on code from Phillip Eby)
# 2003-01-22 sm  Add support for the bool type
# 2003-02-27 gvr Remove apply calls
# 2003-04-24 sm  Use cStringIO if available
# 2003-04-25 ak  Add support for nil
# 2003-06-15 gn  Add support for time.struct_time
# 2003-07-12 gp  Correct marshalling of Faults
# 2003-10-31 mvl Add multicall support
# 2004-08-20 mvl Bump minimum supported Python version to 2.1
#
# Copyright (c) 1999-2002 by Secret Labs AB.
# Copyright (c) 1999-2002 by Fredrik Lundh.
#
# info@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The XML-RPC client interface is
#
# Copyright (c) 1999-2002 by Secret Labs AB
# Copyright (c) 1999-2002 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

#
# things to look into some day:

# TODO: sort out True/False/boolean issues for Python 2.3

"""
An XML-RPC client interface for Python.

The marshalling and response parser code can also be used to
implement XML-RPC servers.

Exported exceptions:
  
  Error          Base class for client errors
  ProtocolError  Indicates an HTTP protocol error
  ResponseError  Indicates a broken response package
  Fault          Indicates an XML-RPC fault package

Exported classes:
  
  ServerProxy    Represents a logical connection to an XML-RPC server
  
  MultiCall      Executor of boxcared xmlrpc requests
  Boolean        boolean wrapper to generate a "boolean" XML-RPC value
  DateTime       dateTime wrapper for an ISO 8601 string or time tuple or
                 localtime integer value to generate a "dateTime.iso8601"
                 XML-RPC value
  Binary         binary data wrapper
  
  SlowParser     Slow but safe standard parser (based on xmllib)
  Marshaller     Generate an XML-RPC params chunk from a Python data structure
  Unmarshaller   Unmarshal an XML-RPC response from incoming XML event message
  Transport      Handles an HTTP transaction to an XML-RPC server
  SafeTransport  Handles an HTTPS transaction to an XML-RPC server

Exported constants:
  
  True
  False

Exported functions:
  
  boolean        Convert any Python value to an XML-RPC boolean
  getparser      Create instance of the fastest available parser & attach
                 to an unmarshalling object
  dumps          Convert an argument tuple or a Fault instance to an XML-RPC
                 request (or response, if the methodresponse option is used).
  loads          Convert an XML-RPC packet to unmarshalled data plus a method
                 name (None if not present).
"""

import re, string, time, operator

from types import *
import socket
import errno
import httplib

# --------------------------------------------------------------------
# Internal stuff

try:
    unicode
except NameError:
    unicode = None # unicode support not available

try:
    import datetime
    #import sg_timezone
except ImportError:
    datetime = None

try:
    _bool_is_builtin = False.__class__.__name__ == "bool"
except NameError:
    _bool_is_builtin = 0

def _decode(data, encoding, is8bit=re.compile("[\x80-\xff]").search):
    # decode non-ascii string (if possible)
    if unicode and encoding and is8bit(data):
        data = unicode(data, encoding)
    return data

def escape(s, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "<", "&lt;")
    return replace(s, ">", "&gt;",)

if unicode:
    def _stringify(string):
        # convert to 7-bit ascii if possible
        try:
            return string.encode("ascii")
        except UnicodeError:
            return string
else:
    def _stringify(string):
        return string

#__version__ = "1.0.1"

# xmlrpc integer limits
MAXINT =  2L**31-1
MININT = -2L**31

# --------------------------------------------------------------------
# Error constants (from Dan Libby's specification at
# http://xmlrpc-epi.sourceforge.net/specs/rfc.fault_codes.php)

# Ranges of errors
PARSE_ERROR       = -32700
SERVER_ERROR      = -32600
APPLICATION_ERROR = -32500
SYSTEM_ERROR      = -32400
TRANSPORT_ERROR   = -32300

# Specific errors
NOT_WELLFORMED_ERROR  = -32700
UNSUPPORTED_ENCODING  = -32701
INVALID_ENCODING_CHAR = -32702
INVALID_XMLRPC        = -32600
METHOD_NOT_FOUND      = -32601
INVALID_METHOD_PARAMS = -32602
INTERNAL_ERROR        = -32603

# --------------------------------------------------------------------
# Exceptions

##
# Base class for all kinds of client-side errors.

class Error(Exception):
    """Base class for client errors."""
    def __str__(self):
        return repr(self)

##
# Indicates an HTTP-level protocol error.  This is raised by the HTTP
# transport layer, if the server returns an error code other than 200
# (OK).
#
# @param url The target URL.
# @param errcode The HTTP error code.
# @param errmsg The HTTP error message.
# @param headers The HTTP header dictionary.

class ProtocolError(Error):
    """Indicates an HTTP protocol error."""
    def __init__(self, url, errcode, errmsg, headers):
        Error.__init__(self)
        self.url = url
        self.errcode = errcode
        self.errmsg = errmsg
        self.headers = headers
    def __repr__(self):
        return (
            "<ProtocolError for %s: %s %s>" %
            (self.url, self.errcode, self.errmsg)
            )

##
# Indicates a broken XML-RPC response package.  This exception is
# raised by the unmarshalling layer, if the XML-RPC response is
# malformed.

class ResponseError(Error):
    """Indicates a broken response package."""
    pass

##
# Indicates an XML-RPC fault response package.  This exception is
# raised by the unmarshalling layer, if the XML-RPC response contains
# a fault string.  This exception can also used as a class, to
# generate a fault XML-RPC message.
#
# @param faultCode The XML-RPC fault code.
# @param faultString The XML-RPC fault string.

class Fault(Error):
    """Indicates an XML-RPC fault package."""
    def __init__(self, faultCode, faultString, **extra):
        Error.__init__(self)
        self.faultCode = faultCode
        self.faultString = faultString
    def __repr__(self):
        return (
            "<Fault %s: %s>" %
            (self.faultCode, repr(self.faultString))
            )

# --------------------------------------------------------------------
# Special values

##
# Wrapper for XML-RPC boolean values.  Use the xmlrpclib.True and
# xmlrpclib.False constants, or the xmlrpclib.boolean() function, to
# generate boolean XML-RPC values.
#
# @param value A boolean value.  Any true value is interpreted as True,
#              all other values are interpreted as False.

if _bool_is_builtin:
    boolean = Boolean = bool
    # to avoid breaking code which references xmlrpclib.{True,False}
    True, False = True, False
else:
    class Boolean:
        """Boolean-value wrapper.
        
        Use True or False to generate a "boolean" XML-RPC value.
        """
        
        def __init__(self, value = 0):
            self.value = operator.truth(value)
        
        def encode(self, out):
            out.write("<value><boolean>%d</boolean></value>\n" % self.value)
        
        def __cmp__(self, other):
            if isinstance(other, Boolean):
                other = other.value
            return cmp(self.value, other)
        
        def __repr__(self):
            if self.value:
                return "<Boolean True at %x>" % id(self)
            else:
                return "<Boolean False at %x>" % id(self)
        
        def __int__(self):
            return self.value
        
        def __nonzero__(self):
            return self.value
    
    True, False = Boolean(1), Boolean(0)
    
    ##
    # Map true or false value to XML-RPC boolean values.
    #
    # @def boolean(value)
    # @param value A boolean value.  Any true value is mapped to True,
    #              all other values are mapped to False.
    # @return xmlrpclib.True or xmlrpclib.False.
    # @see Boolean
    # @see True
    # @see False
    
    def boolean(value, _truefalse=(False, True)):
        """Convert any Python value to XML-RPC 'boolean'."""
        return _truefalse[operator.truth(value)]

##
# Wrapper for XML-RPC DateTime values.  This converts a time value to
# the format used by XML-RPC.
# <p>
# The value can be given as a string in the format
# "yyyymmddThh:mm:ss", as a 9-item time tuple (as returned by
# time.localtime()), or an integer value (as returned by time.time()).
# The wrapper uses time.localtime() to convert an integer to a time
# tuple.
#
# @param value The time, given as an ISO 8601 string, a time
#              tuple, or a integer time value.

class DateTime:
    """DateTime wrapper for an ISO 8601 string or time tuple or
    localtime integer value to generate 'dateTime.iso8601' XML-RPC
    value.
    """
    
    def __init__(self, value=0):
        if not isinstance(value, StringType):
            if datetime and isinstance(value, datetime.datetime):
                self.value = value.strftime("%Y%m%dT%H:%M:%S")
                return
            if datetime and isinstance(value, datetime.date):
                self.value = value.strftime("%Y%m%dT%H:%M:%S")
                return
            if datetime and isinstance(value, datetime.time):
                today = datetime.datetime.now().strftime("%Y%m%d")
                self.value = value.strftime(today+"T%H:%M:%S")
                return
            if not isinstance(value, (TupleType, time.struct_time)):
                if value == 0:
                    value = time.time()
                value = time.localtime(value)
            value = time.strftime("%Y%m%dT%H:%M:%S", value)
        self.value = value
    
    def __cmp__(self, other):
        if isinstance(other, DateTime):
            other = other.value
        return cmp(self.value, other)
    
    ##
    # Get date/time value.
    #
    # @return Date/time value, as an ISO 8601 string.
    
    def __str__(self):
        return self.value
    
    def __repr__(self):
        return "<DateTime %s at %x>" % (repr(self.value), id(self))
    
    def decode(self, data):
        data = str(data)
        self.value = string.strip(data)
    
    def encode(self, out):
        out.write("<value><dateTime.iso8601>")
        out.write(self.value)
        out.write("</dateTime.iso8601></value>\n")

def _datetime(data):
    # decode xml element contents into a DateTime structure.
    value = DateTime()
    value.decode(data)
    return value

def _datetime_type(data):
    t = time.strptime(data, "%Y%m%dT%H:%M:%S")
    return datetime.datetime(*tuple(t)[:6])

##
# Wrapper for binary data.  This can be used to transport any kind
# of binary data over XML-RPC, using BASE64 encoding.
#
# @param data An 8-bit string containing arbitrary data.

import base64
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class Binary:
    """Wrapper for binary data."""
    
    def __init__(self, data=None):
        self.data = data
    
    ##
    # Get buffer contents.
    #
    # @return Buffer contents, as an 8-bit string.
    
    def __str__(self):
        return self.data or ""
    
    def __cmp__(self, other):
        if isinstance(other, Binary):
            other = other.data
        return cmp(self.data, other)
    
    def decode(self, data):
        self.data = base64.decodestring(data)
    
    def encode(self, out):
        out.write("<value><base64>\n")
        base64.encode(StringIO.StringIO(self.data), out)
        out.write("</base64></value>\n")

def _binary(data):
    # decode xml element contents into a Binary structure
    value = Binary()
    value.decode(data)
    return value

WRAPPERS = (DateTime, Binary)
if not _bool_is_builtin:
    WRAPPERS = WRAPPERS + (Boolean,)

# --------------------------------------------------------------------
# XML parsers

try:
    # optional xmlrpclib accelerator
    import _xmlrpclib
    FastParser = _xmlrpclib.Parser
    FastUnmarshaller = _xmlrpclib.Unmarshaller
except (AttributeError, ImportError):
    FastParser = FastUnmarshaller = None

try:
    import _xmlrpclib
    FastMarshaller = _xmlrpclib.Marshaller
except (AttributeError, ImportError):
    FastMarshaller = None

#
# the SGMLOP parser is about 15x faster than Python's builtin
# XML parser.  SGMLOP sources can be downloaded from:
#
#     http://www.pythonware.com/products/xml/sgmlop.htm
#

try:
    import sgmlop
    if not hasattr(sgmlop, "XMLParser"):
        raise ImportError
except ImportError:
    SgmlopParser = None # sgmlop accelerator not available
else:
    class SgmlopParser:
        def __init__(self, target):
            
            # setup callbacks
            self.finish_starttag = target.start
            self.finish_endtag = target.end
            self.handle_data = target.data
            self.handle_xml = target.xml
            
            # activate parser
            self.parser = sgmlop.XMLParser()
            self.parser.register(self)
            self.feed = self.parser.feed
            self.entity = {
                "amp": "&", "gt": ">", "lt": "<",
                "apos": "'", "quot": '"'
                }
        
        def close(self):
            try:
                self.parser.close()
            finally:
                self.parser = self.feed = None # nuke circular reference
        
        def handle_proc(self, tag, attr):
            m = re.search("encoding\s*=\s*['\"]([^\"']+)[\"']", attr)
            if m:
                self.handle_xml(m.group(1), 1)
        
        def handle_entityref(self, entity):
            # <string> entity
            try:
                self.handle_data(self.entity[entity])
            except KeyError:
                self.handle_data("&%s;" % entity)

try:
    from xml.parsers import expat
    if not hasattr(expat, "ParserCreate"):
        raise ImportError
except ImportError:
    ExpatParser = None # expat not available
else:
    class ExpatParser:
        # fast expat parser for Python 2.0 and later.  this is about
        # 50% slower than sgmlop, on roundtrip testing
        def __init__(self, target):
            self._parser = parser = expat.ParserCreate(None, None)
            self._target = target
            parser.StartElementHandler = target.start
            parser.EndElementHandler = target.end
            parser.CharacterDataHandler = target.data
            encoding = None
            if not parser.returns_unicode:
                encoding = "utf-8"
            target.xml(encoding, None)
        
        def feed(self, data):
            self._parser.Parse(data, 0)
        
        def close(self):
            self._parser.Parse("", 1) # end of data
            del self._target, self._parser # get rid of circular references

class SlowParser:
    """Default XML parser (based on xmllib.XMLParser)."""
    # this is about 10 times slower than sgmlop, on roundtrip
    # testing.
    def __init__(self, target):
        import xmllib # lazy subclassing (!)
        if xmllib.XMLParser not in SlowParser.__bases__:
            SlowParser.__bases__ = (xmllib.XMLParser,)
        self.handle_xml = target.xml
        self.unknown_starttag = target.start
        self.handle_data = target.data
        self.handle_cdata = target.data
        self.unknown_endtag = target.end
        try:
            xmllib.XMLParser.__init__(self, accept_utf8=1)
        except TypeError:
            xmllib.XMLParser.__init__(self) # pre-2.0

# --------------------------------------------------------------------
# XML-RPC marshalling and unmarshalling code

##
# XML-RPC marshaller.
#
# @param encoding Default encoding for 8-bit strings.  The default
#     value is None (interpreted as UTF-8).
# @see dumps

class Marshaller:
    """Generate an XML-RPC params chunk from a Python data structure.
    
    Create a Marshaller instance for each set of parameters, and use
    the "dumps" method to convert your data (represented as a tuple)
    to an XML-RPC params chunk.  To write a fault response, pass a
    Fault instance instead.  You may prefer to use the "dumps" module
    function for this purpose.
    """
    
    # by the way, if you don't understand what's going on in here,
    # that's perfectly ok.
    
    def __init__(self, encoding=None, allow_none=1, convert_datetimes_to_utc=1):
        self.memo = {}
        self.data = None
        self.encoding = encoding
        self.allow_none = allow_none
        self.convert_datetimes_to_utc = convert_datetimes_to_utc
    
    dispatch = {}
    
    def dumps(self, values):
        out = []
        write = out.append
        dump = self.__dump
        if isinstance(values, Fault):
            # fault instance
            write("<fault>\n")
            dump({'faultCode': values.faultCode,
                  'faultString': values.faultString},
                 write)
            write("</fault>\n")
        else:
            # parameter block
            # FIXME: the xml-rpc specification allows us to leave out
            # the entire <params> block if there are no parameters.
            # however, changing this may break older code (including
            # old versions of xmlrpclib.py), so this is better left as
            # is for now.  See @XMLRPC3 for more information. /F
            write("<params>\n")
            for v in values:
                write("<param>\n")
                dump(v, write)
                write("</param>\n")
            write("</params>\n")
        result = string.join(out, "")
        return result
    
    def __dump(self, value, write):
        try:
            f = self.dispatch[type(value)]
        except KeyError:
            raise TypeError, "cannot marshal %s objects" % type(value)
        else:
            f(self, value, write)
    
    def dump_nil (self, value, write):
        if not self.allow_none:
            raise TypeError, "cannot marshal None unless allow_none is enabled"
        write("<value><nil/></value>")
    dispatch[NoneType] = dump_nil
    
    def dump_int(self, value, write):
        # in case ints are > 32 bits
        if value > MAXINT or value < MININT:
            raise OverflowError, "int exceeds XML-RPC limits"
        write("<value><int>")
        write(str(value))
        write("</int></value>\n")
    dispatch[IntType] = dump_int
    
    if _bool_is_builtin:
        def dump_bool(self, value, write):
            write("<value><boolean>")
            write(value and "1" or "0")
            write("</boolean></value>\n")
        dispatch[bool] = dump_bool
    
    def dump_long(self, value, write):
        if value > MAXINT or value < MININT:
            raise OverflowError, "long int exceeds XML-RPC limits"
        write("<value><int>")
        write(str(int(value)))
        write("</int></value>\n")
    dispatch[LongType] = dump_long
    
    def dump_double(self, value, write):
        write("<value><double>")
        write(repr(value))
        write("</double></value>\n")
    dispatch[FloatType] = dump_double
    
    def dump_string(self, value, write, escape=escape):
        write("<value><string>")
        write(escape(value))
        write("</string></value>\n")
    dispatch[StringType] = dump_string
    
    if unicode:
        def dump_unicode(self, value, write, escape=escape):
            value = value.encode(self.encoding)
            write("<value><string>")
            write(escape(value))
            write("</string></value>\n")
        dispatch[UnicodeType] = dump_unicode
    
    def dump_array(self, value, write):
        i = id(value)
        if self.memo.has_key(i):
            raise TypeError, "cannot marshal recursive sequences"
        self.memo[i] = None
        dump = self.__dump
        write("<value><array><data>\n")
        for v in value:
            dump(v, write)
        write("</data></array></value>\n")
        del self.memo[i]
    dispatch[TupleType] = dump_array
    dispatch[ListType] = dump_array
    
    def dump_struct(self, value, write, escape=escape):
        i = id(value)
        if self.memo.has_key(i):
            raise TypeError, "cannot marshal recursive dictionaries"
        self.memo[i] = None
        dump = self.__dump
        write("<value><struct>\n")
        for k, v in value.items():
            write("<member>\n")
            if type(k) is not StringType:
                if unicode and type(k) is UnicodeType:
                    k = k.encode(self.encoding)
                else:
                    raise TypeError, "dictionary key must be string"
            write("<name>%s</name>\n" % escape(k))
            dump(v, write)
            write("</member>\n")
        write("</struct></value>\n")
        del self.memo[i]
    dispatch[DictType] = dump_struct
    
    if datetime:
        def dump_datetime(self, value, write):
            if self.convert_datetimes_to_utc:
                if value.tzinfo == None:
                    value = value.replace(tzinfo = sg_timezone.local)
                value = value.astimezone(sg_timezone.utc)
            write("<value><dateTime.iso8601>")
            write(value.strftime("%Y%m%dT%H:%M:%S"))
            write("</dateTime.iso8601></value>\n")
        dispatch[datetime.datetime] = dump_datetime
        
        def dump_date(self, value, write):
            write("<value><dateTime.iso8601>")
            write(value.strftime("%Y%m%dT00:00:00"))
            write("</dateTime.iso8601></value>\n")
        dispatch[datetime.date] = dump_date
        
        def dump_time(self, value, write):
            if self.convert_datetimes_to_utc:
                if value.tzinfo == None:
                    value = value.replace(tzinfo = sg_timezone.local)
                value = value.astimezone(sg_timezone.utc)
            write("<value><dateTime.iso8601>")
            write(datetime.datetime.now().date().strftime("%Y%m%dT"))
            write(value.strftime("%H:%M:%S"))
            write("</dateTime.iso8601></value>\n")
        dispatch[datetime.time] = dump_time
    
    def dump_instance(self, value, write):
        # check for special wrappers
        if value.__class__ in WRAPPERS:
            self.write = write
            value.encode(self)
            del self.write
        else:
            # store instance attributes as a struct (really?)
            self.dump_struct(value.__dict__, write)
    dispatch[InstanceType] = dump_instance

##
# XML-RPC unmarshaller.
#
# @see loads

class Unmarshaller:
    """Unmarshal an XML-RPC response, based on incoming XML event
    messages (start, data, end).  Call close() to get the resulting
    data structure.
    
    Note that this reader is fairly tolerant, and gladly accepts bogus
    XML-RPC data without complaining (but not bogus XML).
    """
    
    # and again, if you don't understand what's going on in here,
    # that's perfectly ok.
    
    def __init__(self, use_datetime=1, convert_datetimes_to_utc=1):
        self._type = None
        self._stack = []
        self._marks = []
        self._data = []
        self._methodname = None
        self._encoding = "utf-8"
        self.append = self._stack.append
        self._use_datetime = use_datetime
        self._convert_datetimes_to_utc = convert_datetimes_to_utc
        if use_datetime and not datetime:
            raise ValueError, "the datetime module is not available"
    
    def close(self):
        # return response tuple and target method
        if self._type is None or self._marks:
            raise ResponseError()
        if self._type == "fault":
            raise Fault(**self._stack[0])
        return tuple(self._stack)
    
    def getmethodname(self):
        return self._methodname
    
    #
    # event handlers
    
    def xml(self, encoding, standalone):
        self._encoding = encoding
        # FIXME: assert standalone == 1 ???
    
    def start(self, tag, attrs):
        # prepare to handle this element
        if tag == "array" or tag == "struct":
            self._marks.append(len(self._stack))
        self._data = []
        self._value = (tag == "value")
    
    def data(self, text):
        self._data.append(text)
    
    def end(self, tag, join=string.join):
        # call the appropriate end tag handler
        try:
            f = self.dispatch[tag]
        except KeyError:
            pass # unknown tag ?
        else:
            return f(self, join(self._data, ""))
    
    #
    # accelerator support
    
    def end_dispatch(self, tag, data):
        # dispatch data
        try:
            f = self.dispatch[tag]
        except KeyError:
            pass # unknown tag ?
        else:
            return f(self, data)
    
    #
    # element decoders
    
    dispatch = {}
    
    def end_nil (self, data):
        self.append(None)
        self._value = 0
    dispatch["nil"] = end_nil
    
    def end_boolean(self, data):
        if data == "0":
            self.append(False)
        elif data == "1":
            self.append(True)
        else:
            raise TypeError, "bad boolean value"
        self._value = 0
    dispatch["boolean"] = end_boolean
    
    def end_int(self, data):
        self.append(int(data))
        self._value = 0
    dispatch["i4"] = end_int
    dispatch["int"] = end_int
    
    def end_double(self, data):
        self.append(float(data))
        self._value = 0
    dispatch["double"] = end_double
    
    def end_string(self, data):
        if self._encoding:
            data = _decode(data, self._encoding)
        self.append(_stringify(data))
        self._value = 0
    dispatch["string"] = end_string
    dispatch["name"] = end_string # struct keys are always strings
    
    def end_array(self, data):
        mark = self._marks.pop()
        # map arrays to Python lists
        self._stack[mark:] = [self._stack[mark:]]
        self._value = 0
    dispatch["array"] = end_array
    
    def end_struct(self, data):
        mark = self._marks.pop()
        # map structs to Python dictionaries
        dict = {}
        items = self._stack[mark:]
        for i in range(0, len(items), 2):
            dict[_stringify(items[i])] = items[i+1]
        self._stack[mark:] = [dict]
        self._value = 0
    dispatch["struct"] = end_struct
    
    def end_base64(self, data):
        value = Binary()
        value.decode(data)
        self.append(value)
        self._value = 0
    dispatch["base64"] = end_base64
    
    def end_dateTime(self, data):
        if self._use_datetime:
            value = _datetime_type(data)
            if self._convert_datetimes_to_utc:
                value = value.replace(tzinfo = sg_timezone.utc).astimezone(sg_timezone.local)
        else:
            value = DateTime()
            value.decode(data)
        self.append(value)
    dispatch["dateTime.iso8601"] = end_dateTime
    
    def end_value(self, data):
        # if we stumble upon a value element with no internal
        # elements, treat it as a string element
        if self._value:
            self.end_string(data)
    dispatch["value"] = end_value
    
    def end_params(self, data):
        self._type = "params"
    dispatch["params"] = end_params
    
    def end_fault(self, data):
        self._type = "fault"
    dispatch["fault"] = end_fault
    
    def end_methodName(self, data):
        if self._encoding:
            data = _decode(data, self._encoding)
        self._methodname = data
        self._type = "methodName" # no params
    dispatch["methodName"] = end_methodName

## Multicall support
#

class _MultiCallMethod:
    # some lesser magic to store calls made to a MultiCall object
    # for batch execution
    def __init__(self, call_list, name):
        self.__call_list = call_list
        self.__name = name
    def __getattr__(self, name):
        return _MultiCallMethod(self.__call_list, "%s.%s" % (self.__name, name))
    def __call__(self, *args):
        self.__call_list.append((self.__name, args))

class MultiCallIterator:
    """Iterates over the results of a multicall. Exceptions are
    thrown in response to xmlrpc faults."""
    
    def __init__(self, results):
        self.results = results
    
    def __getitem__(self, i):
        item = self.results[i]
        if type(item) == type({}):
            raise Fault(item['faultCode'], item['faultString'])
        elif type(item) == type([]):
            return item[0]
        else:
            raise ValueError,\
                  "unexpected type in multicall result"

class MultiCall:
    """server -> a object used to boxcar method calls
    
    server should be a ServerProxy object.
    
    Methods can be added to the MultiCall using normal
    method call syntax e.g.:
    
    multicall = MultiCall(server_proxy)
    multicall.add(2,3)
    multicall.get_address("Guido")
    
    To execute the multicall, call the MultiCall object e.g.:
    
    add_result, address = multicall()
    """
    
    def __init__(self, server):
        self.__server = server
        self.__call_list = []
    
    def __repr__(self):
        return "<MultiCall at %x>" % id(self)
    
    __str__ = __repr__
    
    def __getattr__(self, name):
        return _MultiCallMethod(self.__call_list, name)
    
    def __call__(self):
        marshalled_list = []
        for name, args in self.__call_list:
            marshalled_list.append({'methodName' : name, 'params' : args})
        
        return MultiCallIterator(self.__server.system.multicall(marshalled_list))

# --------------------------------------------------------------------
# convenience functions

##
# Create a parser object, and connect it to an unmarshalling instance.
# This function picks the fastest available XML parser.
#
# return A (parser, unmarshaller) tuple.

def getparser(use_datetime=1, convert_datetimes_to_utc=1):
    """getparser() -> parser, unmarshaller
    
    Create an instance of the fastest available parser, and attach it
    to an unmarshalling object.  Return both objects.
    """
    if use_datetime and not datetime:
        raise ValueError, "the datetime module is not available"
    if FastParser and FastUnmarshaller:
        if use_datetime:
            mkdatetime = _datetime_type
        else:
            mkdatetime = _datetime
        target = FastUnmarshaller(True, False, _binary, mkdatetime, Fault)
        parser = FastParser(target)
    else:
        target = Unmarshaller(use_datetime=use_datetime, convert_datetimes_to_utc=convert_datetimes_to_utc)
        if FastParser:
            parser = FastParser(target)
        elif SgmlopParser:
            parser = SgmlopParser(target)
        elif ExpatParser:
            parser = ExpatParser(target)
        else:
            parser = SlowParser(target)
    return parser, target

##
# Convert a Python tuple or a Fault instance to an XML-RPC packet.
#
# @def dumps(params, **options)
# @param params A tuple or Fault instance.
# @keyparam methodname If given, create a methodCall request for
#     this method name.
# @keyparam methodresponse If given, create a methodResponse packet.
#     If used with a tuple, the tuple must be a singleton (that is,
#     it must contain exactly one element).
# @keyparam encoding The packet encoding.
# @return A string containing marshalled data.

def dumps(params, methodname=None, methodresponse=None, encoding=None,
          allow_none=1, convert_datetimes_to_utc=1):
    """data [,options] -> marshalled data
    
    Convert an argument tuple or a Fault instance to an XML-RPC
    request (or response, if the methodresponse option is used).
    
    In addition to the data object, the following options can be given
    as keyword arguments:
        
        methodname: the method name for a methodCall packet
        
        methodresponse: true to create a methodResponse packet.
        If this option is used with a tuple, the tuple must be
        a singleton (i.e. it can contain only one element).
        
        encoding: the packet encoding (default is UTF-8)
    
    All 8-bit strings in the data structure are assumed to use the
    packet encoding.  Unicode strings are automatically converted,
    where necessary.
    """
    
    assert isinstance(params, TupleType) or isinstance(params, Fault),\
           "argument must be tuple or Fault instance"
    
    if isinstance(params, Fault):
        methodresponse = 1
    elif methodresponse and isinstance(params, TupleType):
        assert len(params) == 1, "response tuple must be a singleton"
    
    if not encoding:
        encoding = "utf-8"
    
    if FastMarshaller:
        m = FastMarshaller(encoding)
    else:
        m = Marshaller(encoding, allow_none, convert_datetimes_to_utc)
    
    data = m.dumps(params)
    
    if encoding != "utf-8":
        xmlheader = "<?xml version='1.0' encoding='%s'?>\n" % str(encoding)
    else:
        xmlheader = "<?xml version='1.0'?>\n" # utf-8 is default
    
    # standard XML-RPC wrappings
    if methodname:
        # a method call
        if not isinstance(methodname, StringType):
            methodname = methodname.encode(encoding)
        data = (
            xmlheader,
            "<methodCall>\n"
            "<methodName>", methodname, "</methodName>\n",
            data,
            "</methodCall>\n"
            )
    elif methodresponse:
        # a method response, or a fault structure
        data = (
            xmlheader,
            "<methodResponse>\n",
            data,
            "</methodResponse>\n"
            )
    else:
        return data # return as is
    return string.join(data, "")

##
# Convert an XML-RPC packet to a Python object.  If the XML-RPC packet
# represents a fault condition, this function raises a Fault exception.
#
# @param data An XML-RPC packet, given as an 8-bit string.
# @return A tuple containing the unpacked data, and the method name
#     (None if not present).
# @see Fault

def loads(data, use_datetime=1, convert_datetimes_to_utc=1):
    """data -> unmarshalled data, method name
    
    Convert an XML-RPC packet to unmarshalled data plus a method
    name (None if not present).
    
    If the XML-RPC packet represents a fault condition, this function
    raises a Fault exception.
    """
    p, u = getparser(use_datetime=use_datetime, convert_datetimes_to_utc=convert_datetimes_to_utc)
    p.feed(data)
    p.close()
    return u.close(), u.getmethodname()


# --------------------------------------------------------------------
# request dispatcher

class _Method:
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
        self.__send = send
        self.__name = name
    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))
    def __call__(self, *args):
        return self.__send(self.__name, args)

##
# Standard transport class for XML-RPC over HTTP.
# <p>
# You can create custom transports by subclassing this method, and
# overriding selected methods.

class Transport:
    """Handles an HTTP transaction to an XML-RPC server."""
    
    # client identifier (may be overridden)
    user_agent = "xmlrpclib.py/%s (by www.pythonware.com)" % __version__
    
    def __init__(self, use_datetime=1, convert_datetimes_to_utc=1):
        self._use_datetime = use_datetime
        self._connection = (None, None)
        self._extra_headers = []
        self._convert_datetimes_to_utc = convert_datetimes_to_utc
    
    ##
    # Send a complete request, and parse the response.
    # Retry request if a cached connection has disconnected.
    #
    # @param host Target host.
    # @param handler Target PRC handler.
    # @param request_body XML-RPC request body.
    # @param verbose Debugging flag.
    # @return Parsed response.
    
    def request(self, host, handler, request_body, verbose=0):
        #retry request once if cached connection has gone cold
        for i in range(10):
            try:
                return self.single_request(host, handler, request_body, verbose)
            except socket.error, (err_num, msg):
                if i >= 10 or err_num not in (errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE):
                    raise
            except httplib.BadStatusLine: #close after we sent request
                if i >= 10:
                    raise
    
    ##
    # Send a complete request, and parse the response.
    #
    # @param host Target host.
    # @param handler Target PRC handler.
    # @param request_body XML-RPC request body.
    # @param verbose Debugging flag.
    # @return Parsed response.
    
    def single_request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request
        
        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)
        
        try:
            self.send_request(h, handler, request_body)
            self.send_host(h, host)
            self.send_user_agent(h)
            self.send_content(h, request_body)
            
            response = h.getresponse()
            if response.status == 200:
                self.verbose = verbose
                return self.parse_response(response)
        except Fault:
            raise
        except Exception:
            # All unexpected errors leave connection in
            # a strange state, so we clear it.
            self.close()
            raise
        
        #discard any response data and raise exception
        if (response.getheader("content-length", 0)):
            response.read()
        raise ProtocolError(
            host + handler,
            response.status, response.reason,
            response.msg,
            )
    
    ##
    # Create parser.
    #
    # @return A 2-tuple containing a parser and a unmarshaller.
    
    def getparser(self):
        # get parser and unmarshaller
        return getparser(use_datetime=self._use_datetime, convert_datetimes_to_utc=self._convert_datetimes_to_utc)
    
    ##
    # Get authorization info from host parameter
    # Host may be a string, or a (host, x509-dict) tuple; if a string,
    # it is checked for a "user:pw@host" format, and a "Basic
    # Authentication" header is added if appropriate.
    #
    # @param host Host descriptor (URL or (URL, x509 info) tuple).
    # @return A 3-tuple containing (actual host, extra headers,
    #     x509 info).  The header and x509 fields may be None.
    
    def get_host_info(self, host):
        
        x509 = {}
        if isinstance(host, TupleType):
            host, x509 = host
        
        import urllib
        auth, host = urllib.splituser(host)
        
        if auth:
            import base64
            auth = base64.encodestring(urllib.unquote(auth))
            auth = string.join(string.split(auth), "") # get rid of whitespace
            extra_headers = [
                ("Authorization", "Basic " + auth)
                ]
        else:
            extra_headers = None
        
        return host, extra_headers, x509
    
    ##
    # Connect to server.
    #
    # @param host Target host.
    # @return A connection handle.
    
    def make_connection(self, host):
        #return an existing connection if possible.  This allows
        #HTTP/1.1 keep-alive.
        if self._connection and host == self._connection[0]:
            return self._connection[1]
        # create a HTTP connection object from a host descriptor
        chost, self._extra_headers, x509 = self.get_host_info(host)
        #store the host argument along with the connection object
        self._connection = host, httplib.HTTPConnection(chost)
        return self._connection[1]
    
    ##
    # Clear any cached connection object.
    # Used in the event of socket errors.
    #
    def close(self):
        if self._connection[1]:
            self._connection[1].close()
            self._connection = (None, None)
    
    ##
    # Send request header.
    #
    # @param connection Connection handle.
    # @param handler Target RPC handler.
    # @param request_body XML-RPC body.
    
    def send_request(self, connection, handler, request_body):
        connection.putrequest("POST", handler)
    
    ##
    # Send host name.
    #
    # @param connection Connection handle.
    # @param host Host name.
    #
    # Note: This function doesn't actually add the "Host"
    # header anymore, it is done as part of the connection.putrequest() in
    # send_request() above.
    
    def send_host(self, connection, host):
        extra_headers = self._extra_headers
        if extra_headers:
            if isinstance(extra_headers, DictType):
                extra_headers = extra_headers.items()
            for key, value in extra_headers:
                connection.putheader(key, value)
    
    ##
    # Send user-agent identifier.
    #
    # @param connection Connection handle.
    
    def send_user_agent(self, connection):
        connection.putheader("User-Agent", self.user_agent)
    
    ##
    # Send request body.
    #
    # @param connection Connection handle.
    # @param request_body XML-RPC request body.
    
    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "text/xml")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)
    
    ##
    # Parse response.
    #
    # @param file Stream.
    # @return Response tuple and target method.
    
    def parse_response(self, file):
        # compatibility interface
        return self._parse_response(file, None)
    
    ##
    # Parse response (alternate interface).  This is similar to the
    # parse_response method, but also provides direct access to the
    # underlying socket object (where available).
    #
    # @param file Stream.
    # @param sock Socket handle (or None, if the socket object
    #    could not be accessed).
    # @return Response tuple and target method.
    
    def _parse_response(self, file, sock):
        # read response from input file/socket, and parse it
        
        p, u = self.getparser()
        
        while 1:
            if sock:
                response = sock.recv(1024)
            else:
                response = file.read(1024)
            if not response:
                break
            if self.verbose:
                print "body:", repr(response)
            p.feed(response)
        
        file.close()
        p.close()
        
        return u.close()

##
# Standard transport class for XML-RPC over HTTPS.

class SafeTransport(Transport):
    """Handles an HTTPS transaction to an XML-RPC server."""
    
    # FIXME: mostly untested
    
    def make_connection(self, host):
        #return an existing connection if possible.  This allows
        #HTTP/1.1 keep-alive.
        if self._connection and host == self._connection[0]:
            return self._connection[1]
        # create a HTTPS connection object from a host descriptor
        # host may be a string, or a (host, x509-dict) tuple
        try:
            HTTPS = httplib.HTTPSConnection
        except AttributeError:
            raise NotImplementedError(
                "your version of httplib doesn't support HTTPS"
                )
        else:
            chost, self._extra_headers, x509 = self.get_host_info(host)
            self._connection = host, HTTPS(chost, None, **(x509 or {}))
            return self._connection[1]

# From example here, modified for keepalive changes:  http://docs.python.org/library/xmlrpclib.html
class ProxiedTransport(Transport):
    
    def set_proxy(self, proxy):
        self.proxy = proxy
    
    def make_connection(self, host):
        self.realhost = host
        host = self.proxy
        #return an existing connection if possible.  This allows
        #HTTP/1.1 keep-alive.
        if self._connection and host == self._connection[0]:
            return self._connection[1]
        # create a HTTP connection object from a host descriptor
        chost, self._extra_headers, x509 = self.get_host_info(host)
        #store the host argument along with the connection object
        self._connection = host, httplib.HTTPConnection(chost)
        return self._connection[1]
    
    def send_request(self, connection, handler, request_body):
        connection.putrequest("POST", 'http://%s%s' % (self.realhost, handler))


##
# Standard server proxy.  This class establishes a virtual connection
# to an XML-RPC server.
# <p>
# This class is available as ServerProxy and Server.  New code should
# use ServerProxy, to avoid confusion.
#
# @def ServerProxy(uri, **options)
# @param uri The connection point on the server.
# @keyparam transport A transport factory, compatible with the
#    standard transport class.
# @keyparam encoding The default encoding used for 8-bit strings
#    (default is UTF-8).
# @keyparam verbose Use a true value to enable debugging output.
#    (printed to standard output).
# @see Transport

class ServerProxy:
    """uri [,options] -> a logical connection to an XML-RPC server
    
    uri is the connection point on the server, given as
    scheme://host/target.
    
    The standard implementation always supports the "http" scheme.  If
    SSL socket support is available (Python 2.0), it also supports
    "https".
    
    If the target part and the slash preceding it are both omitted,
    "/RPC2" is assumed.
    
    The following options can be given as keyword arguments:
        
        transport: a transport factory
        encoding: the request encoding (default is UTF-8)
    
    All 8-bit strings passed to the server proxy are assumed to use
    the given encoding.
    """
    
    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                 allow_none=1, use_datetime=1, convert_datetimes_to_utc=1):
        # establish a "logical" server connection
        
        # get the url
        import urllib
        type, uri = urllib.splittype(uri)
        if type not in ("http", "https"):
            raise IOError, "unsupported XML-RPC protocol"
        self.__host, self.__handler = urllib.splithost(uri)
        if not self.__handler:
            self.__handler = "/RPC2"
        
        if transport is None:
            if type == "https":
                transport = SafeTransport(use_datetime=use_datetime, convert_datetimes_to_utc=convert_datetimes_to_utc)
            else:
                transport = Transport(use_datetime=use_datetime, convert_datetimes_to_utc=convert_datetimes_to_utc)
        self.__transport = transport
        
        self.__encoding = encoding
        self.__verbose = verbose
        self.__allow_none = allow_none
        self.__convert_datetimes_to_utc = convert_datetimes_to_utc
    
    def __close(self):
        self.__transport.close()
    
    def __request(self, methodname, params):
        # call a method on the remote server
        
        request = dumps(params, methodname, encoding=self.__encoding,
                        allow_none=self.__allow_none, convert_datetimes_to_utc=self.__convert_datetimes_to_utc)
        
        response = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=self.__verbose
            )
        
        if len(response) == 1:
            response = response[0]
        
        return response
    
    def __repr__(self):
        return (
            "<ServerProxy for %s%s>" %
            (self.__host, self.__handler)
            )
    
    __str__ = __repr__
    
    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self.__request, name)
    
    # note: to call a remote object with an non-standard name, use
    # result getattr(server, "strange-python-name")(args)
    
    def __call__(self, attr):
        """A workaround to get special attributes on the ServerProxy
           without interfering with the magic __getattr__
        """
        if attr == "close":
            return self.__close
        elif attr == "transport":
            return self.__transport
        raise AttributeError("Attribute %r not found" % (attr,))

# compatibility

Server = ServerProxy

# --------------------------------------------------------------------
# test code

# if __name__ == "__main__":
#
#     # simple test program (from the XML-RPC specification)
#
#     # server = ServerProxy("http://localhost:8000") # local server
#     server = ServerProxy("http://time.xmlrpc.com/RPC2")
#
#     print server
#
#     try:
#         print server.currentTime.getCurrentTime()
#     except Error, v:
#         print "ERROR", v
#
#     multi = MultiCall(server)
#     multi.currentTime.getCurrentTime()
#     multi.currentTime.getCurrentTime()
#     try:
#         for response in multi():
#             print response
#     except Error, v:
#         print "ERROR", v

if __name__ == "__main__":
    from pprint import pprint
    
    sg = Shotgun('http://localhost:3000', 'wrapper_script', 'ca8e878c9c7f6d8ab3bf1d92fd1a624361cf4e6e')
    
    # for i in range(1001,5000):
    #     pprint(sg.create("Asset",{"code":"Asset %d"%i,"project_names":"Test Project"}))
    #
    # pprint(sg.find("Asset",filters=[], filter_operator='any', fields=['code','image']))
    # sg.upload("Asset", 1, "/path/to/file.png", display_name="My File", field_name="sg_attachment")
