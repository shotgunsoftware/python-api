"""Tests agains the client software that do not involve calling the 
CRUD functions. These tests always use a mock http connection so not not 
need a live server to run against."""

import base64
import datetime
import re
try:
    import simplejson as json
except ImportError:
    import json as json
import platform
import sys
import time
import unittest

import mock
import shotgun_api3 as api

import base

class TestShotgunClient(base.TestBase):
    def __init__(self, *args, **kws):
        super(TestShotgunClient, self).__init__(*args, **kws)

    def setUp(self):
        super(TestShotgunClient, self).setUp()
        #get domain and uri scheme
        match = re.search('(https?://)(.*)', self.server_url)
        self.uri_prefix = match.group(1)
        self.domain     = match.group(2)
        #always want the mock on
        self._setup_mock()
        
    def test_detect_caps(self):
        """Client and server capabilities detected"""

        self.sg.connect()
        self.assertEqual(1, self.sg._http_request.call_count)
        
        self.assertTrue(self.sg.client_caps is not None)
        self.assertTrue(self.sg.client_caps.platform in (
            "windows", "linux", "mac"))
        self.assertTrue(self.sg.client_caps.local_path_field.startswith(
            "local_path"))
        self.assertTrue(str(self.sg.client_caps).startswith(
            "ClientCapabilities"))
        self.assertTrue(self.sg.client_caps.py_version.startswith(
            str(sys.version_info[0])))
        self.assertTrue(self.sg.client_caps.py_version.endswith(
            str(sys.version_info[1])))

        
        #has paging is tested else where.
        server_info = {
            "version" : [9,9,9]
        }
        self._mock_http(server_info)
        # ensrue the server caps is re-read
        self.sg._server_caps = None
        self.assertTrue(self.sg.server_caps is not None)
        self.assertFalse(self.sg.server_caps.is_dev)
        self.assertEqual((9,9,9), self.sg.server_caps.version)
        self.assertTrue(self.server_url.endswith(self.sg.server_caps.host))
        self.assertTrue(self.sg.server_caps.has_paging)
        self.assertTrue(str(self.sg.server_caps).startswith(
            "ServerCapabilities"))
        self.assertEqual(server_info, self.sg.server_info)

        
        self._mock_http({
            "version" : [9,9,9, "Dev"]
        })
        self.sg._server_caps = None
        self.assertTrue(self.sg.server_caps.is_dev)
        
        return
    
    def test_server_version(self):
        """Server supports json API"""
        
        sc = api.ServerCapabilities("foo", {"version" : (2,4,0)})
        
        sc.version = (2,3,99)
        self.assertRaises(api.ShotgunError, sc._ensure_json_supported)
        self.assertRaises(api.ShotgunError, api.ServerCapabilities, "foo", 
            {"version" : (2,2,0)})
            
        sc.version = (0,0,0)
        self.assertRaises(api.ShotgunError, sc._ensure_json_supported)
        
        sc.version = (2,4,0)
        sc._ensure_json_supported()
        
        sc.version = (2,5,0)
        sc._ensure_json_supported()
        
        return
        
    def test_session_uuid(self):
        """Session UUID is included in request"""
        
        #ok for the mock server to just return an error, we want to look at 
        #whats in the request 
        self._mock_http({
            "message":"Go BANG",
            "exception":True
        })
        
        def auth_args():
            args, _ = self.sg._http_request.call_args
            verb, path, body, headers = args
            body = json.loads(body)
            return body["params"][0]

        self.sg.set_session_uuid(None)
        self.assertRaises(api.Fault, self.sg.delete, "FakeType", 1)
        self.assertTrue("session_uuid" not in auth_args())
        
        my_uuid = '5a1d49b0-0c69-11e0-a24c-003048d17544'
        self.sg.set_session_uuid(my_uuid)
        self.assertRaises(api.Fault, self.sg.delete, "FakeType", 1)
        self.assertEqual(my_uuid, auth_args()["session_uuid"])
        return
        
    def test_config(self):
        """Client config can be created"""
        x = api._Config()
        self.assertTrue(x is not None)
        
    def test_url(self):
        """Server url is parsed correctly"""
        login    = self.human_user['login']
        password = self.human_password
        
        self.assertRaises(ValueError, api.Shotgun, None, None, None)
        self.assertRaises(ValueError, api.Shotgun, "file://foo.com",None,None)
        
        self.assertEqual("/api3/json", self.sg.config.api_path)
        
        #support auth details in the url of the form 
        login_password = "%s:%s" % (login, password)
        # login:password@domain
        auth_url = "%s%s@%s" % (self.uri_prefix, login_password, self.domain)
        sg = api.Shotgun(auth_url, None, None)
        expected = "Basic " + base64.encodestring(login_password).strip()
        self.assertEqual(expected, sg.config.authorization)
        
        return
    
    def test_authorization(self):
        """Authorization passed to server"""
        login    = self.human_user['login']
        password = self.human_password
        login_password = "%s:%s" % (login, password)
        # login:password@domain
        auth_url = "%s%s@%s" % (self.uri_prefix, login_password, self.domain)
        
        
        self.sg = api.Shotgun(auth_url, "foo", "bar")
        self._setup_mock()
        self._mock_http({
            'version': [2, 4, 0, u'Dev']
        })
        
        self.sg.info()
        
        args, _ = self.sg._http_request.call_args
        verb, path, body, headers = args
        
        expected = "Basic " + base64.encodestring(login_password).strip()
        self.assertEqual(expected, headers.get("Authorization"))
        return
        
    def test_connect_close(self):
        """Connection is closed and opened."""
        
        #The mock created an existing mock connection, 
        self.sg.connect()
        self.assertEqual(0, self.mock_conn.request.call_count)
        self.sg.close()
        self.assertEqual(None, self.sg._connection)
        return
        
    def test_has_paging(self):
        """Server paging detected"""
        
        #tricky because we now only support version > 2.4
        sc = api.ServerCapabilities("foo", {"version" : (2,4,0)})
        
        self.assertFalse(sc._is_paging((0,0,0)), 
            "no version has no paging")
        self.assertFalse(sc._is_paging((2,3,3)), 
            "2,3,3, has no paging")
        self.assertTrue(sc._is_paging((2,3,4)), 
            "2,3,4, has paging")
        self.assertTrue(sc._is_paging((2,3,5)), 
            "2,3,5, has paging")
        self.assertTrue(sc._is_paging((2,4,0)), 
            "any 2.4 has paging")

    def test_network_retry(self):
        """Network failure is retried"""
        
        self.sg._http_request.side_effect = api.HttpLib2Error
        
        self.assertRaises(api.HttpLib2Error, self.sg.info)
        self.assertTrue(
            self.sg.config.max_rpc_attempts ==self.sg._http_request.call_count, 
            "Call is repeated")
        return

    def test_http_error(self):
        """HTTP error raised and not retried."""
        
        self._mock_http(
            "big old error string", 
            status=(500, "Internal Server Error")
        )
                
        self.assertRaises(RuntimeError, self.sg.info)
        self.assertEqual(1, self.sg._http_request.call_count, 
            "Call is not repeated")
        return
        
    def test_rpc_error(self):
        """RPC error transformed into Python error"""
        
        self._mock_http({
            "message":"Go BANG",
            "exception":True
        })
        
        self.assertRaises(api.Fault, self.sg.info)
        
        try:
            self.sg.info()
        except api.Fault, e:
            self.assertEqual("Go BANG", str(e))
            
    def test_call_rpc(self):
        """Named rpc method is called and results handled"""
        
        d = {
            "no-results" : "data without a results key"
        }
        self._mock_http(d)
        rv = self.sg._call_rpc("no-results", None)
        self._assert_http_method("no-results", None)
        self.assertEqual(d, rv, 
            "rpc response without results key is returned as-is")
        
        d = {
            "results" : {"singleton" : "result"}
        }
        self._mock_http(d)
        rv = self.sg._call_rpc("singleton", None)
        self._assert_http_method("singleton", None)
        self.assertEqual(d["results"], rv, 
            "rpc response with singleton result")
        
        d = {
            "results" : ["foo", "bar"]
        }
        a = {"some" : "args"}
        self._mock_http(d)
        rv = self.sg._call_rpc("list", a)
        self._assert_http_method("list", a)
        self.assertEqual(d["results"], rv, 
            "rpc response with list result")
            
        d = {
            "results" : ["foo", "bar"]
        }
        a = {"some" : "args"}
        self._mock_http(d)
        rv = self.sg._call_rpc("list-first", a, first=True)
        self._assert_http_method("list-first", a)
        self.assertEqual(d["results"][0], rv, 
            "rpc response with list result, first item")
        
    def test_transform_data(self):
        """Outbound data is transformed"""
        
        timestamp = time.time()
        #microseconds will be last during transforms
        now = datetime.datetime.fromtimestamp(timestamp).replace(
            microsecond=0)
        utc_now = datetime.datetime.utcfromtimestamp(timestamp).replace(
            microsecond=0)
        local = {
            "date" : now.strftime('%Y-%m-%d'),
            "datetime" : now,
            "time" : now.time()
        }
        #date will still be the local date, because they are not transformed
        utc = {
            "date" : now.strftime('%Y-%m-%d'),
            "datetime": utc_now, 
            "time" : utc_now.time()
        }
        
        def _datetime(s, f):
            return datetime.datetime(*time.strptime(s, f)[:6])
            
        def assert_wire(wire, match):
            self.assertTrue(isinstance(wire["date"], basestring))
            d = _datetime(wire["date"], "%Y-%m-%d").date()
            d = wire['date']
            self.assertEqual(match["date"], d)
            self.assertTrue(isinstance(wire["datetime"], basestring))
            d = _datetime(wire["datetime"], "%Y-%m-%dT%H:%M:%SZ")
            self.assertEqual(match["datetime"], d)
            self.assertTrue(isinstance(wire["time"], basestring))
            d = _datetime(wire["time"], "%Y-%m-%dT%H:%M:%SZ")
            self.assertEqual(match["time"], d.time())
            
        #leave as local
        #AMORTON: tests disabled for now, always have utc over the wire
        # self.sg.config.convert_datetimes_to_utc = False
        # wire = self.sg._transform_outbound(local)
        # print "local ", local
        # print "wire ", wire
        # assert_wire(wire, local)
        # wire = self.sg._transform_inbound(wire)
        # #times will become datetime over the wire
        # wire["time"] = wire["time"].time()
        # self.assertEqual(local, wire)
        
        self.sg.config.convert_datetimes_to_utc = True
        wire = self.sg._transform_outbound(local)
        assert_wire(wire, utc)
        wire = self.sg._transform_inbound(wire)
        #times will become datetime over the wire
        wire["time"] = wire["time"].time()
        self.assertEqual(local, wire)
        return
        
    def test_encode_payload(self):
        """Request body is encoded as JSON"""
        
        d = {
            "this is " : u"my data \u00E0"
        }
        j = self.sg._encode_payload(d)
        self.assertTrue(isinstance(j, str))
        
        d = {
            "this is " : u"my data"
        }
        j = self.sg._encode_payload(d)
        self.assertTrue(isinstance(j, str))
        
    def test_decode_response(self):
        """HTTP Response is decoded as JSON or text"""
        
        headers = {
            "content-type" : "application/json;charset=utf-8"
        }
        d = {
            "this is " : u"my data \u00E0"
        }
        j = json.dumps(d, ensure_ascii=False, encoding="utf-8")        
        self.assertEqual(d, self.sg._decode_response(headers, j))
        
        headers["content-type"] = "text/javascript"
        self.assertEqual(d, self.sg._decode_response(headers, j))

        headers["content-type"] = "text/foo"
        self.assertEqual(j, self.sg._decode_response(headers, j))
        
    def test_parse_records(self):
        """Parse records to replace thumbnail and local paths"""
        
        system = platform.system().lower()
        if system =='darwin':
            local_path_field = "local_path_mac"
        elif system == 'windows':
            local_path_field = "local_path_windows"
        elif system == 'linux':
            local_path_field = "local_path_linux"
        orig = {
            "type" : "FakeAsset", 
            "id" : 1234, 
            "image" : "blah",
            "foo" : {
                "link_type" : "local",
                local_path_field: "/foo/bar.jpg", 
            }
        }
        url = "http://foo/files/0000/0000/0012/232/shot_thumb.jpg"
        self.sg._build_thumb_url = mock.Mock(
            return_value=url)
        
        modified, txt = self.sg._parse_records([orig, "plain text"])        
        self.assertEqual("plain text", txt, 
            "non dict value is left as is")

        self.sg._build_thumb_url.assert_called_once_with("FakeAsset", 1234)
        
        self.assertEqual(url, modified["image"], 
            "image path changed to url path")
        self.assertEqual("/foo/bar.jpg", modified["foo"]["local_path"])
        self.assertEqual("file:///foo/bar.jpg", modified["foo"]["url"])
        
        return
        
    def test_thumb_url(self):
        """Thumbnail endpoint used to get thumbnail url"""
        
        #the thumbnail service returns a two line 
        #test response success code on line 1, data on line 2
        resp = "1\n/files/0000/0000/0012/232/shot_thumb.jpg"
        self._mock_http(resp, headers={"content-type" : "text/plain"})
        self.sg.config.scheme = "http"
        self.sg.config.server = "foo.com"
        
        url = self.sg._build_thumb_url("FakeAsset", 1234)
        
        self.assertEqual(
            "http://foo.com/files/0000/0000/0012/232/shot_thumb.jpg", url)
        self.assertTrue(self.sg._http_request.called, 
            "http request made to get url")
        args, _ = self.sg._http_request.call_args
        verb, path, body, headers = args
        self.assertEqual(
            "/upload/get_thumbnail_url?entity_type=FakeAsset&entity_id=1234",
            path, "thumbnail url called with correct args")
        
        resp = "0\nSome Error"
        self._mock_http(resp, headers={"content-type" : "text/plain"})
        self.assertRaises(api.ShotgunError, self.sg._build_thumb_url, 
            "FakeAsset", 456)
        
        resp = "99\nSome Error"
        self._mock_http(resp, headers={"content-type" : "text/plain"})
        self.assertRaises(RuntimeError, self.sg._build_thumb_url, 
            "FakeAsset", 456)
        return

class TestCreateSummaryRequest(base.TestBase):
    '''Test case for _create_summary_request function and parameter
    validation as it exists in Shotgun.summarize.

    Does not require database connection or test data.'''

    def test_filter_operator_none(self):
        expected_logical_operator = 'and'
        filter_operator = None
        result = api._create_summary_request('',[],None,filter_operator, None) 
        actual_logical_operator = result['filters']['logical_operator']
        self.assertEqual(expected_logical_operator, actual_logical_operator)

    def test_filter_operator_all(self):
        expected_logical_operator = 'and'
        filter_operator = 'all'
        result = api._create_summary_request('',[],None,filter_operator, None) 
        actual_logical_operator = result['filters']['logical_operator']
        self.assertEqual(expected_logical_operator, actual_logical_operator)

    def test_filter_operator_none(self):
        expected_logical_operator = 'or'
        filter_operator = 'or'
        result = api._create_summary_request('',[],None,filter_operator, None) 
        actual_logical_operator = result['filters']['logical_operator']
        self.assertEqual(expected_logical_operator, actual_logical_operator)

    def test_filters(self):
        path = 'path'
        relation = 'relation'
        value = 'value'
        expected_condition = {'path':path, 'relation':relation, 'value':value}
        result = api._create_summary_request('', [[path, relation, value]], None, None, None) 
        actual_condition = result['filters']['conditions'][0]

    def test_grouping(self):
        result = api._create_summary_request('', [], None, None, None) 
        self.assertFalse(result.has_key('grouping'))
        grouping = ['something']
        result = api._create_summary_request('', [], None, None, grouping) 
        self.assertEqual(grouping, result['grouping'])

    def test_filters_type(self):
        '''test_filters_type tests that filters parameter is a list'''
        self.assertRaises(ValueError, self.sg.summarize, '', 'not a list', [])

    def test_grouping_type(self):
        '''test_grouping_type tests that grouping parameter is a list or None'''
        self.assertRaises(ValueError, self.sg.summarize, '', [], [], grouping='Not a list')
if __name__ == '__main__':
    unittest.main()
