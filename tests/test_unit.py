#! /opt/local/bin/python

# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import unittest
from .mock import patch
import shotgun_api3 as api
from shotgun_api3.shotgun import _is_mimetypes_broken
from shotgun_api3.lib.six.moves import range, urllib
from shotgun_api3.lib.httplib2 import Http, ssl_error_classes


class TestShotgunInit(unittest.TestCase):
    '''Test case for Shotgun.__init__'''
    def setUp(self):
        self.server_path = 'http://server_path'
        self.script_name = 'script_name'
        self.api_key = 'api_key'

    # Proxy Server Tests
    def test_http_proxy_server(self):
        proxy_server = "someserver.com"
        http_proxy = proxy_server
        sg = api.Shotgun(self.server_path,
                         self.script_name,
                         self.api_key,
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, 8080)
        proxy_server = "123.456.789.012"
        http_proxy = proxy_server
        sg = api.Shotgun(self.server_path,
                         self.script_name,
                         self.api_key,
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, 8080)

    def test_http_proxy_server_and_port(self):
        proxy_server = "someserver.com"
        proxy_port = 1234
        http_proxy = "%s:%d" % (proxy_server, proxy_port)
        sg = api.Shotgun(self.server_path,
                         self.script_name,
                         self.api_key,
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)
        proxy_server = "123.456.789.012"
        proxy_port = 1234
        http_proxy = "%s:%d" % (proxy_server, proxy_port)
        sg = api.Shotgun(self.server_path,
                         self.script_name,
                         self.api_key,
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)

    def test_http_proxy_server_and_port_with_authentication(self):
        proxy_server = "someserver.com"
        proxy_port = 1234
        proxy_user = "user"
        proxy_pass = "password"
        http_proxy = "%s:%s@%s:%d" % (proxy_user, proxy_pass, proxy_server,
                                      proxy_port)
        sg = api.Shotgun(self.server_path,
                         self.script_name,
                         self.api_key,
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)
        self.assertEqual(sg.config.proxy_user, proxy_user)
        self.assertEqual(sg.config.proxy_pass, proxy_pass)
        proxy_server = "123.456.789.012"
        proxy_port = 1234
        proxy_user = "user"
        proxy_pass = "password"
        http_proxy = "%s:%s@%s:%d" % (proxy_user, proxy_pass, proxy_server,
                                      proxy_port)
        sg = api.Shotgun(self.server_path,
                         self.script_name,
                         self.api_key,
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)
        self.assertEqual(sg.config.proxy_user, proxy_user)
        self.assertEqual(sg.config.proxy_pass, proxy_pass)

    def test_http_proxy_with_at_in_password(self):
        proxy_server = "someserver.com"
        proxy_port = 1234
        proxy_user = "user"
        proxy_pass = "p@ssword"
        http_proxy = "%s:%s@%s:%d" % (proxy_user, proxy_pass, proxy_server,
                                      proxy_port)
        sg = api.Shotgun(self.server_path,
                         self.script_name,
                         self.api_key,
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)
        self.assertEqual(sg.config.proxy_user, proxy_user)
        self.assertEqual(sg.config.proxy_pass, proxy_pass)

    def test_malformatted_proxy_info(self):
        conn_info = {
            'base_url': self.server_path,
            'script_name': self.script_name,
            'api_key': self.api_key,
            'connect': False,
        }
        conn_info['http_proxy'] = 'http://someserver.com'
        self.assertRaises(ValueError, api.Shotgun, **conn_info)
        conn_info['http_proxy'] = 'user@someserver.com'
        self.assertRaises(ValueError, api.Shotgun, **conn_info)
        conn_info['http_proxy'] = 'someserver.com:1234:5678'
        self.assertRaises(ValueError, api.Shotgun, **conn_info)


class TestShotgunSummarize(unittest.TestCase):
    '''Test case for _create_summary_request function and parameter
    validation as it exists in Shotgun.summarize.

    Does not require database connection or test data.'''
    def setUp(self):
        self.sg = api.Shotgun('http://server_path',
                              'script_name',
                              'api_key',
                              connect=False)

    def test_filter_operator_none(self):
        expected_logical_operator = 'and'
        filter_operator = None
        self._assert_filter_operator(expected_logical_operator, filter_operator)

    def _assert_filter_operator(self, expected_logical_operator, filter_operator):
        result = self.get_call_rpc_params(None, {'filter_operator': filter_operator})
        actual_logical_operator = result['filters']['logical_operator']
        self.assertEqual(expected_logical_operator, actual_logical_operator)

    def test_filter_operator_all(self):
        expected_logical_operator = 'and'
        filter_operator = 'all'
        self._assert_filter_operator(expected_logical_operator, filter_operator)

    def test_filter_operator_or(self):
        expected_logical_operator = 'or'
        filter_operator = 'or'
        self._assert_filter_operator(expected_logical_operator, filter_operator)

    def test_filters(self):
        path = 'path'
        relation = 'relation'
        value = 'value'
        expected_condition = {'path': path, 'relation': relation, 'values': [value]}
        args = ['', [[path, relation, value]], None]
        result = self.get_call_rpc_params(args, {})
        actual_condition = result['filters']['conditions'][0]
        self.assertEqual(expected_condition, actual_condition)

    @patch('shotgun_api3.Shotgun._call_rpc')
    def get_call_rpc_params(self, args, kws, call_rpc):
        '''Return params sent to _call_rpc from summarize.'''
        if not args:
            args = [None, [], None]
        self.sg.summarize(*args, **kws)
        return call_rpc.call_args[0][1]

    def test_grouping(self):
        result = self.get_call_rpc_params(None, {})
        self.assertFalse('grouping' in result)
        grouping = ['something']
        kws = {'grouping': grouping}
        result = self.get_call_rpc_params(None, kws)
        self.assertEqual(grouping, result['grouping'])

    def test_grouping_type(self):
        '''test_grouping_type tests that grouping parameter is a list or None'''
        self.assertRaises(ValueError, self.sg.summarize, '', [], [], grouping='Not a list')


class TestShotgunBatch(unittest.TestCase):
    def setUp(self):
        self.sg = api.Shotgun('http://server_path',
                              'script_name',
                              'api_key',
                              connect=False)

    def test_missing_required_key(self):
        req = {}
        # requires keys request_type and entity_type
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        req['entity_type'] = 'Entity'
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        req['request_type'] = 'not_real_type'
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        # create requires data key
        req['request_type'] = 'create'
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        # update requires entity_id and data
        req['request_type'] = 'update'
        req['data'] = {}
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        del req['data']
        req['entity_id'] = 2334
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        # delete requires entity_id
        req['request_type'] = 'delete'
        del req['entity_id']
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])


class TestServerCapabilities(unittest.TestCase):
    def test_no_server_version(self):
        self.assertRaises(api.ShotgunError, api.shotgun.ServerCapabilities, 'host', {})

    def test_bad_version(self):
        '''test_bad_meta tests passing bad meta data type'''
        self.assertRaises(api.ShotgunError, api.shotgun.ServerCapabilities, 'host', {'version': (0, 0, 0)})

    def test_dev_version(self):
        serverCapabilities = api.shotgun.ServerCapabilities('host', {'version': (3, 4, 0, 'Dev')})
        self.assertEqual(serverCapabilities.version, (3, 4, 0))
        self.assertTrue(serverCapabilities.is_dev)

        serverCapabilities = api.shotgun.ServerCapabilities('host', {'version': (2, 4, 0)})
        self.assertEqual(serverCapabilities.version, (2, 4, 0))
        self.assertFalse(serverCapabilities.is_dev)


class TestClientCapabilities(unittest.TestCase):

    def test_darwin(self):
        self.assert_platform('Darwin', 'mac')

    def test_windows(self):
        self.assert_platform('win32', 'windows')

    def test_linux(self):
        self.assert_platform('Linux', 'linux')

    def assert_platform(self, sys_ret_val, expected):
        platform = api.shotgun.sys.platform
        try:
            api.shotgun.sys.platform = sys_ret_val
            expected_local_path_field = "local_path_%s" % expected

            client_caps = api.shotgun.ClientCapabilities()
            self.assertEqual(client_caps.platform, expected)
            self.assertEqual(client_caps.local_path_field, expected_local_path_field)
        finally:
            api.shotgun.sys.platform = platform

    def test_no_platform(self):
        platform = api.shotgun.sys.platform
        try:
            api.shotgun.sys.platform = "unsupported"
            client_caps = api.shotgun.ClientCapabilities()
            self.assertEqual(client_caps.platform, None)
            self.assertEqual(client_caps.local_path_field, None)
        finally:
            api.shotgun.sys.platform = platform

    @patch('shotgun_api3.shotgun.sys')
    def test_py_version(self, mock_sys):
        major = 2
        minor = 7
        micro = 3
        mock_sys.version_info = (major, minor, micro, 'final', 0)
        expected_py_version = "%s.%s" % (major, minor)
        client_caps = api.shotgun.ClientCapabilities()
        self.assertEqual(client_caps.py_version, expected_py_version)


class TestFilters(unittest.TestCase):
    def test_empty(self):
        expected = {
            "logical_operator": "and",
            "conditions": []
        }

        result = api.shotgun._translate_filters([], None)
        self.assertEqual(result, expected)

    def test_simple(self):
        filters = [
            ["code", "is", "test"],
            ["sg_status_list", "is", "ip"]
        ]

        expected = {
            "logical_operator": "or",
            "conditions": [
                {"path": "code", "relation": "is", "values": ["test"]},
                {"path": "sg_status_list", "relation": "is", "values": ["ip"]}
            ]
        }

        result = api.shotgun._translate_filters(filters, "any")
        self.assertEqual(result, expected)

    # Test both styles of passing arrays
    def test_arrays(self):
        expected = {
            "logical_operator": "and",
            "conditions": [
                {"path": "code", "relation": "in", "values": ["test1", "test2", "test3"]}
            ]
        }

        filters = [
            ["code", "in", "test1", "test2", "test3"]
        ]

        result = api.shotgun._translate_filters(filters, "all")
        self.assertEqual(result, expected)

        filters = [
            ["code", "in", ["test1", "test2", "test3"]]
        ]

        result = api.shotgun._translate_filters(filters, "all")
        self.assertEqual(result, expected)

    def test_nested(self):
        filters = [
            ["code", "in", "test"],
            {
                "filter_operator": "any",
                "filters": [
                    ["sg_status_list", "is", "ip"],
                    ["sg_status_list", "is", "fin"],
                    {
                        "filter_operator": "all",
                        "filters": [
                            ["sg_status_list", "is", "hld"],
                            ["assets", "is", {"type": "Asset", "id": 9}]
                        ]
                    }
                ]
            }
        ]

        expected = {
            "logical_operator": "and",
            "conditions": [
                {"path": "code", "relation": "in", "values": ["test"]},
                {
                    "logical_operator": "or",
                    "conditions": [
                        {"path": "sg_status_list", "relation": "is", "values": ["ip"]},
                        {"path": "sg_status_list", "relation": "is", "values": ["fin"]},
                        {
                            "logical_operator": "and",
                            "conditions": [
                                {"path": "sg_status_list", "relation": "is", "values": ["hld"]},
                                {"path": "assets", "relation": "is", "values": [{"type": "Asset", "id": 9}]},
                            ]
                        }
                    ]
                }
            ]
        }

        result = api.shotgun._translate_filters(filters, "all")
        self.assertEqual(result, expected)

    def test_invalid(self):
        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, [], "bogus")
        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, ["bogus"], "all")

        filters = [{
            "filter_operator": "bogus",
            "filters": []
        }]

        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, filters, "all")

        filters = [{
            "filters": []
        }]

        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, filters, "all")

        filters = [{
            "filter_operator": "all",
            "filters": {"bogus": "bogus"}
        }]

        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, filters, "all")


class TestCerts(unittest.TestCase):
    # A dummy bad url provided by Amazon
    bad_url = "https://untrusted-root.badssl.com/"
    # A list of Amazon cert URLS, taken from here:
    # https://aws.amazon.com/blogs/security/how-to-prepare-for-aws-move-to-its-own-certificate-authority/
    test_urls = [
        "https://good.sca1a.amazontrust.com",
        "https://good.sca2a.amazontrust.com",
        "https://good.sca3a.amazontrust.com",
        "https://good.sca4a.amazontrust.com",
        "https://good.sca0a.amazontrust.com",
    ]

    def setUp(self):
        self.sg = api.Shotgun('http://server_path',
                              'script_name',
                              'api_key',
                              connect=False)

        # Get the location of the certs file
        self.certs = self.sg._get_certs_file(None)

    def _check_url_with_sg_api_httplib2(self, url, certs):
        """
        Given a url and the certs file, it will do a simple
        request and return the result.
        """
        http = Http(ca_certs=certs)
        return http.request(url)

    def _check_url_with_urllib(self, url):
        """
        Given a url it will perform a simple request and return a result.
        """
        # create a request using the opener generated by the SG API.
        # The `_build_opener` method internally should use the correct certs.
        opener = self.sg._build_opener(urllib.request.HTTPHandler)
        request = urllib.request.Request(url)
        return opener.open(request)

    def test_found_correct_cert(self):
        """
        Checks that the cert file the API is finding,
        (when a cert path isn't passed and the SHOTGUN_API_CACERTS
        isn't set), is the one bundled with this API
        """
        # Get the path to the cert file we expect the Shotgun API to find
        cert_path = os.path.normpath(
            # Get the path relative to where we picked up the API and not relative
            # to file on disk. On CI we pip install the API to run the tests
            # so we have to pick the location from the installed copy.
            # Call dirname to remove from __init__.py
            os.path.join(os.path.dirname(api.__file__), "lib", "certifi", "cacert.pem")
        )
        # Now ensure that the path the SG API has found is correct.
        self.assertEqual(cert_path, self.certs)
        self.assertTrue(os.path.isfile(self.certs))

    def test_httplib(self):
        """
        Checks that we can access the amazon urls using our bundled
        certificate with httplib.
        """
        # First check that we get an error when trying to connect to a known dummy bad URL
        self.assertRaises(ssl_error_classes, self._check_url_with_sg_api_httplib2, self.bad_url, self.certs)

        # Now check that the good urls connect properly using the certs
        for url in self.test_urls:
            response, message = self._check_url_with_sg_api_httplib2(url, self.certs)
            self.assertEqual(response["status"], "200")

    def test_urlib(self):
        """
        Checks that we can access the amazon urls using our bundled
        certificate with urllib.
        """
        # First check that we get an error when trying to connect to a known dummy bad URL
        self.assertRaises(urllib.error.URLError, self._check_url_with_urllib, self.bad_url)

        # Now check that the good urls connect properly using the certs
        for url in self.test_urls:
            response = self._check_url_with_urllib(url)
            assert (response is not None)


class TestMimetypesFix(unittest.TestCase):
    """
    Makes sure that the mimetypes fix will be imported.
    """

    @patch('shotgun_api3.shotgun.sys')
    def _test_mimetypes_import(self, platform, major, minor, patch_number, result, mock):
        """
        Mocks sys.platform and sys.version_info to test the mimetypes import code.
        """

        mock.version_info = [major, minor, patch_number]
        mock.platform = platform
        self.assertEqual(_is_mimetypes_broken(), result)

if __name__ == '__main__':
    unittest.main()
