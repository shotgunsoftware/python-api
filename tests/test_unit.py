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

import copy
import os
import shutil
import socket
import ssl
import tempfile
import threading
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

    @mock.patch("shotgun_api3._core.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION", False)
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

    @mock.patch("shotgun_api3._core.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION", False)
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

    @mock.patch("shotgun_api3._core.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION", False)
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

    @mock.patch("shotgun_api3._core.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION", False)
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
            "shotgun_api3.shotgun.KeepaliveHttp", side_effect=self._make_connection
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
    Test that KeepaliveHttp injects the keepalive-enabled connection classes
    into httplib2, so the bundled httplib2 needs no modification (SG-44724).
    """

    def _injected_for(self, uri):
        """Return the connection_type KeepaliveHttp hands to httplib2."""
        http = shotgun.KeepaliveHttp()
        with mock.patch.object(
            shotgun.Http, "request", return_value=(mock.MagicMock(), b"")
        ) as base:
            http.request(uri)
        return base.call_args[1]["connection_type"]

    def test_https_uses_keepalive_connection(self):
        self.assertIs(
            self._injected_for("https://server_path/x"),
            shotgun.KeepaliveHTTPSConnection,
        )

    def test_http_uses_keepalive_connection(self):
        self.assertIs(
            self._injected_for("http://server_path/x"),
            shotgun.KeepaliveHTTPConnection,
        )

    def test_unknown_scheme_is_left_to_httplib2(self):
        """httplib2 should raise its own error rather than be handed a class."""
        self.assertIsNone(self._injected_for("ftp://server_path/x"))

    def test_explicit_connection_type_is_respected(self):
        http = shotgun.KeepaliveHttp()
        sentinel = shotgun.KeepaliveHTTPConnection
        with mock.patch.object(
            shotgun.Http, "request", return_value=(mock.MagicMock(), b"")
        ) as base:
            http.request("https://server_path/x", connection_type=sentinel)
        self.assertIs(base.call_args[1]["connection_type"], sentinel)

    def test_shotgun_uses_keepalive_http(self):
        sg = api.Shotgun("https://server_path", "script_name", "api_key", connect=False)
        self.assertIsInstance(sg._get_connection(), shotgun.KeepaliveHttp)

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


class TestMaxConnectionIdleEnvVar(unittest.TestCase):
    """
    SHOTGUN_API_MAX_CONNECTION_IDLE lets operators tune or disable the idle
    expiry without code changes (SG-44724).
    """

    def _make(self):
        return api.Shotgun(
            "http://server_path", "script_name", "api_key", connect=False
        )

    def test_default_is_60(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SHOTGUN_API_MAX_CONNECTION_IDLE", None)
            self.assertEqual(self._make().config.max_connection_idle_secs, 60)

    def test_env_var_overrides_default(self):
        with mock.patch.dict(os.environ, {"SHOTGUN_API_MAX_CONNECTION_IDLE": "15"}):
            self.assertEqual(self._make().config.max_connection_idle_secs, 15)

    def test_env_var_zero_disables_expiry(self):
        with mock.patch.dict(os.environ, {"SHOTGUN_API_MAX_CONNECTION_IDLE": "0"}):
            sg = self._make()
        self.assertEqual(sg.config.max_connection_idle_secs, 0)
        self.assertFalse(sg._is_connection_stale())

    def test_non_integer_env_var_raises(self):
        with mock.patch.dict(os.environ, {"SHOTGUN_API_MAX_CONNECTION_IDLE": "banana"}):
            self.assertRaises(ValueError, self._make)

    def test_negative_env_var_raises(self):
        with mock.patch.dict(os.environ, {"SHOTGUN_API_MAX_CONNECTION_IDLE": "-5"}):
            self.assertRaises(ValueError, self._make)


class TestKeepaliveAcrossRedirects(unittest.TestCase):
    """
    httplib2 follows a redirect by calling self.request() again without
    forwarding connection_type, so injecting it at the call site would lose
    keepalive on the redirected connection. KeepaliveHttp overrides request(),
    which catches those recursive calls too (SG-44724).

    Uses two loopback servers; no external network.
    """

    def setUp(self):
        self.stop = threading.Event()
        self.addCleanup(self.stop.set)
        self.target_port = self._serve(self._target)
        self.redirect_port = self._serve(self._redirect)

    def _serve(self, handler):
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(4)
        port = listener.getsockname()[1]
        self.addCleanup(listener.close)

        def loop():
            while not self.stop.is_set():
                try:
                    conn, _ = listener.accept()
                except OSError:
                    return
                try:
                    conn.settimeout(5)
                    conn.recv(4096)
                    conn.sendall(handler())
                except OSError:
                    pass
                finally:
                    conn.close()

        thread = threading.Thread(target=loop)
        thread.daemon = True
        thread.start()
        return port

    def _target(self):
        return (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: 2\r\n"
            b"Connection: close\r\n"
            b"\r\n"
            b"{}"
        )

    def _redirect(self):
        # 302 to a different authority, which forces httplib2 to build a second
        # connection -- the one that used to miss keepalive.
        return (
            "HTTP/1.1 302 Found\r\n"
            "Location: http://127.0.0.1:%d/target\r\n"
            "Content-Length: 0\r\n"
            "Connection: close\r\n"
            "\r\n" % self.target_port
        ).encode("ascii")

    def test_redirected_connection_is_keepalive_enabled(self):
        http = shotgun.KeepaliveHttp()
        response, _ = http.request(
            "http://127.0.0.1:%d/start" % self.redirect_port, method="GET"
        )

        self.assertEqual(response["status"], "200")
        # Both the original and the redirect target are cached; neither may be a
        # plain httplib2 connection.
        cached = list(http.connections.items())
        self.assertEqual(len(cached), 2, cached)
        for key, conn in cached:
            self.assertIsInstance(conn, shotgun.KeepaliveHTTPConnection, key)


class CustomEntityConfigTestBase(unittest.TestCase):
    """Shared setup for the custom entity config API test cases.

    The custom_entity_* methods are gated on server version 8.91.0"""

    def setUp(self):
        self.sg = api.Shotgun(
            "http://server_path", "script_name", "api_key", connect=False
        )
        self.set_server_version(
            list(api.shotgun.ServerCapabilities.CUSTOM_ENTITY_CONFIG_MIN_VERSION)
        )

    def set_server_version(self, version):
        self.sg._server_caps = api.shotgun.ServerCapabilities(
            self.sg.config.server, {"version": version}
        )


class TestShotgunCustomEntityRead(CustomEntityConfigTestBase):
    """Test case for Shotgun.custom_entity_read"""

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_entity_type_sent(self, call_rpc):
        self.sg.custom_entity_read("CustomEntity08")
        self.assertEqual("custom_entity_read", call_rpc.call_args[0][0])
        self.assertEqual({"entity_type": "CustomEntity08"}, call_rpc.call_args[0][1])


class TestShotgunCustomEntityEnable(CustomEntityConfigTestBase):
    """Test case for Shotgun.custom_entity_enable"""

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_entity_type_sent(self, call_rpc):
        self.sg.custom_entity_enable("CustomEntity08")
        self.assertEqual("custom_entity_enable", call_rpc.call_args[0][0])
        self.assertEqual({"entity_type": "CustomEntity08"}, call_rpc.call_args[0][1])


class TestShotgunCustomEntityConfigure(CustomEntityConfigTestBase):
    """Test case for Shotgun.custom_entity_configure"""

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_optional_params_omitted_by_default(self, call_rpc):
        self.sg.custom_entity_configure("CustomEntity08")
        self.assertEqual("custom_entity_configure", call_rpc.call_args[0][0])
        self.assertEqual({"entity_type": "CustomEntity08"}, call_rpc.call_args[0][1])

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_display_name_sent_without_entity_config(self, call_rpc):
        self.sg.custom_entity_configure("CustomEntity08", display_name="Episode")
        self.assertEqual(
            {"entity_type": "CustomEntity08", "display_name": "Episode"},
            call_rpc.call_args[0][1],
        )

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_entity_config_sent_without_display_name(self, call_rpc):
        entity_config = {"enable_versions": False}
        self.sg.custom_entity_configure("CustomEntity08", entity_config=entity_config)
        self.assertEqual(
            {"entity_type": "CustomEntity08", "entity_config": entity_config},
            call_rpc.call_args[0][1],
        )

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_empty_optional_params_sent(self, call_rpc):
        """Empty values are distinct from omitted ones and must reach the server."""
        self.sg.custom_entity_configure(
            "CustomEntity08", display_name="", entity_config={}
        )
        self.assertEqual(
            {"entity_type": "CustomEntity08", "display_name": "", "entity_config": {}},
            call_rpc.call_args[0][1],
        )


class TestShotgunCustomEntityDisable(CustomEntityConfigTestBase):
    """Test case for Shotgun.custom_entity_disable"""

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_force_omitted_by_default(self, call_rpc):
        self.sg.custom_entity_disable("CustomEntity08")
        self.assertEqual("custom_entity_disable", call_rpc.call_args[0][0])
        self.assertEqual({"entity_type": "CustomEntity08"}, call_rpc.call_args[0][1])

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_force_sent_when_set(self, call_rpc):
        self.sg.custom_entity_disable("CustomEntity08", force=True)
        self.assertEqual("custom_entity_disable", call_rpc.call_args[0][0])
        self.assertEqual(
            {"entity_type": "CustomEntity08", "force": True}, call_rpc.call_args[0][1]
        )


class TestCustomEntityConfigVersionGate(unittest.TestCase):
    """Test case for the custom entity config API's minimum server version guard."""

    MIN_VERSION = api.shotgun.ServerCapabilities.CUSTOM_ENTITY_CONFIG_MIN_VERSION

    # One version below MIN_VERSION, computed rather than hardcoded so this stays
    # correct if MIN_VERSION is ever updated (e.g. to X.Y.0, where patch - 1 would
    # otherwise go negative).
    if MIN_VERSION[2] > 0:
        BELOW_MIN_VERSION = (MIN_VERSION[0], MIN_VERSION[1], MIN_VERSION[2] - 1)
    else:
        BELOW_MIN_VERSION = (MIN_VERSION[0], MIN_VERSION[1] - 1, 9)

    def setUp(self):
        self.sg = api.Shotgun(
            "http://server_path", "script_name", "api_key", connect=False
        )

    def _set_server_version(self, version):
        self.sg._server_caps = api.shotgun.ServerCapabilities(
            self.sg.config.server, {"version": version}
        )

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_below_minimum_version_raises_before_call_rpc(self, call_rpc):
        self._set_server_version(list(self.BELOW_MIN_VERSION))
        self.assertRaises(
            api.ShotgunError, self.sg.custom_entity_read, "CustomEntity08"
        )
        call_rpc.assert_not_called()

    @mock.patch("shotgun_api3.Shotgun._call_rpc")
    def test_minimum_version_boundary_is_supported(self, call_rpc):
        self._set_server_version(list(self.MIN_VERSION))
        self.sg.custom_entity_read("CustomEntity08")
        call_rpc.assert_called_once()


class _NamedFile(object):
    """A real file object reporting an arbitrary name."""

    def __init__(self, fd, name):
        self._fd = fd
        self.name = name

    def __getattr__(self, attr):
        return getattr(self._fd, attr)


class TestFormPostHandlerEncode(unittest.TestCase):
    """
    Multipart encoding of form fields and file names.
    """

    BOUNDARY = "BOUNDARY"

    def setUp(self):
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        self.path = os.path.join(tmp_dir, "data.txt")
        with open(self.path, "wb") as fh:
            fh.write(b"data")

    def _file(self, name):
        fd = open(self.path, "rb")
        self.addCleanup(fd.close)
        return _NamedFile(fd, name)

    def _encode(self, params, files):
        _, body = shotgun.FormPostHandler().encode(
            params, files, boundary=self.BOUNDARY
        )
        return body

    def test_plain_upload_is_unchanged(self):
        body = self._encode(
            [("entity_id", 1), ("display_name", "report.txt")],
            [("file", self._file("/renders/report.txt"))],
        )
        self.assertIn(
            b'Content-Disposition: form-data; name="display_name"'
            b"\r\n\r\nreport.txt\r\n",
            body,
        )
        self.assertIn(
            b'Content-Disposition: form-data; name="file"; filename="report.txt"\r\n'
            b"Content-Type: text/plain\r\nContent-Length: 4\r\n\r\ndata\r\n",
            body,
        )
        self.assertEqual(body.count(b"--BOUNDARY\r\n"), 3)

    def test_value_containing_boundary_raises(self):
        display_name = "report.txt\r\n--BOUNDARY\r\nmore text"
        with self.assertRaises(ValueError):
            self._encode(
                [("entity_id", 1), ("display_name", display_name)],
                [("file", self._file("report.txt"))],
            )

    def test_value_with_line_breaks_is_kept(self):
        body = self._encode(
            [("tag_list", "a\r\nb")], [("file", self._file("report.txt"))]
        )
        self.assertIn(b"\r\n\r\na\r\nb\r\n--BOUNDARY\r\n", body)
        self.assertEqual(body.count(b"--BOUNDARY\r\n"), 2)

    def test_filename_special_characters_are_percent_encoded(self):
        name = 'shot\r\nv2: final\r\n\r\n"notes.txt'
        body = self._encode([], [("file", self._file(name))])
        self.assertNotIn(b"\r\nv2: final", body)
        self.assertIn(
            b'filename="shot%0D%0Av2: final%0D%0A%0D%0A%22notes.txt"\r\n',
            body,
        )

    def test_field_name_special_characters_are_percent_encoded(self):
        body = self._encode(
            [('entity_id"\r\nv2: final', 1)], [("file", self._file("a.txt"))]
        )
        self.assertNotIn(b"\r\nv2: final", body)
        self.assertIn(b'name="entity_id%22%0D%0Av2: final"\r\n\r\n1\r\n', body)

    def test_windows_path_is_reduced_to_base_name(self):
        body = self._encode([], [("file", self._file("C:\\renders\\shot.txt"))])
        self.assertIn(b'filename="shot.txt"', body)


class TestAuthParamsServerCaps(unittest.TestCase):
    """Version-gated auth params: the shared core never fetches server caps itself."""

    URL = "http://server_path"

    def _caps(self, version):
        return shotgun.ServerCapabilities("server_path", {"version": version})

    def _script_sg(self, **kw):
        return api.Shotgun(self.URL, "script", "key", connect=False, **kw)

    def _session_sg(self):
        return api.Shotgun(self.URL, session_token="tok", connect=False)

    def test_script_auth_needs_no_caps(self):
        sg = self._script_sg()
        with mock.patch.object(sg, "info") as info:
            params = sg._auth_params()
        self.assertEqual({"script_name": "script", "script_key": "key"}, params)
        info.assert_not_called()

    def test_core_requires_caps_for_session_token(self):
        sg = self._session_sg()
        with self.assertRaises(shotgun._ServerCapsRequired):
            shotgun._SGCore._auth_params(sg)

    def test_core_requires_caps_for_sudo_as_login(self):
        sg = self._script_sg(sudo_as_login="someone")
        with self.assertRaises(shotgun._ServerCapsRequired):
            shotgun._SGCore._auth_params(sg)

    def test_session_token_version_gate(self):
        sg = self._session_sg()
        with self.assertRaises(api.ShotgunError):
            shotgun._SGCore._auth_params(sg, self._caps((5, 2, 9)))

        params = shotgun._SGCore._auth_params(sg, self._caps((5, 3, 0)))
        self.assertEqual("tok", params["session_token"])
        self.assertNotIn("reject_if_expired", params)

        params = shotgun._SGCore._auth_params(sg, self._caps((5, 4, 4)))
        self.assertTrue(params["reject_if_expired"])

    def test_sudo_as_login_version_gate(self):
        sg = self._script_sg(sudo_as_login="someone")
        with self.assertRaises(api.ShotgunError):
            shotgun._SGCore._auth_params(sg, self._caps((5, 3, 11)))

        params = shotgun._SGCore._auth_params(sg, self._caps((5, 3, 12)))
        self.assertEqual("someone", params["sudo_as_login"])

    def test_sync_client_fetches_caps_lazily(self):
        sg = self._session_sg()
        with mock.patch.object(sg, "info", return_value={"version": [5, 4, 4]}) as info:
            params = sg._auth_params()
            sg._auth_params()
        self.assertTrue(params["reject_if_expired"])
        info.assert_called_once_with()  # fetched once, then cached

    def test_sync_client_gate_error_after_lazy_fetch(self):
        sg = self._session_sg()
        with mock.patch.object(sg, "info", return_value={"version": [5, 2, 0]}):
            with self.assertRaises(api.ShotgunError):
                sg._auth_params()

    def test_build_payload_passes_caps_through(self):
        sg = self._session_sg()
        payload = sg._build_payload("read", {"a": 1}, caps=self._caps((5, 4, 4)))
        self.assertEqual("read", payload["method_name"])
        self.assertEqual("tok", payload["params"][0]["session_token"])
        self.assertEqual({"a": 1}, payload["params"][1])


class TestRetryHelpers(unittest.TestCase):
    """Retry decisions shared by the sync and async clients."""

    def setUp(self):
        self.sg = api.Shotgun("http://server_path", "script", "key", connect=False)
        self.sg.config.rpc_attempt_interval = 0
        self.sg.BACKOFF = 0.5

    @staticmethod
    def _protocol_error(code, msg="msg"):
        return api.ProtocolError("host", code, msg, {})

    def test_ssl_errors_are_retryable(self):
        is_retryable = shotgun._SGCore._is_retryable_connection_error
        self.assertTrue(is_retryable(ssl.SSLEOFError()))
        self.assertTrue(is_retryable(ssl.SSLError()))
        self.assertTrue(is_retryable(ssl.CertificateError()))

    def test_other_errors_are_not_retryable(self):
        is_retryable = shotgun._SGCore._is_retryable_connection_error
        self.assertFalse(is_retryable(socket.timeout()))
        self.assertFalse(is_retryable(ValueError()))

    def test_gateway_retry_delay_scales_with_attempt(self):
        for code in (502, 504):
            err = self._protocol_error(code)
            self.assertEqual(0.5, self.sg._gateway_retry_delay(err, 1))
            self.assertEqual(1.0, self.sg._gateway_retry_delay(err, 2))

    def test_gateway_retry_delay_none_on_last_attempt(self):
        err = self._protocol_error(502)
        self.assertIsNone(self.sg._gateway_retry_delay(err, self.sg.MAX_ATTEMPTS))

    def test_gateway_retry_delay_none_for_other_statuses(self):
        for code in (400, 403, 500, 503):
            self.assertIsNone(
                self.sg._gateway_retry_delay(self._protocol_error(code), 1)
            )

    def test_annotate_protocol_error(self):
        err = shotgun._SGCore._annotate_protocol_error(
            self._protocol_error(500, "boom"), {"h": "v"}, "body"
        )
        self.assertEqual({"h": "v"}, err.headers)
        self.assertEqual("boom", err.errmsg)

    def test_annotate_protocol_error_403_appends_body(self):
        err = shotgun._SGCore._annotate_protocol_error(
            self._protocol_error(403, "Forbidden"), {}, "blocked page"
        )
        self.assertEqual("Forbidden: blocked page", err.errmsg)

    def test_make_call_retries_ssl_error_then_succeeds(self):
        ok = ((200, "OK"), {}, "body")
        self.sg._http_request = mock.Mock(
            side_effect=[ssl.SSLEOFError(), ssl.SSLError(), ok]
        )
        self.sg._close_connection = mock.Mock()

        self.assertEqual(ok, self.sg._make_call("POST", "/p", None, None))
        self.assertEqual(3, self.sg._http_request.call_count)
        self.assertEqual(2, self.sg._close_connection.call_count)

    def test_make_call_raises_ssl_error_when_attempts_exhausted(self):
        self.sg._http_request = mock.Mock(side_effect=ssl.SSLEOFError())
        self.sg._close_connection = mock.Mock()

        with self.assertRaises(ssl.SSLEOFError):
            self.sg._make_call("POST", "/p", None, None)
        self.assertEqual(
            self.sg.config.max_rpc_attempts, self.sg._http_request.call_count
        )

    def test_make_call_does_not_retry_other_errors(self):
        self.sg._http_request = mock.Mock(side_effect=socket.timeout())
        self.sg._close_connection = mock.Mock()

        with self.assertRaises(socket.timeout):
            self.sg._make_call("POST", "/p", None, None)
        self.assertEqual(1, self.sg._http_request.call_count)
        self.sg._close_connection.assert_called_once_with()


def _caps(version):
    return shotgun.ServerCapabilities("server_path", {"version": version})


class TestFindFlow(unittest.TestCase):
    """``_find_flow`` is driven by hand: no I/O, the test plays the driver."""

    NEW = (8, 0, 0)  # supports pagination without counts
    OLD = (7, 0, 0)  # pagination with counts

    def setUp(self):
        self.sg = api.Shotgun("http://server_path", "script", "key", connect=False)
        self.sg.config._records_per_page = 2  # the property is read-only

    def _flow(self, limit=0, page=0, **kw):
        kw.setdefault("include_archived_projects", True)
        return self.sg._find_flow(
            "Shot",
            [],
            None,
            None,
            None,
            limit,
            False,
            page,
            **{
                "include_archived_projects": kw["include_archived_projects"],
                "additional_filter_presets": kw.get("additional_filter_presets"),
            }
        )

    def _run(self, flow, version, replies):
        """Play the driver; returns (steps requested, final value)."""
        steps, replies = [], list(replies)
        reply = None
        while True:
            try:
                step = flow.send(reply)
            except StopIteration as stop:
                return steps, stop.value
            # the flow mutates one params dict between requests: keep a snapshot
            steps.append(step if step is shotgun.NEED_CAPS else copy.deepcopy(step))
            reply = _caps(version) if step is shotgun.NEED_CAPS else replies.pop(0)

    @staticmethod
    def _rec(i):
        return {"type": "Shot", "id": i}

    def test_invalid_limit_raises_before_requesting_caps(self):
        with self.assertRaises(ValueError):
            next(self._flow(limit="x"))

    def test_invalid_page_raises_before_requesting_caps(self):
        with self.assertRaises(ValueError):
            next(self._flow(page=-1))

    def test_filter_operator_with_dict_filters_raises(self):
        flow = self.sg._find_flow(
            "Shot", {}, None, None, "all", 0, False, 0, True, None
        )
        with self.assertRaises(api.ShotgunError):
            next(flow)

    def test_requests_caps_first(self):
        self.assertIs(shotgun.NEED_CAPS, next(self._flow()))

    def test_unsupported_server_raises(self):
        flow = self._flow(include_archived_projects=False)
        next(flow)
        with self.assertRaises(api.ShotgunError):
            flow.send(_caps((5, 3, 13)))

    def test_single_page_when_limit_fits(self):
        steps, result = self._run(
            self._flow(limit=1), self.NEW, [{"entities": [self._rec(1)]}]
        )

        self.assertEqual(2, len(steps))
        method, params = steps[1]
        self.assertEqual("read", method)
        self.assertEqual({"entities_per_page": 1, "current_page": 1}, params["paging"])
        self.assertFalse(params["return_paging_info_without_counts"])
        self.assertEqual([self._rec(1)], result)

    def test_explicit_page(self):
        steps, result = self._run(
            self._flow(page=3), self.NEW, [{"entities": [self._rec(7)]}]
        )

        self.assertEqual(3, steps[1][1]["paging"]["current_page"])
        self.assertEqual([self._rec(7)], result)

    def test_paginates_without_counts(self):
        replies = [
            {
                "entities": [self._rec(1), self._rec(2)],
                "paging_info": {"has_next_page": True},
            },
            {"entities": [self._rec(3)], "paging_info": {"has_next_page": False}},
        ]
        steps, result = self._run(self._flow(), self.NEW, replies)

        pages = [s[1]["paging"]["current_page"] for s in steps[1:]]
        self.assertEqual([1, 2], pages)
        self.assertTrue(steps[1][1]["return_paging_info_without_counts"])
        self.assertEqual([self._rec(1), self._rec(2), self._rec(3)], result)

    def test_paginates_with_counts_on_older_server(self):
        replies = [
            {
                "entities": [self._rec(1), self._rec(2)],
                "paging_info": {"entity_count": 3},
            },
            {"entities": [self._rec(3)], "paging_info": {"entity_count": 3}},
        ]
        steps, result = self._run(self._flow(), self.OLD, replies)

        self.assertEqual(2, len(steps[1:]))
        self.assertTrue(steps[1][1]["return_paging_info"])
        self.assertEqual([self._rec(i) for i in (1, 2, 3)], result)

    def test_older_server_stops_on_empty_page(self):
        replies = [{"entities": [], "paging_info": {"entity_count": 0}}]
        steps, result = self._run(self._flow(), self.OLD, replies)

        self.assertEqual(1, len(steps[1:]))
        self.assertEqual([], result)

    def test_limit_truncates_across_pages(self):
        replies = [
            {
                "entities": [self._rec(1), self._rec(2)],
                "paging_info": {"has_next_page": True},
            },
            {
                "entities": [self._rec(3), self._rec(4)],
                "paging_info": {"has_next_page": True},
            },
        ]
        steps, result = self._run(self._flow(limit=3), self.NEW, replies)

        self.assertEqual(2, len(steps[1:]))
        self.assertEqual([self._rec(i) for i in (1, 2, 3)], result)

    def test_sync_find_drives_the_flow(self):
        self.sg._server_caps = _caps(self.NEW)
        self.sg._call_rpc = mock.Mock(return_value={"entities": [self._rec(1)]})

        result = self.sg.find("Shot", [], limit=1)

        self.assertEqual([self._rec(1)], result)
        self.assertEqual("read", self.sg._call_rpc.call_args[0][0])

    def test_sync_find_does_not_swallow_stop_iteration_from_rpc(self):
        # A mock with an exhausted side_effect raises StopIteration from _call_rpc itself.
        self.sg._server_caps = _caps(self.NEW)
        self.sg._call_rpc = mock.Mock(side_effect=StopIteration)

        with self.assertRaises(StopIteration):
            self.sg.find("Shot", [], limit=1)


class TestSharedBuilders(unittest.TestCase):
    def setUp(self):
        self.sg = api.Shotgun("http://server_path", "script", "key", connect=False)

    # create
    def test_prepare_create_defaults_and_splits_image(self):
        params, image, filmstrip = self.sg._prepare_create(
            "Shot", {"code": "a", "image": "p.png"}, None
        )

        self.assertEqual(["id"], params["return_fields"])
        self.assertEqual([{"field_name": "code", "value": "a"}], params["fields"])
        self.assertEqual(("p.png", None), (image, filmstrip))

    def test_prepare_create_does_not_mutate_input(self):
        data = {"code": "a", "image": "p.png"}
        self.sg._prepare_create("Shot", data, ["id"])
        self.assertEqual({"code": "a", "image": "p.png"}, data)

    def test_prepare_create_filmstrip_needs_caps(self):
        with self.assertRaises(shotgun._ServerCapsRequired):
            self.sg._prepare_create("Shot", {"filmstrip_image": "f.png"}, None)
        with self.assertRaises(api.ShotgunError):
            self.sg._prepare_create(
                "Shot", {"filmstrip_image": "f.png"}, None, caps=_caps((3, 0, 9))
            )

        _, _, filmstrip = self.sg._prepare_create(
            "Shot", {"filmstrip_image": "f.png"}, None, caps=_caps((3, 1, 0))
        )
        self.assertEqual("f.png", filmstrip)

    def test_prepare_create_without_filmstrip_needs_no_caps(self):
        self.sg._prepare_create("Shot", {"code": "a"}, None)  # does not raise

    # update
    def test_prepare_update_only_image_has_no_rpc_params(self):
        params, image, _ = self.sg._prepare_update("Shot", 1, {"image": "p.png"}, None)

        self.assertIsNone(params)
        self.assertEqual("p.png", image)

    def test_prepare_update_none_image_is_sent_as_a_field(self):
        params, image, _ = self.sg._prepare_update("Shot", 1, {"image": None}, None)

        self.assertIsNone(image)
        self.assertEqual([{"field_name": "image", "value": None}], params["fields"])

    def test_prepare_update_filmstrip_needs_caps(self):
        with self.assertRaises(shotgun._ServerCapsRequired):
            self.sg._prepare_update("Shot", 1, {"filmstrip_image": "f.png"}, None)

    # batch
    def test_build_batch_calls_empty(self):
        self.assertEqual([], self.sg._build_batch_calls([]))

    def test_build_batch_calls_rejects_non_list(self):
        with self.assertRaises(api.ShotgunError):
            self.sg._build_batch_calls(({},))

    def test_build_batch_calls_rejects_invalid_request(self):
        for bad in (
            {"request_type": "create"},
            {"request_type": "nope", "entity_type": "Shot"},
            {"request_type": "update", "entity_type": "Shot", "data": {}},
        ):
            with self.assertRaises(api.ShotgunError):
                self.sg._build_batch_calls([bad])

    def test_build_batch_calls_shapes(self):
        calls = self.sg._build_batch_calls(
            [
                {
                    "request_type": "create",
                    "entity_type": "Shot",
                    "data": {"code": "a"},
                },
                {
                    "request_type": "update",
                    "entity_type": "Shot",
                    "entity_id": 2,
                    "data": {"code": "b"},
                    "multi_entity_update_modes": {"code": "add"},
                },
                {"request_type": "delete", "entity_type": "Shot", "entity_id": 3},
            ]
        )

        self.assertEqual(["id"], calls[0]["return_fields"])
        self.assertEqual(
            [{"field_name": "code", "value": "b", "multi_entity_update_mode": "add"}],
            calls[1]["fields"],
        )
        self.assertEqual({"request_type": "delete", "type": "Shot", "id": 3}, calls[2])

    # records
    def test_parse_records_without_image_needs_no_caps(self):
        self.assertEqual(
            [{"type": "Shot", "id": 1}],
            shotgun._SGCore._parse_records(self.sg, {"type": "Shot", "id": 1}, None),
        )

    def test_parse_records_with_image_needs_caps(self):
        rec = {"type": "Shot", "id": 1, "image": "http://x/y.png"}
        with self.assertRaises(shotgun._ServerCapsRequired):
            shotgun._SGCore._parse_records(self.sg, [dict(rec)], None)

        self.assertEqual(
            [rec],
            shotgun._SGCore._parse_records(self.sg, [dict(rec)], _caps((8, 0, 0))),
        )

    def test_parse_records_old_server_thumbnail_fallback_is_pluggable(self):
        rec = {"type": "Shot", "id": 1, "image": "x"}
        with mock.patch.object(
            self.sg, "_build_thumb_url", return_value="http://thumb"
        ):
            out = shotgun._SGCore._parse_records(self.sg, [rec], _caps((3, 2, 0)))
        self.assertEqual("http://thumb", out[0]["image"])

    def test_core_has_no_thumbnail_fallback(self):
        with self.assertRaises(NotImplementedError):
            shotgun._SGCore._build_thumb_url(self.sg, "Shot", 1)

    def test_sync_parse_records_fetches_caps_only_for_images(self):
        with mock.patch.object(
            self.sg, "info", return_value={"version": [8, 0, 0]}
        ) as info:
            self.sg._parse_records([{"type": "Shot", "id": 1}])
            info.assert_not_called()
            self.sg._parse_records([{"type": "Shot", "id": 1, "image": "u"}])
            info.assert_called_once_with()


class TestSyncMethodsUseSharedHelpers(unittest.TestCase):
    """The sync methods are thin glue over the core helpers; check the glue with rpc mocked."""

    def setUp(self):
        self.sg = api.Shotgun("http://server_path", "script", "key", connect=False)
        self.sg._server_caps = _caps((8, 0, 0))
        self.sg._call_rpc = mock.Mock()

    def test_create(self):
        self.sg._call_rpc.return_value = {"type": "Shot", "id": 5, "code": "a"}

        result = self.sg.create("Shot", {"code": "a"})

        self.assertEqual({"type": "Shot", "id": 5, "code": "a"}, result)
        self.sg._call_rpc.assert_called_once_with(
            "create",
            {
                "type": "Shot",
                "fields": [{"field_name": "code", "value": "a"}],
                "return_fields": ["id"],
            },
            first=True,
        )

    def test_create_with_image_uploads_thumbnail(self):
        self.sg._call_rpc.return_value = {"type": "Shot", "id": 5}
        self.sg.upload_thumbnail = mock.Mock()
        self.sg.find_one = mock.Mock(return_value={"image": "http://thumb"})

        result = self.sg.create("Shot", {"image": "p.png"})

        self.sg.upload_thumbnail.assert_called_once_with("Shot", 5, "p.png")
        self.assertEqual("http://thumb", result["image"])

    def test_update(self):
        self.sg._call_rpc.return_value = {"type": "Shot", "id": 5, "code": "b"}

        result = self.sg.update("Shot", 5, {"code": "b"})

        self.assertEqual("b", result["code"])
        method, params = self.sg._call_rpc.call_args[0]
        self.assertEqual("update", method)
        self.assertEqual([{"field_name": "code", "value": "b"}], params["fields"])

    def test_update_only_image_makes_no_rpc(self):
        self.sg.upload_thumbnail = mock.Mock()
        self.sg.find_one = mock.Mock(return_value={"image": "http://thumb"})

        result = self.sg.update("Shot", 5, {"image": "p.png"})

        self.sg._call_rpc.assert_not_called()
        self.assertEqual({"id": 5, "type": "Shot", "image": "http://thumb"}, result)

    def test_batch_empty_makes_no_rpc(self):
        self.assertEqual([], self.sg.batch([]))
        self.sg._call_rpc.assert_not_called()

    def test_batch(self):
        self.sg._call_rpc.return_value = [True]

        self.assertEqual(
            [True],
            self.sg.batch(
                [{"request_type": "delete", "entity_type": "Shot", "entity_id": 3}]
            ),
        )
        self.sg._call_rpc.assert_called_once_with(
            "batch", [{"request_type": "delete", "type": "Shot", "id": 3}]
        )

    def test_batch_rejects_non_list_without_rpc(self):
        with self.assertRaises(api.ShotgunError):
            self.sg.batch(({},))
        self.sg._call_rpc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
