"""Tests against the client software that do not involve calling the
CRUD functions. These tests always use a mock http connection so not not
need a live server to run against."""

import base64
import datetime
import re
try:
    import simplejson as json
except ImportError:
    try:
        import json as json
    except ImportError:
        import shotgun_api3.lib.simplejson as json

import platform
import sys
import time
import unittest
import mock

import shotgun_api3.lib.httplib2 as httplib2
import shotgun_api3 as api
from shotgun_api3.shotgun import ServerCapabilities, SG_TIMEZONE
import base

class TestShotgunClient(base.MockTestBase):
    '''Test case for shotgun api with server interactions mocked.'''

    def setUp(self):
        super(TestShotgunClient, self).setUp()
        #get domain and uri scheme
        match = re.search('(https?://)(.*)', self.server_url)
        self.uri_prefix = match.group(1)
        self.domain     = match.group(2)
        #always want the mock on
        self._setup_mock()

    def test_detect_client_caps(self):
        """Client and server capabilities detected"""
        client_caps = self.sg.client_caps
        self.sg.connect()
        self.assertEqual(1, self.sg._http_request.call_count)

        self.assertTrue(client_caps is not None)
        self.assertTrue(client_caps.platform in ("windows", "linux", "mac"))
        self.assertTrue(client_caps.local_path_field.startswith("local_path"))
        self.assertTrue(str(client_caps).startswith("ClientCapabilities"))
        self.assertTrue(client_caps.py_version.startswith(str(sys.version_info[0])))
        self.assertTrue(client_caps.py_version.endswith(str(sys.version_info[1])))

    def test_detect_server_caps(self):
        '''test_detect_server_caps tests that ServerCapabilities object is made
        with appropriate settings for given server version.'''
        #has paging is tested else where.
        server_info = { "version" : [9,9,9] }
        self._mock_http(server_info)
        # ensrue the server caps is re-read
        self.sg._server_caps = None
        self.assertTrue(self.sg.server_caps is not None)
        self.assertFalse(self.sg.server_caps.is_dev)
        self.assertEqual((9,9,9), self.sg.server_caps.version)
        self.assertTrue(self.server_url.endswith(self.sg.server_caps.host))
        self.assertTrue(str(self.sg.server_caps).startswith( "ServerCapabilities"))
        self.assertEqual(server_info, self.sg.server_info)

        self._mock_http({ "version" : [9,9,9, "Dev"] })
        self.sg._server_caps = None
        self.assertTrue(self.sg.server_caps.is_dev)


    def test_server_version_json(self):
        '''test_server_version_json tests expected versions for json support.'''
        sc = ServerCapabilities("foo", {"version" : (2,4,0)})

        sc.version = (2,3,99)
        self.assertRaises(api.ShotgunError, sc._ensure_json_supported)
        self.assertRaises(api.ShotgunError, ServerCapabilities, "foo",
            {"version" : (2,2,0)})

        sc.version = (0,0,0)
        self.assertRaises(api.ShotgunError, sc._ensure_json_supported)

        sc.version = (2,4,0)
        sc._ensure_json_supported()

        sc.version = (2,5,0)
        sc._ensure_json_supported()


    def test_session_uuid(self):
        """test_session_uuid tests session UUID is included in request"""
        #ok for the mock server to just return an error, we want to look at
        #whats in the request
        self._mock_http({ "message":"Go BANG",
                          "exception":True })

        def auth_args():
            args = self.sg._http_request.call_args[0]
            body = args[2]
            body = json.loads(body)
            return body["params"][0]

        self.sg.set_session_uuid(None)
        self.assertRaises(api.Fault, self.sg.delete, "FakeType", 1)
        self.assertTrue("session_uuid" not in auth_args())

        my_uuid = '5a1d49b0-0c69-11e0-a24c-003048d17544'
        self.sg.set_session_uuid(my_uuid)
        self.assertRaises(api.Fault, self.sg.delete, "FakeType", 1)
        self.assertEqual(my_uuid, auth_args()["session_uuid"])

    def test_config(self):
        """Client config can be created"""
        x = api.shotgun._Config()
        self.assertTrue(x is not None)

    def test_url(self):
        """Server url is parsed correctly"""
        login    = self.human_user['login']
        password = self.human_password

        self.assertRaises(ValueError, api.Shotgun, None, None, None, connect=False)
        self.assertRaises(ValueError, api.Shotgun, "file://foo.com",None,None, connect=False)

        self.assertEqual("/api3/json", self.sg.config.api_path)

        #support auth details in the url of the form
        login_password = "%s:%s" % (login, password)
        # login:password@domain
        auth_url = "%s%s@%s" % (self.uri_prefix, login_password, self.domain)
        sg = api.Shotgun(auth_url, None, None, connect=False)
        expected = "Basic " + base64.encodestring(login_password).strip()
        self.assertEqual(expected, sg.config.authorization)

    def test_authorization(self):
        """Authorization passed to server"""
        login    = self.human_user['login']
        password = self.human_password
        login_password = "%s:%s" % (login, password)
        # login:password@domain
        auth_url = "%s%s@%s" % (self.uri_prefix, login_password, self.domain)

        self.sg = api.Shotgun(auth_url, "foo", "bar", connect=False)
        self._setup_mock()
        self._mock_http({ 'version': [2, 4, 0, u'Dev'] })

        self.sg.info()

        args, _ = self.sg._http_request.call_args
        verb, path, body, headers = args

        expected = "Basic " + base64.encodestring(login_password).strip()
        self.assertEqual(expected, headers.get("Authorization"))

    def test_connect_close(self):
        """Connection is closed and opened."""
        #The mock created an existing mock connection,
        self.sg.connect()
        self.assertEqual(0, self.mock_conn.request.call_count)
        self.sg.close()
        self.assertEqual(None, self.sg._connection)


    def test_network_retry(self):
        """Network failure is retried"""
        self.sg._http_request.side_effect = httplib2.HttpLib2Error

        self.assertRaises(httplib2.HttpLib2Error, self.sg.info)
        self.assertTrue(
            self.sg.config.max_rpc_attempts ==self.sg._http_request.call_count,
            "Call is repeated")

    def test_http_error(self):
        """HTTP error raised and not retried."""

        self._mock_http( "big old error string",
                       status=(500, "Internal Server Error"))

        self.assertRaises(api.ProtocolError, self.sg.info)
        self.assertEqual(1,
                        self.sg._http_request.call_count,
                        "Call is not repeated")

    def test_rpc_error(self):
        """RPC error transformed into Python error"""

        self._mock_http({ "message":"Go BANG",
                          "exception":True })

        self.assertRaises(api.Fault, self.sg.info)

        try:
            self.sg.info()
        except api.Fault, e:
            self.assertEqual("Go BANG", str(e))

    def test_call_rpc(self):
        """Named rpc method is called and results handled"""

        d = { "no-results" : "data without a results key" }
        self._mock_http(d)
        rv = self.sg._call_rpc("no-results", None)
        self._assert_http_method("no-results", None)
        expected = "rpc response without results key is returned as-is"
        self.assertEqual(d, rv, expected )

        d = { "results" : {"singleton" : "result"} }
        self._mock_http(d)
        rv = self.sg._call_rpc("singleton", None)
        self._assert_http_method("singleton", None)
        expected = "rpc response with singleton result"
        self.assertEqual(d["results"], rv, expected )

        d = { "results" : ["foo", "bar"] }
        a = {"some" : "args"}
        self._mock_http(d)
        rv = self.sg._call_rpc("list", a)
        self._assert_http_method("list", a)
        expected = "rpc response with list result"
        self.assertEqual(d["results"], rv, expected )

        d = { "results" : ["foo", "bar"] }
        a = {"some" : "args"}
        self._mock_http(d)
        rv = self.sg._call_rpc("list-first", a, first=True)
        self._assert_http_method("list-first", a)
        expected = "rpc response with list result, first item"
        self.assertEqual(d["results"][0], rv, expected )

        # Test unicode mixed with utf-8 as reported in Ticket #17959
        d = { "results" : ["foo", "bar"] }
        a = { "utf_str": "\xe2\x88\x9a", "unicode_str": "\xe2\x88\x9a".decode("utf-8") }
        self._mock_http(d)
        rv = self.sg._call_rpc("list", a)
        expected = "rpc response with list result"
        self.assertEqual(d["results"], rv, expected )



    def test_transform_data(self):
        """Outbound data is transformed"""
        timestamp = time.time()
        #microseconds will be last during transforms
        now = datetime.datetime.fromtimestamp(timestamp).replace(
            microsecond=0, tzinfo=SG_TIMEZONE.local)
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

    def test_decode_response_ascii(self):
        self._assert_decode_resonse(True, u"my data \u00E0".encode('utf8'))

    def test_decode_response_unicode(self):
        self._assert_decode_resonse(False, u"my data \u00E0")

    def _assert_decode_resonse(self, ensure_ascii, data):
        """HTTP Response is decoded as JSON or text"""

        headers = {
            "content-type" : "application/json;charset=utf-8"
        }
        d = {
            "this is " : data
        }
        sg = api.Shotgun(self.config.server_url,
                         self.config.script_name,
                         self.config.api_key,
                         http_proxy=self.config.http_proxy,
                         ensure_ascii = ensure_ascii,
                         connect=False)

        j = json.dumps(d, ensure_ascii=ensure_ascii, encoding="utf-8")
        self.assertEqual(d, sg._decode_response(headers, j))

        headers["content-type"] = "text/javascript"
        self.assertEqual(d, sg._decode_response(headers, j))

        headers["content-type"] = "text/foo"
        self.assertEqual(j, sg._decode_response(headers, j))


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

class TestShotgunClientInterface(base.MockTestBase):
    '''Tests expected interface for shotgun module and client'''
    def test_client_interface(self):
        expected_attributes = ['base_url',
                               'config',
                               'client_caps',
                               'server_caps']
        for expected_attribute in expected_attributes:
            if not hasattr(self.sg, expected_attribute):
                assert False, '%s not found on %s' % (expected_attribute,
                                                      self.sg)

    def test_module_interface(self):
        import shotgun_api3
        expected_contents = ['Shotgun', 'ShotgunError', 'Fault',
                             'ProtocolError', 'ResponseError', 'Error',
                             'sg_timezone', '__version__']
        for expected_content in expected_contents:
            if not hasattr(shotgun_api3, expected_content):
                assert False, '%s not found on module %s' % (expected_content,
                                                            shotgun_api3)


if __name__ == '__main__':
    unittest.main()
