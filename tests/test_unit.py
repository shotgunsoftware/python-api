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
import socket
import ssl
import unittest
from unittest import mock
import urllib.request
import urllib.error

import shotgun_api3 as api
from shotgun_api3 import shotgun
from shotgun_api3.lib.httplib2 import Http


class TestShotgunInit(unittest.TestCase):
    """Test case for Shotgun.__init__"""

    def setUp(self):
        self.server_path = "http://server_path"
        self.script_name = "script_name"
        self.api_key = "api_key"

    # Proxy Server Tests
    def test_http_proxy_server(self):
        proxy_server = "someserver.com"
        http_proxy = proxy_server
        sg = api.Shotgun(
            self.server_path,
            self.script_name,
            self.api_key,
            http_proxy=http_proxy,
            connect=False,
        )
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, 8080)
        proxy_server = "123.456.789.012"
        http_proxy = proxy_server
        sg = api.Shotgun(
            self.server_path,
            self.script_name,
            self.api_key,
            http_proxy=http_proxy,
            connect=False,
        )
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, 8080)

    def test_http_proxy_server_and_port(self):
        proxy_server = "someserver.com"
        proxy_port = 1234
        http_proxy = "%s:%d" % (proxy_server, proxy_port)
        sg = api.Shotgun(
            self.server_path,
            self.script_name,
            self.api_key,
            http_proxy=http_proxy,
            connect=False,
        )
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)
        proxy_server = "123.456.789.012"
        proxy_port = 1234
        http_proxy = "%s:%d" % (proxy_server, proxy_port)
        sg = api.Shotgun(
            self.server_path,
            self.script_name,
            self.api_key,
            http_proxy=http_proxy,
            connect=False,
        )
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)

    def test_http_proxy_server_and_port_with_authentication(self):
        proxy_server = "someserver.com"
        proxy_port = 1234
        proxy_user = "user"
        proxy_pass = "password"
        http_proxy = "%s:%s@%s:%d" % (proxy_user, proxy_pass, proxy_server, proxy_port)
        sg = api.Shotgun(
            self.server_path,
            self.script_name,
            self.api_key,
            http_proxy=http_proxy,
            connect=False,
        )
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)
        self.assertEqual(sg.config.proxy_user, proxy_user)
        self.assertEqual(sg.config.proxy_pass, proxy_pass)
        proxy_server = "123.456.789.012"
        proxy_port = 1234
        proxy_user = "user"
        proxy_pass = "password"
        http_proxy = "%s:%s@%s:%d" % (proxy_user, proxy_pass, proxy_server, proxy_port)
        sg = api.Shotgun(
            self.server_path,
            self.script_name,
            self.api_key,
            http_proxy=http_proxy,
            connect=False,
        )
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)
        self.assertEqual(sg.config.proxy_user, proxy_user)
        self.assertEqual(sg.config.proxy_pass, proxy_pass)

    def test_http_proxy_with_at_in_password(self):
        proxy_server = "someserver.com"
        proxy_port = 1234
        proxy_user = "user"
        proxy_pass = "p@ssword"
        http_proxy = "%s:%s@%s:%d" % (proxy_user, proxy_pass, proxy_server, proxy_port)
        sg = api.Shotgun(
            self.server_path,
            self.script_name,
            self.api_key,
            http_proxy=http_proxy,
            connect=False,
        )
        self.assertEqual(sg.config.proxy_server, proxy_server)
        self.assertEqual(sg.config.proxy_port, proxy_port)
        self.assertEqual(sg.config.proxy_user, proxy_user)
        self.assertEqual(sg.config.proxy_pass, proxy_pass)

    def test_malformatted_proxy_info(self):
        conn_info = {
            "base_url": self.server_path,
            "script_name": self.script_name,
            "api_key": self.api_key,
            "connect": False,
        }
        conn_info["http_proxy"] = "http://someserver.com"
        self.assertRaises(ValueError, api.Shotgun, **conn_info)
        conn_info["http_proxy"] = "user@someserver.com"
        self.assertRaises(ValueError, api.Shotgun, **conn_info)
        conn_info["http_proxy"] = "someserver.com:1234:5678"
        self.assertRaises(ValueError, api.Shotgun, **conn_info)


class TestShotgunSummarize(unittest.TestCase):
    """Test case for _create_summary_request function and parameter
    validation as it exists in Shotgun.summarize.

    Does not require database connection or test data."""

    def setUp(self):
        self.sg = api.Shotgun(
            "http://server_path", "script_name", "api_key", connect=False
        )

    def test_filter_operator_none(self):
        expected_logical_operator = "and"
        filter_operator = None
        self._assert_filter_operator(expected_logical_operator, filter_operator)

    def _assert_filter_operator(self, expected_logical_operator, filter_operator):
        result = self.get_call_rpc_params(None, {"filter_operator": filter_operator})
        actual_logical_operator = result["filters"]["logical_operator"]
        self.assertEqual(expected_logical_operator, actual_logical_operator)

    def test_filter_operator_all(self):
        expected_logical_operator = "and"
        filter_operator = "all"
        self._assert_filter_operator(expected_logical_operator, filter_operator)

    def test_filter_operator_or(self):
        expected_logical_operator = "or"
        filter_operator = "or"
        self._assert_filter_operator(expected_logical_operator, filter_operator)

    def test_filters(self):
        path = "path"
        relation = "relation"
        value = "value"
        expected_condition = {"path": path, "relation": relation, "values": [value]}
        args = ["", [[path, relation, value]], None]
        result = self.get_call_rpc_params(args, {})
        actual_condition = result["filters"]["conditions"][0]
        self.assertEqual(expected_condition, actual_condition)

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def get_call_rpc_params(self, args, kws, call_rpc):
        """Return params sent to _call_rpc from summarize."""
        if not args:
            args = [None, [], None]
        self.sg.summarize(*args, **kws)
        return call_rpc.call_args[0][1]

    def test_grouping(self):
        result = self.get_call_rpc_params(None, {})
        self.assertFalse("grouping" in result)
        grouping = ["something"]
        kws = {"grouping": grouping}
        result = self.get_call_rpc_params(None, kws)
        self.assertEqual(grouping, result["grouping"])

    def test_grouping_type(self):
        """test_grouping_type tests that grouping parameter is a list or None"""
        self.assertRaises(
            ValueError, self.sg.summarize, "", [], [], grouping="Not a list"
        )


class TestShotgunBatch(unittest.TestCase):
    def setUp(self):
        self.sg = api.Shotgun(
            "http://server_path", "script_name", "api_key", connect=False
        )

    def test_missing_required_key(self):
        req = {}
        # requires keys request_type and entity_type
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        req["entity_type"] = "Entity"
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        req["request_type"] = "not_real_type"
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        # create requires data key
        req["request_type"] = "create"
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        # update requires entity_id and data
        req["request_type"] = "update"
        req["data"] = {}
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        del req["data"]
        req["entity_id"] = 2334
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        # delete requires entity_id
        req["request_type"] = "delete"
        del req["entity_id"]
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])


class TestServerCapabilities(unittest.TestCase):
    def test_no_server_version(self):
        self.assertRaises(api.ShotgunError, api.shotgun.ServerCapabilities, "host", {})

    def test_bad_version(self):
        """test_bad_meta tests passing bad meta data type"""
        self.assertRaises(
            api.ShotgunError,
            api.shotgun.ServerCapabilities,
            "host",
            {"version": (0, 0, 0)},
        )

    def test_dev_version(self):
        serverCapabilities = api.shotgun.ServerCapabilities(
            "host", {"version": (3, 4, 0, "Dev")}
        )
        self.assertEqual(serverCapabilities.version, (3, 4, 0))
        self.assertTrue(serverCapabilities.is_dev)

        serverCapabilities = api.shotgun.ServerCapabilities(
            "host", {"version": (2, 4, 0)}
        )
        self.assertEqual(serverCapabilities.version, (2, 4, 0))
        self.assertFalse(serverCapabilities.is_dev)


class TestClientCapabilities(unittest.TestCase):

    def test_darwin(self):
        self.assert_platform("Darwin", "mac")

    def test_windows(self):
        self.assert_platform("win32", "windows")

    def test_linux(self):
        self.assert_platform("Linux", "linux")

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

    @mock.patch("shotgun_api3.shotgun.sys")
    def test_py_version(self, mock_sys):
        major = 2
        minor = 7
        micro = 3
        mock_sys.version_info = (major, minor, micro, "final", 0)
        expected_py_version = "%s.%s" % (major, minor)
        client_caps = api.shotgun.ClientCapabilities()
        self.assertEqual(client_caps.py_version, expected_py_version)


class TestFilters(unittest.TestCase):
    maxDiff = None

    def test_empty(self):
        expected = {"logical_operator": "and", "conditions": []}

        result = api.shotgun._translate_filters([], None)
        self.assertEqual(result, expected)

    def test_simple(self):
        filters = [["code", "is", "test"], ["sg_status_list", "is", "ip"]]

        expected = {
            "logical_operator": "or",
            "conditions": [
                {"path": "code", "relation": "is", "values": ["test"]},
                {"path": "sg_status_list", "relation": "is", "values": ["ip"]},
            ],
        }

        result = api.shotgun._translate_filters(filters, "any")
        self.assertEqual(result, expected)

    # Test both styles of passing arrays
    def test_arrays(self):
        expected = {
            "logical_operator": "and",
            "conditions": [
                {
                    "path": "code",
                    "relation": "in",
                    "values": ["test1", "test2", "test3"],
                }
            ],
        }

        filters = [["code", "in", "test1", "test2", "test3"]]

        result = api.shotgun._translate_filters(filters, "all")
        self.assertEqual(result, expected)

        filters = [["code", "in", ["test1", "test2", "test3"]]]

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
                            ["assets", "is", {"type": "Asset", "id": 9}],
                        ],
                    },
                ],
            },
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
                                {
                                    "path": "sg_status_list",
                                    "relation": "is",
                                    "values": ["hld"],
                                },
                                {
                                    "path": "assets",
                                    "relation": "is",
                                    "values": [{"type": "Asset", "id": 9}],
                                },
                            ],
                        },
                    ],
                },
            ],
        }

        result = api.shotgun._translate_filters(filters, "all")
        self.assertEqual(result, expected)

    def test_invalid(self):
        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, [], "bogus")
        self.assertRaises(
            api.ShotgunError, api.shotgun._translate_filters, ["bogus"], "all"
        )

        filters = [{"filter_operator": "bogus", "filters": []}]

        self.assertRaises(
            api.ShotgunError, api.shotgun._translate_filters, filters, "all"
        )

        filters = [{"filters": []}]

        self.assertRaises(
            api.ShotgunError, api.shotgun._translate_filters, filters, "all"
        )

        filters = [{"filter_operator": "all", "filters": {"bogus": "bogus"}}]

        self.assertRaises(
            api.ShotgunError, api.shotgun._translate_filters, filters, "all"
        )

    @mock.patch.dict(os.environ, {"SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION": "1"})
    def test_related_object(self):
        filters = [
            [
                "project",
                "is",
                {
                    "foo": "foo",
                    "bar": "bar",
                    "id": 999,
                    "baz": "baz",
                    "type": "Anything",
                },
            ],
        ]
        expected = {
            "logical_operator": "and",
            "conditions": [
                {
                    "path": "project",
                    "relation": "is",
                    "values": [
                        {
                            "foo": "foo",
                            "bar": "bar",
                            "baz": "baz",
                            "id": 999,
                            "type": "Anything",
                        }
                    ],
                }
            ],
        }
        api.Shotgun("http://server_path", "script_name", "api_key", connect=False)
        result = api.shotgun._translate_filters(filters, "all")
        self.assertEqual(result, expected)

    @mock.patch("shotgun_api3.shotgun.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION", False)
    def test_related_object_entity_optimization_is(self):
        filters = [
            [
                "project",
                "is",
                {
                    "foo": "foo",
                    "bar": "bar",
                    "id": 999,
                    "baz": "baz",
                    "type": "Anything",
                },
            ],
        ]
        expected = {
            "logical_operator": "and",
            "conditions": [
                {
                    "path": "project",
                    "relation": "is",
                    "values": [
                        {
                            "id": 999,
                            "type": "Anything",
                        }
                    ],
                }
            ],
        }
        api.Shotgun("http://server_path", "script_name", "api_key", connect=False)
        result = api.shotgun._translate_filters(filters, "all")
        self.assertEqual(result, expected)

        # Now test a non-related object. The expected result should not be optimized.
        filters = [
            [
                "something",
                "is",
                {"foo": "foo", "bar": "bar"},
            ],
        ]
        expected = {
            "logical_operator": "and",
            "conditions": [
                {
                    "path": "something",
                    "relation": "is",
                    "values": [{"bar": "bar", "foo": "foo"}],
                }
            ],
        }
        api.Shotgun("http://server_path", "script_name", "api_key", connect=False)
        result = api.shotgun._translate_filters(filters, "all")
        self.assertEqual(result, expected)

    @mock.patch("shotgun_api3.shotgun.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION", False)
    def test_related_object_entity_optimization_in(self):
        filters = [
            [
                "project",
                "in",
                [
                    {
                        "foo1": "foo1",
                        "bar1": "bar1",
                        "id": 999,
                        "baz1": "baz1",
                        "type": "Anything",
                    },
                    {
                        "foo2": "foo2",
                        "bar2": "bar2",
                        "id": 998,
                        "baz2": "baz2",
                        "type": "Anything",
                    },
                    {"foo3": "foo3", "bar3": "bar3"},
                ],
            ],
        ]
        expected = {
            "logical_operator": "and",
            "conditions": [
                {
                    "path": "project",
                    "relation": "in",
                    "values": [
                        {
                            "id": 999,
                            "type": "Anything",
                        },
                        {
                            "id": 998,
                            "type": "Anything",
                        },
                        {
                            "foo3": "foo3",
                            "bar3": "bar3",
                        },
                    ],
                }
            ],
        }
        api.Shotgun("http://server_path", "script_name", "api_key", connect=False)
        result = api.shotgun._translate_filters(filters, "all")
        self.assertEqual(result, expected)

    def test_related_object_update_entity(self):
        entity_type = "Anything"
        entity_id = 999
        multi_entity_update_modes = {"link": "set", "name": "set"}
        data = {
            "name": "test",
            "link": {
                "name": "test",
                "url": "http://test.com",
            },
        }
        expected = {
            "id": 999,
            "type": "Anything",
            "fields": [
                {
                    "field_name": "name",
                    "value": "test",
                    "multi_entity_update_mode": "set",
                },
                {
                    "field_name": "link",
                    "value": {
                        "name": "test",
                        "url": "http://test.com",
                    },
                    "multi_entity_update_mode": "set",
                },
            ],
        }
        sg = api.Shotgun("http://server_path", "script_name", "api_key", connect=False)
        result = sg._translate_update_params(
            entity_type, entity_id, data, multi_entity_update_modes
        )
        self.assertEqual(result, expected)

    @mock.patch("shotgun_api3.shotgun.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION", False)
    def test_related_object_update_optimization_entity(self):
        entity_type = "Anything"
        entity_id = 999
        multi_entity_update_modes = {"project": "set", "link": "set", "name": "set"}
        data = {
            "name": "test",
            "link": {
                "name": "test",
                "url": "http://test.com",
            },
            "project": {
                "foo1": "foo1",
                "bar1": "bar1",
                "id": 888,
                "baz1": "baz1",
                "type": "Project",
            },
        }
        expected = {
            "id": 999,
            "type": "Anything",
            "fields": [
                {
                    "field_name": "name",
                    "value": "test",
                    "multi_entity_update_mode": "set",
                },
                {
                    "field_name": "link",
                    "value": {
                        "name": "test",
                        "url": "http://test.com",
                    },
                    "multi_entity_update_mode": "set",
                },
                {
                    "field_name": "project",
                    "multi_entity_update_mode": "set",
                    "value": {
                        # Entity is optimized with type/id fields.
                        "id": 888,
                        "type": "Project",
                    },
                },
            ],
        }
        sg = api.Shotgun("http://server_path", "script_name", "api_key", connect=False)
        result = sg._translate_update_params(
            entity_type, entity_id, data, multi_entity_update_modes
        )
        self.assertEqual(result, expected)

    @mock.patch("shotgun_api3.shotgun.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION", False)
    def test_related_object_update_optimization_entity_multi(self):
        entity_type = "Asset"
        entity_id = 6626
        data = {
            "sg_status_list": "ip",
            "project": {"id": 70, "type": "Project", "name": "important name 70"},
            "sg_vvv": [
                {"id": 6440, "type": "Asset"},
                {"id": 6441, "type": "Asset", "custom_name": "disposable name 6441"},
                {
                    # To be kept
                    "id": 6442,
                    "type": "Asset",
                    "url": "http://test.com/asset/6442",
                    # to be removed
                    "custom_name": "disposable name 1",
                    "custom_name2": "disposable name 2",
                    "custom_name3": "disposable name 3",
                    "custom_name4": "disposable name 4",
                },
                {
                    "sg_nested": {
                        "level1": {
                            "level2": {"id": 123, "type": "Entity", "foo": "bar"}
                        }
                    }
                },
            ],
            "sg_class": {
                # To be kept
                "id": 1,
                "type": "CustomEntity53",
                "url": "http://test.com",
                "name": "important class name",
                "local_path": "/some/local/path",
                # to be removed
                "custom_name": "disposable name 1",
                "custom_name2": "disposable name 2",
                "custom_name3": "disposable name 3",
                "custom_name4": "disposable name 4",
            },
        }
        expected = {
            "type": "Asset",
            "id": 6626,
            "fields": [
                {"field_name": "sg_status_list", "value": "ip"},
                {
                    "field_name": "project",
                    "value": {
                        "type": "Project",
                        "id": 70,
                        "name": "important name 70",
                    },
                },
                {
                    "field_name": "sg_vvv",
                    "value": [
                        {"id": 6440, "type": "Asset"},
                        {"id": 6441, "type": "Asset"},
                        {
                            "id": 6442,
                            "type": "Asset",
                            "url": "http://test.com/asset/6442",
                        },
                        {
                            "sg_nested": {
                                "level1": {
                                    "level2": {
                                        "id": 123,
                                        "type": "Entity",
                                        "foo": "bar",
                                    }
                                }
                            }
                        },
                    ],
                },
                {
                    "field_name": "sg_class",
                    "value": {
                        "type": "CustomEntity53",
                        "id": 1,
                        "name": "important class name",
                        "url": "http://test.com",
                        "local_path": "/some/local/path",
                    },
                },
            ],
        }
        sg = api.Shotgun("http://server_path", "script_name", "api_key", connect=False)
        result = sg._translate_update_params(entity_type, entity_id, data, None)
        self.assertEqual(result, expected)


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
        self.sg = api.Shotgun(
            "http://server_path", "script_name", "api_key", connect=False
        )

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
        # create a request using the opener generated by the PTR API.
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
        # Now ensure that the path the PTR API has found is correct.
        self.assertEqual(cert_path, self.certs)
        self.assertTrue(os.path.isfile(self.certs))

    def test_httplib(self):
        """
        Checks that we can access the amazon urls using our bundled
        certificate with httplib.
        """
        # First check that we get an error when trying to connect to a known dummy bad URL
        self.assertRaises(
            (ssl.SSLError, ssl.CertificateError),
            self._check_url_with_sg_api_httplib2,
            self.bad_url,
            self.certs,
        )

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
        self.assertRaises(
            urllib.error.URLError, self._check_url_with_urllib, self.bad_url
        )

        # Now check that the good urls connect properly using the certs
        for url in self.test_urls:
            response = self._check_url_with_urllib(url)
            assert response is not None


class _FakeClock(object):
    """Controllable stand-in for time.monotonic."""

    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestConnectionIdleExpiry(unittest.TestCase):
    """
    Test that connections idle for longer than config.max_connection_idle_secs
    are closed and recreated instead of reused (SG-44724).

    A NAT or load balancer can silently drop an idle keep-alive session, and
    reusing that socket blocks until the socket timeout expires. None of these
    tests make network requests.
    """

    def setUp(self):
        self.sg = api.Shotgun(
            "http://server_path", "script_name", "api_key", connect=False
        )
        self.clock = _FakeClock()
        self.created_connections = []

        clock_patcher = mock.patch(
            "shotgun_api3.shotgun.time.monotonic", side_effect=self.clock
        )
        clock_patcher.start()
        self.addCleanup(clock_patcher.stop)

        http_patcher = mock.patch(
            "shotgun_api3.shotgun.Http", side_effect=self._make_connection
        )
        http_patcher.start()
        self.addCleanup(http_patcher.stop)

    def _make_connection(self, *args, **kwargs):
        """Build a fake Http whose request() returns a minimal 200 response."""
        conn = mock.MagicMock()
        conn.connections = {"http:server_path": mock.MagicMock()}
        conn.init_kwargs = kwargs
        response = mock.MagicMock()
        response.status = 200
        response.reason = "OK"
        response.items.return_value = [("content-type", "application/json")]
        conn.request.return_value = (response, "{}")
        self.created_connections.append(conn)
        return conn

    def _request(self):
        return self.sg._http_request("GET", "/path", None, {})

    def test_stale_connection_is_replaced(self):
        """A connection idle beyond the limit is closed and recreated."""
        self._request()
        first = self.sg._get_connection()

        self.clock.advance(self.sg.config.max_connection_idle_secs + 1)
        self._request()
        second = self.sg._get_connection()

        self.assertIsNot(first, second)
        self.assertEqual(len(self.created_connections), 2)
        # The stale connection's socket must actually be closed, not just
        # dropped from the cache.
        self.assertEqual(first.connections, {})

    def test_fresh_connection_is_reused(self):
        """A connection used recently is reused as before."""
        self._request()
        first = self.sg._get_connection()

        self.clock.advance(self.sg.config.max_connection_idle_secs - 1)
        self._request()
        second = self.sg._get_connection()

        self.assertIs(first, second)
        self.assertEqual(len(self.created_connections), 1)

    def test_expiry_is_measured_from_last_use_not_creation(self):
        """Steady traffic keeps a connection alive indefinitely."""
        self._request()
        first = self.sg._get_connection()

        for _ in range(5):
            self.clock.advance(self.sg.config.max_connection_idle_secs - 1)
            self._request()

        self.assertIs(first, self.sg._get_connection())
        self.assertEqual(len(self.created_connections), 1)

    def test_unused_connection_is_not_expired(self):
        """A connection created but never used has no idle time to expire."""
        first = self.sg._get_connection()
        self.clock.advance(self.sg.config.max_connection_idle_secs + 1)

        self.assertIs(first, self.sg._get_connection())
        self.assertEqual(len(self.created_connections), 1)

    def test_failed_request_does_not_refresh_idle_clock(self):
        """
        A request that raised is no evidence the socket is alive, so it must not
        reset the idle clock.
        """
        self._request()
        first = self.sg._get_connection()
        first.request.side_effect = Exception("boom")

        self.clock.advance(self.sg.config.max_connection_idle_secs - 1)
        with self.assertRaises(Exception):
            self._request()

        # Only 1 second of headroom remains; without the failed attempt
        # refreshing the clock, 2 more seconds must expire the connection.
        self.clock.advance(2)
        self.assertIsNot(first, self.sg._get_connection())

    def test_expiry_can_be_disabled(self):
        """None and 0 both mean 'reuse regardless of idle time'."""
        for disabled_value in (None, 0):
            self.sg._close_connection()
            self.created_connections = []
            self.sg.config.max_connection_idle_secs = disabled_value

            self._request()
            first = self.sg._get_connection()
            self.clock.advance(3600)

            self.assertIs(first, self.sg._get_connection())
            self.assertEqual(len(self.created_connections), 1)

    def test_expiry_preserves_proxy_configuration(self):
        """The replacement connection is built with the same proxy settings."""
        self.sg.config.proxy_server = "proxy.example.com"
        self.sg.config.proxy_port = 8080

        self._request()
        first = self.sg._get_connection()
        self.clock.advance(self.sg.config.max_connection_idle_secs + 1)
        self._request()
        second = self.sg._get_connection()

        self.assertIsNot(first, second)
        self.assertIsNotNone(second.init_kwargs["proxy_info"])
        self.assertEqual(
            second.init_kwargs["proxy_info"].proxy_host, "proxy.example.com"
        )


class TestSocketKeepalive(unittest.TestCase):
    """
    Test that sockets get TCP keepalive enabled once connected (SG-44724).

    Keepalive lets the kernel notice a peer that vanished without FIN or RST.
    These tests assert only that the options are attempted, since which timers
    are adjustable and whether the OS accepts them is platform dependent. No
    network requests are made.
    """

    # Stand-in for the Windows-only socket.SIO_KEEPALIVE_VALS constant.
    SIO_SENTINEL = 2550136836

    def _keepalive_calls(self, sock):
        return [
            call
            for call in sock.setsockopt.call_args_list
            if call[0][:2] == (socket.SOL_SOCKET, socket.SO_KEEPALIVE)
        ]

    def _tcp_option_calls(self, sock):
        return [
            call
            for call in sock.setsockopt.call_args_list
            if call[0][0] == socket.IPPROTO_TCP
        ]

    def _addrinfo(self, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

    def test_keepalive_enabled_on_socket(self):
        sock = mock.MagicMock()
        shotgun._set_socket_keepalive(sock)

        self.assertEqual(len(self._keepalive_calls(sock)), 1)
        self.assertEqual(self._keepalive_calls(sock)[0][0][2], 1)

    def test_unsupported_options_are_ignored(self):
        """A socket that refuses keepalive outright must not raise."""
        sock = mock.MagicMock()
        sock.setsockopt.side_effect = OSError("unsupported")
        sock.ioctl.side_effect = OSError("unsupported")

        # Must not raise.
        shotgun._set_socket_keepalive(sock)

        # Nothing is tuned once the socket has rejected SO_KEEPALIVE.
        sock.ioctl.assert_not_called()
        self.assertEqual(len(self._keepalive_calls(sock)), 1)

    def test_windows_timers_tuned_via_ioctl(self):
        """
        On Windows the timers are set with an ioctl rather than socket options.
        SIO_KEEPALIVE_VALS is patched in so the branch runs on any platform.
        """
        sock = mock.MagicMock()
        with mock.patch.object(
            socket, "SIO_KEEPALIVE_VALS", self.SIO_SENTINEL, create=True
        ):
            shotgun._set_socket_keepalive(sock)

        sock.ioctl.assert_called_once_with(
            self.SIO_SENTINEL,
            (
                1,
                shotgun.KEEPALIVE_IDLE_SECS * 1000,
                shotgun.KEEPALIVE_INTERVAL_SECS * 1000,
            ),
        )
        # The POSIX socket options must not also be attempted.
        self.assertEqual(len(self._tcp_option_calls(sock)), 0)

    def test_windows_ioctl_failure_is_ignored(self):
        """Keepalive stays enabled even if the timers cannot be tuned."""
        sock = mock.MagicMock()
        sock.ioctl.side_effect = OSError("unsupported")
        with mock.patch.object(
            socket, "SIO_KEEPALIVE_VALS", self.SIO_SENTINEL, create=True
        ):
            # Must not raise.
            shotgun._set_socket_keepalive(sock)

        self.assertEqual(len(self._keepalive_calls(sock)), 1)

    def test_timers_tuned_via_socket_options(self):
        """
        Off Windows the timers are socket options. SIO_KEEPALIVE_VALS is patched
        out so the branch runs there too.
        """
        sock = mock.MagicMock()
        with mock.patch.object(socket, "SIO_KEEPALIVE_VALS", None, create=True):
            shotgun._set_socket_keepalive(sock)

        sock.ioctl.assert_not_called()
        # Which timers exist is platform dependent, but at least the idle timer
        # is available everywhere this library is supported.
        self.assertGreater(len(self._tcp_option_calls(sock)), 0)

    def test_rejected_timer_options_are_ignored(self):
        """A platform that rejects the timers must still get keepalive."""
        sock = mock.MagicMock()

        def reject_tcp_options(level, option, value):
            if level == socket.IPPROTO_TCP:
                raise OSError("unsupported")
            return None

        sock.setsockopt.side_effect = reject_tcp_options
        with mock.patch.object(socket, "SIO_KEEPALIVE_VALS", None, create=True):
            # Must not raise.
            shotgun._set_socket_keepalive(sock)

        self.assertEqual(len(self._keepalive_calls(sock)), 1)
        self.assertGreater(len(self._tcp_option_calls(sock)), 0)

    def test_http_connection_enables_keepalive(self):
        sock = mock.MagicMock()
        with mock.patch("socket.socket", return_value=sock), mock.patch(
            "socket.getaddrinfo", return_value=self._addrinfo(80)
        ):
            conn = shotgun.KeepaliveHTTPConnection("server_path")
            conn.connect()

        self.assertEqual(len(self._keepalive_calls(sock)), 1)

    def test_https_connection_enables_keepalive(self):
        """
        For HTTPS the option lands on the SSL-wrapped socket, which delegates to
        the underlying socket.
        """
        wrapped = mock.MagicMock()
        with mock.patch("socket.socket", return_value=mock.MagicMock()), mock.patch(
            "socket.getaddrinfo", return_value=self._addrinfo(443)
        ), mock.patch("ssl.SSLContext.wrap_socket", return_value=wrapped):
            conn = shotgun.KeepaliveHTTPSConnection("server_path")
            conn.connect()

        self.assertEqual(len(self._keepalive_calls(wrapped)), 1)

    def test_proxied_socket_enables_keepalive(self):
        sock = mock.MagicMock()
        proxy_info = api.lib.httplib2.ProxyInfo(
            api.lib.httplib2.socks.PROXY_TYPE_HTTP, "proxy.example.com", 8080
        )
        with mock.patch.object(
            api.lib.httplib2.socks, "socksocket", return_value=sock
        ), mock.patch("socket.getaddrinfo", return_value=self._addrinfo(80)):
            conn = shotgun.KeepaliveHTTPConnection("server_path", proxy_info=proxy_info)
            conn.connect()

        self.assertEqual(len(self._keepalive_calls(sock)), 1)

    def test_keepalive_failure_does_not_break_connect(self):
        """A socket that rejects keepalive must still yield a usable conn."""

        def reject_keepalive(level, option, value):
            # Leave httplib2's own TCP_NODELAY alone; rejecting that is
            # pre-existing behaviour unrelated to keepalive.
            if (level, option) == (socket.IPPROTO_TCP, socket.TCP_NODELAY):
                return None
            raise OSError("unsupported")

        sock = mock.MagicMock()
        sock.setsockopt.side_effect = reject_keepalive
        with mock.patch("socket.socket", return_value=sock), mock.patch(
            "socket.getaddrinfo", return_value=self._addrinfo(80)
        ):
            conn = shotgun.KeepaliveHTTPConnection("server_path")
            conn.connect()

        self.assertIs(conn.sock, sock)


class TestKeepaliveConnectionType(unittest.TestCase):
    """
    Test that the keepalive-enabled connection classes are injected into
    httplib2 via its connection_type parameter, so the bundled httplib2 needs
    no modification (SG-44724).
    """

    def _connection_type_used(self, url):
        sg = api.Shotgun(url, "script_name", "api_key", connect=False)
        conn = mock.MagicMock()
        response = mock.MagicMock()
        response.status = 200
        response.reason = "OK"
        response.items.return_value = []
        conn.request.return_value = (response, "{}")

        with mock.patch.object(sg, "_get_connection", return_value=conn):
            sg._http_request("GET", "/path", None, {})

        return conn.request.call_args[1]["connection_type"]

    def test_https_uses_keepalive_connection(self):
        self.assertIs(
            self._connection_type_used("https://server_path"),
            shotgun.KeepaliveHTTPSConnection,
        )

    def test_http_uses_keepalive_connection(self):
        self.assertIs(
            self._connection_type_used("http://server_path"),
            shotgun.KeepaliveHTTPConnection,
        )

    def test_connection_classes_are_httplib2_subclasses(self):
        """httplib2 branches on the class to pick constructor arguments."""
        self.assertTrue(
            issubclass(
                shotgun.KeepaliveHTTPSConnection,
                api.lib.httplib2.HTTPSConnectionWithTimeout,
            )
        )
        self.assertTrue(
            issubclass(
                shotgun.KeepaliveHTTPConnection,
                api.lib.httplib2.HTTPConnectionWithTimeout,
            )
        )


if __name__ == "__main__":
    unittest.main()
