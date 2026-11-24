# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""Tests for the async client. Skipped when the optional httpx dependency is missing."""

import asyncio
import contextlib
import datetime
import http.server
import io
import json
import re
import os
import socket
import ssl
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

try:
    import httpx
    import shotgun_api3
    from shotgun_api3 import aio
except ImportError:  # pragma: no cover - httpx is an optional extra
    httpx = None

URL = "http://server_path"


def make(**kwargs):
    kwargs.setdefault("script_name", "script")
    kwargs.setdefault("api_key", "key")
    return aio.AsyncShotgun(URL, **kwargs)


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestAsyncShotgunConfig(unittest.TestCase):
    def test_reuses_sync_config_handling(self):
        sg = make(
            http_proxy="user:pass@proxy.example:8080", convert_datetimes_to_utc=False
        )

        self.assertEqual("script", sg.config.script_name)
        self.assertEqual("server_path", sg.config.server)
        self.assertFalse(sg.config.convert_datetimes_to_utc)
        self.assertEqual("proxy.example", sg.config.proxy_server)
        self.assertEqual(8080, sg.config.proxy_port)
        self.assertTrue(any(ua.startswith("shotgun-json") for ua in sg._user_agents))

    def test_reuses_sync_validation(self):
        with self.assertRaises(ValueError):
            aio.AsyncShotgun(URL)  # no credentials
        with self.assertRaises(ValueError):
            make(login="a", password="b")  # script and user credentials
        with self.assertRaises(ValueError):
            make(http_proxy="proxy.example:notaport")

    def test_session_token_auth(self):
        sg = aio.AsyncShotgun(URL, session_token="tok")
        self.assertEqual("tok", sg.config.session_token)

    def test_no_auth_token_support(self):
        with self.assertRaises(TypeError):
            aio.AsyncShotgun(URL, login="a", password="b", auth_token="123456")


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestBuildClient(unittest.TestCase):
    def _kwargs(self, **sg_kwargs):
        sg = make(**sg_kwargs)
        with mock.patch.object(aio.httpx, "AsyncClient") as client_cls:
            sg._build_client()
        return client_cls.call_args.kwargs

    def test_defaults(self):
        kwargs = self._kwargs()

        self.assertIsInstance(kwargs["verify"], ssl.SSLContext)
        self.assertIsNone(kwargs["proxy"])
        self.assertEqual(aio.DEFAULT_MAX_CONNECTIONS, kwargs["limits"].max_connections)
        self.assertEqual(
            aio.DEFAULT_MAX_CONNECTIONS, kwargs["limits"].max_keepalive_connections
        )

    def test_max_connections(self):
        self.assertEqual(3, self._kwargs(max_connections=3)["limits"].max_connections)

    def test_proxy_with_encoded_credentials(self):
        kwargs = self._kwargs(http_proxy="user:p@ss@proxy.example:8080")
        self.assertEqual("http://user:p%40ss@proxy.example:8080", kwargs["proxy"])

    def test_proxy_without_credentials(self):
        kwargs = self._kwargs(http_proxy="proxy.example:8080")
        self.assertEqual("http://proxy.example:8080", kwargs["proxy"])

    def test_timeout_comes_from_config(self):
        sg = make()
        sg.config.timeout_secs = 7
        with mock.patch.object(aio.httpx, "AsyncClient") as client_cls:
            sg._build_client()
        self.assertEqual(7, client_cls.call_args.kwargs["timeout"])

    def test_idle_seconds_map_to_keepalive_expiry(self):
        sg = make()
        for idle, expiry in ((30, 30), (0, None), (None, None)):
            sg.config.max_connection_idle_secs = idle
            with mock.patch.object(aio.httpx, "AsyncClient") as client_cls:
                sg._build_client()
            self.assertEqual(
                expiry, client_cls.call_args.kwargs["limits"].keepalive_expiry
            )

    def test_custom_ca_file_is_used(self):
        sg = make(ca_certs="/does/not/exist.pem")
        with self.assertRaises(FileNotFoundError):
            sg._build_client()


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    connection_closed = None  # threading.Event set on the class per test

    def do_GET(self):
        self.send_response(200)
        self.send_header("content-length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def finish(self):  # runs when the server side of the connection ends
        super().finish()
        type(self).connection_closed.set()

    def log_message(self, *args):
        pass


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestLifecycle(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        handler = type("H", (_Handler,), {"connection_closed": threading.Event()})
        self.handler = handler
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(
            target=self.server.serve_forever, args=(0.01,), daemon=True
        ).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = "http://127.0.0.1:%d/" % self.server.server_address[1]

    async def test_client_is_created_lazily(self):
        sg = make()
        self.assertIsNone(sg._client)
        client = sg._get_client()
        self.assertIs(client, sg._get_client())
        await sg.close()

    async def test_context_manager_closes_connections(self):
        async with make() as sg:
            client = sg._get_client()
            response = await client.get(self.url)
            self.assertEqual(b"ok", response.content)
            self.assertFalse(self.handler.connection_closed.is_set())  # kept alive

        self.assertTrue(client.is_closed)
        self.assertIsNone(sg._client)
        self.assertTrue(self.handler.connection_closed.wait(timeout=5))

    async def test_explicit_close_is_idempotent(self):
        sg = make()
        client = sg._get_client()
        await sg.close()
        await sg.close()
        self.assertTrue(client.is_closed)

    async def test_usable_again_after_close(self):
        sg = make()
        first = sg._get_client()
        await sg.close()
        second = sg._get_client()
        self.assertIsNot(first, second)
        self.assertFalse(second.is_closed)
        await sg.close()


class _RpcServer:
    """
    A local server speaking the rpc protocol. ``respond(payload, index)`` returns
    ``(status, body)`` for the ``index``-th request; every request is recorded.
    """

    def __init__(self, respond):
        self.requests = []
        self.connections = 0  # TCP connections accepted
        self.inflight = 0
        self.max_inflight = 0  # most requests being served at once
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def setup(self):
                super().setup()
                with outer.lock:
                    outer.connections += 1

            def do_POST(self):
                raw = self.rfile.read(int(self.headers["content-length"]))
                payload = json.loads(raw)
                with outer.lock:
                    index = len(outer.requests)
                    outer.requests.append(
                        {"path": self.path, "headers": self.headers, "payload": payload}
                    )
                with outer.lock:
                    outer.inflight += 1
                    outer.max_inflight = max(outer.max_inflight, outer.inflight)
                try:
                    status, body = respond(payload, index)
                finally:
                    with outer.lock:
                        outer.inflight -= 1
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.lock = threading.Lock()
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(
            target=self.server.serve_forever, args=(0.01,), daemon=True
        ).start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    @property
    def methods(self):
        return [r["payload"]["method_name"] for r in self.requests]


class _RpcTestCase(unittest.IsolatedAsyncioTestCase):
    def serve(self, respond):
        server = _RpcServer(respond)
        self.addCleanup(server.stop)
        return server

    async def client(self, server, **kwargs):
        kwargs.setdefault("script_name", "script")
        kwargs.setdefault("api_key", "key")
        sg = aio.AsyncShotgun(server.url, **kwargs)
        sg.BACKOFF = 0
        sg.config.rpc_attempt_interval = 0
        self.addAsyncCleanup(sg.close)
        return sg


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestRpc(_RpcTestCase):
    async def test_round_trip(self):
        server = self.serve(lambda payload, i: (200, {"results": [{"id": 1}]}))
        sg = await self.client(server)

        self.assertEqual([{"id": 1}], await sg._call_rpc("read", {"a": 1}))

        request = server.requests[0]
        self.assertEqual("/api3/json", request["path"])
        self.assertEqual(
            "application/json; charset=utf-8", request["headers"]["content-type"]
        )
        self.assertIn("shotgun-json", request["headers"]["user-agent"])
        payload = request["payload"]
        self.assertEqual("read", payload["method_name"])
        self.assertEqual(
            {"script_name": "script", "script_key": "key"}, payload["params"][0]
        )
        self.assertEqual({"a": 1}, payload["params"][1])

    async def test_first(self):
        server = self.serve(
            lambda payload, i: (200, {"results": [{"id": 1}, {"id": 2}]})
        )
        sg = await self.client(server)

        self.assertEqual({"id": 1}, await sg._call_rpc("read", None, first=True))

    async def test_datetimes_are_transformed_like_the_sync_client(self):
        server = self.serve(
            lambda payload, i: (200, {"results": [{"at": "2020-01-02T03:04:05Z"}]})
        )
        sg = await self.client(server)

        [record] = await sg._call_rpc("read", None)

        self.assertIsInstance(record["at"], datetime.datetime)

    async def test_basic_auth_from_url(self):
        server = self.serve(lambda payload, i: (200, {"results": []}))
        sg = await self.client(server)
        sg.config.authorization = "Basic abc"

        await sg._call_rpc("read", None)

        self.assertEqual("Basic abc", server.requests[0]["headers"]["authorization"])

    async def test_gateway_error_then_success(self):
        server = self.serve(
            lambda payload, i: (502, b"bad") if i == 0 else (200, {"results": [1]})
        )
        sg = await self.client(server)

        self.assertEqual([1], await sg._call_rpc("read", None))
        self.assertEqual(2, len(server.requests))

    async def test_gateway_error_waits_with_backoff(self):
        server = self.serve(
            lambda payload, i: (504, b"x") if i < 2 else (200, {"results": [1]})
        )
        sg = await self.client(server)
        sg.BACKOFF = 0.5

        with mock.patch.object(aio.asyncio, "sleep", new=mock.AsyncMock()) as sleep:
            await sg._call_rpc("read", None)

        self.assertEqual([mock.call(0.5), mock.call(1.0)], sleep.call_args_list)

    async def test_gateway_error_exhausted(self):
        server = self.serve(lambda payload, i: (502, b"bad"))
        sg = await self.client(server)

        with self.assertRaises(shotgun_api3.ProtocolError) as ctx:
            await sg._call_rpc("read", None)

        self.assertEqual(502, ctx.exception.errcode)
        self.assertEqual(sg.MAX_ATTEMPTS, len(server.requests))

    async def test_other_http_errors_are_not_retried(self):
        server = self.serve(lambda payload, i: (503, b"busy"))
        sg = await self.client(server)

        with self.assertRaises(shotgun_api3.ProtocolError) as ctx:
            await sg._call_rpc("read", None)

        self.assertEqual(503, ctx.exception.errcode)
        self.assertEqual(1, len(server.requests))

    async def test_403_includes_the_error_page(self):
        server = self.serve(lambda payload, i: (403, b"blocked by admin"))
        sg = await self.client(server)

        with self.assertRaises(shotgun_api3.ProtocolError) as ctx:
            await sg._call_rpc("read", None)

        self.assertIn("blocked by admin", ctx.exception.errmsg)

    async def test_server_fault(self):
        server = self.serve(
            lambda payload, i: (200, {"exception": True, "message": "boom"})
        )
        sg = await self.client(server)

        with self.assertRaises(shotgun_api3.Fault) as ctx:
            await sg._call_rpc("read", None)

        self.assertEqual("boom", str(ctx.exception))

    async def test_authentication_fault(self):
        body = {"exception": True, "error_code": 102, "message": "bad key"}
        sg = await self.client(self.serve(lambda payload, i: (200, body)))

        with self.assertRaises(shotgun_api3.AuthenticationFault):
            await sg._call_rpc("read", None)

    async def test_timeout_raises_socket_timeout(self):
        def slow(payload, i):
            time.sleep(1)
            return 200, {"results": []}

        sg = await self.client(self.serve(slow))
        sg.config.timeout_secs = 0.2

        with self.assertRaises(socket.timeout):
            await sg._call_rpc("read", None)

    async def test_connection_refused_raises_os_error(self):
        server = self.serve(lambda payload, i: (200, {}))
        sg = await self.client(server)
        server.stop()

        with self.assertRaises(ConnectionRefusedError):
            await sg._call_rpc("read", None)


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestRetries(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sg = make()
        self.sg.config.rpc_attempt_interval = 0
        self.ok = ((200, "OK"), {}, b"body")

    async def test_ssl_errors_are_retried(self):
        self.sg._http_request = mock.AsyncMock(
            side_effect=[ssl.SSLEOFError(), ssl.SSLError(), self.ok]
        )

        self.assertEqual(self.ok, await self.sg._make_call("POST", "/p", None, None))
        self.assertEqual(3, self.sg._http_request.await_count)

    async def test_ssl_error_raised_when_attempts_exhausted(self):
        self.sg._http_request = mock.AsyncMock(side_effect=ssl.SSLEOFError())

        with self.assertRaises(ssl.SSLEOFError):
            await self.sg._make_call("POST", "/p", None, None)
        self.assertEqual(
            self.sg.config.max_rpc_attempts, self.sg._http_request.await_count
        )

    async def test_other_errors_are_not_retried(self):
        self.sg._http_request = mock.AsyncMock(side_effect=socket.timeout())

        with self.assertRaises(socket.timeout):
            await self.sg._make_call("POST", "/p", None, None)
        self.assertEqual(1, self.sg._http_request.await_count)

    async def test_retry_waits_without_blocking_the_loop(self):
        self.sg.config.rpc_attempt_interval = 1000
        self.sg._http_request = mock.AsyncMock(side_effect=[ssl.SSLError(), self.ok])

        with mock.patch.object(aio.asyncio, "sleep", new=mock.AsyncMock()) as sleep:
            await self.sg._make_call("POST", "/p", None, None)

        sleep.assert_awaited_once_with(1.0)

    async def test_only_the_failed_request_is_retried_not_the_whole_client(self):
        client = self.sg._get_client()
        self.sg._http_request = mock.AsyncMock(side_effect=[ssl.SSLError(), self.ok])

        await self.sg._make_call("POST", "/p", None, None)

        self.assertIs(client, self.sg._client)
        self.assertFalse(client.is_closed)
        await self.sg.close()


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestTransportErrors(unittest.IsolatedAsyncioTestCase):
    async def _raises(self, error):
        sg = make()
        sg._client = mock.Mock(request=mock.AsyncMock(side_effect=error))
        with self.assertRaises(BaseException) as ctx:
            await sg._http_request("POST", "/p", None, {})
        return ctx.exception

    async def test_timeout_becomes_socket_timeout(self):
        self.assertIsInstance(
            await self._raises(httpx.ReadTimeout("slow")), socket.timeout
        )

    async def test_ssl_error_is_unwrapped(self):
        try:
            try:
                raise ssl.SSLEOFError("eof")
            except ssl.SSLEOFError as ssl_error:
                raise httpx.ConnectError("connect failed") from ssl_error
        except httpx.ConnectError as wrapped:
            error = wrapped

        raised = await self._raises(error)

        self.assertIsInstance(raised, ssl.SSLEOFError)
        self.assertTrue(aio.AsyncShotgun._is_retryable_connection_error(raised))

    async def test_transport_error_without_os_error_cause_is_kept(self):
        raised = await self._raises(httpx.RemoteProtocolError("garbled"))
        self.assertIsInstance(raised, httpx.RemoteProtocolError)


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestServerCaps(_RpcTestCase):
    @staticmethod
    def _info(version):
        def respond(payload, i):
            if payload["method_name"] == "info":
                return 200, {"version": version}
            return 200, {"results": [{"id": 1}]}

        return respond

    async def test_concurrent_first_callers_share_one_info_request(self):
        sg = make()
        calls = []

        async def slow_info():
            calls.append(1)
            await asyncio.sleep(0.05)
            return {"version": [8, 0, 0]}

        sg.info = slow_info

        results = await asyncio.gather(*(sg.get_server_caps() for _ in range(10)))

        self.assertEqual(1, len(calls))
        self.assertTrue(all(caps is results[0] for caps in results))
        self.assertEqual((8, 0, 0), results[0].version)

    async def test_caps_are_cached(self):
        server = self.serve(self._info([8, 0, 0]))
        sg = await self.client(server)

        first = await sg.get_server_caps()

        self.assertIs(first, await sg.get_server_caps())
        self.assertEqual(["info"], server.methods)

    async def test_caps_are_fetched_again_if_the_server_changes(self):
        server = self.serve(self._info([8, 0, 0]))
        sg = await self.client(server)
        await sg.get_server_caps()

        sg.config.server = "other:1"
        sg.info = mock.AsyncMock(return_value={"version": [9, 0, 0]})

        self.assertEqual((9, 0, 0), (await sg.get_server_caps()).version)

    async def test_failed_fetch_is_not_cached(self):
        sg = make()
        sg.info = mock.AsyncMock(side_effect=[socket.timeout(), {"version": [8, 0, 0]}])

        with self.assertRaises(socket.timeout):
            await sg.get_server_caps()
        self.assertEqual((8, 0, 0), (await sg.get_server_caps()).version)

    async def test_server_too_old(self):
        sg = make()
        sg.info = mock.AsyncMock(return_value={"version": [2, 0, 0]})

        with self.assertRaises(shotgun_api3.ShotgunError):
            await sg.get_server_caps()

    async def test_server_info_needs_the_caps_first(self):
        server = self.serve(self._info([8, 0, 0]))
        sg = await self.client(server)

        with self.assertRaises(RuntimeError):
            sg.server_info

        await sg.get_server_caps()
        self.assertEqual({"version": [8, 0, 0]}, sg.server_info)

    async def test_info(self):
        server = self.serve(self._info([8, 0, 0]))
        sg = await self.client(server)

        self.assertEqual({"version": [8, 0, 0]}, await sg.info())
        self.assertEqual([], server.requests[0]["payload"]["params"])  # no auth sent

    async def test_script_auth_makes_no_info_request(self):
        server = self.serve(self._info([8, 0, 0]))
        sg = await self.client(server)

        await sg._call_rpc("read", None)

        self.assertEqual(["read"], server.methods)

    async def test_session_token_fetches_caps_once_then_sends_version_gated_param(self):
        server = self.serve(self._info([8, 0, 0]))
        sg = await self.client(
            server, script_name=None, api_key=None, session_token="tok"
        )

        await sg._call_rpc("read", None)
        await sg._call_rpc("read", None)

        self.assertEqual(["info", "read", "read"], server.methods)
        auth = server.requests[1]["payload"]["params"][0]
        self.assertEqual("tok", auth["session_token"])
        self.assertTrue(auth["reject_if_expired"])

    async def test_session_token_on_old_server_raises_before_the_call(self):
        server = self.serve(self._info([5, 2, 0]))
        sg = await self.client(
            server, script_name=None, api_key=None, session_token="tok"
        )

        with self.assertRaises(shotgun_api3.ShotgunError):
            await sg._call_rpc("read", None)

        self.assertEqual(["info"], server.methods)

    async def test_sudo_as_login_on_old_server_raises_before_the_call(self):
        server = self.serve(self._info([5, 3, 11]))
        sg = await self.client(server, sudo_as_login="someone")

        with self.assertRaises(shotgun_api3.ShotgunError):
            await sg._call_rpc("read", None)

        self.assertEqual(["info"], server.methods)


def _api(handlers):
    """A server ``respond`` that answers ``info`` and dispatches the rest by method name."""

    def respond(payload, index):
        method = payload["method_name"]
        if method == "info":
            return 200, {"version": [8, 0, 0]}
        return 200, {"results": handlers[method](payload["params"][-1])}

    return respond


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestRequests(_RpcTestCase):
    @staticmethod
    def _params(server, method):
        [request] = [
            r for r in server.requests if r["payload"]["method_name"] == method
        ]
        return request["payload"]["params"][-1]

    # find
    async def test_find(self):
        server = self.serve(
            _api({"read": lambda p: {"entities": [{"type": "Shot", "id": 1}]}})
        )
        sg = await self.client(server)

        result = await sg.find("Shot", [["code", "is", "a"]], limit=5)

        self.assertEqual([{"type": "Shot", "id": 1}], result)
        params = self._params(server, "read")
        self.assertEqual("Shot", params["type"])
        self.assertEqual(["id"], params["return_fields"])
        self.assertEqual({"entities_per_page": 5, "current_page": 1}, params["paging"])
        self.assertEqual(
            [{"path": "code", "relation": "is", "values": ["a"]}],
            params["filters"]["conditions"],
        )

    async def test_find_transforms_values_like_the_sync_client(self):
        server = self.serve(
            _api(
                {
                    "read": lambda p: {
                        "entities": [
                            {"type": "Shot", "id": 1, "at": "2020-01-02T03:04:05Z"}
                        ]
                    }
                }
            )
        )
        sg = await self.client(server)

        [shot] = await sg.find("Shot", [], fields=["at"], limit=1)

        self.assertIsInstance(shot["at"], datetime.datetime)

    async def test_find_paginates(self):
        pages = [
            {
                "entities": [{"id": 1}, {"id": 2}],
                "paging_info": {"has_next_page": True},
            },
            {"entities": [{"id": 3}], "paging_info": {"has_next_page": False}},
        ]
        seen = []

        def read(params):
            seen.append(params["paging"]["current_page"])
            return pages[len(seen) - 1]

        sg = await self.client(self.serve(_api({"read": read})))
        sg.config._records_per_page = 2

        result = await sg.find("Shot", [])

        self.assertEqual([1, 2, 3], [r["id"] for r in result])
        self.assertEqual([1, 2], seen)

    async def test_find_invalid_arguments_make_no_request(self):
        server = self.serve(_api({}))
        sg = await self.client(server)

        with self.assertRaises(ValueError):
            await sg.find("Shot", [], limit=-1)
        with self.assertRaises(shotgun_api3.ShotgunError):
            await sg.find("Shot", {}, filter_operator="all")

        self.assertEqual([], server.requests)

    async def test_find_one(self):
        server = self.serve(_api({"read": lambda p: {"entities": [{"id": 1}]}}))
        sg = await self.client(server)

        self.assertEqual({"id": 1}, await sg.find_one("Shot", []))
        self.assertEqual(1, self._params(server, "read")["paging"]["entities_per_page"])

    async def test_find_one_without_match(self):
        sg = await self.client(self.serve(_api({"read": lambda p: {"entities": []}})))

        self.assertIsNone(await sg.find_one("Shot", []))

    async def test_find_on_old_server_raises_for_unsupported_option(self):
        server = self.serve(lambda payload, i: (200, {"version": [5, 3, 13]}))
        sg = await self.client(server)

        with self.assertRaises(shotgun_api3.ShotgunError):
            await sg.find("Shot", [], include_archived_projects=False)

        self.assertEqual(["info"], server.methods)

    # create
    async def test_create(self):
        server = self.serve(
            _api({"create": lambda p: [{"type": "Shot", "id": 5, "code": "a"}]})
        )
        sg = await self.client(server)

        result = await sg.create("Shot", {"code": "a"})

        self.assertEqual({"type": "Shot", "id": 5, "code": "a"}, result)
        self.assertEqual(
            {
                "type": "Shot",
                "fields": [{"field_name": "code", "value": "a"}],
                "return_fields": ["id"],
            },
            self._params(server, "create"),
        )
        self.assertEqual(["create"], server.methods)  # no info request needed

    async def test_create_with_thumbnail_is_refused_before_any_request(self):
        for data in ({"image": "p.png"}, {"filmstrip_image": "f.png"}):
            server = self.serve(_api({"create": lambda p: [{"id": 1}]}))
            sg = await self.client(server)

            with self.assertRaises(NotImplementedError):
                await sg.create("Shot", data)

            self.assertNotIn("create", server.methods)

    # update
    async def test_update(self):
        server = self.serve(
            _api({"update": lambda p: [{"type": "Shot", "id": 5, "code": "b"}]})
        )
        sg = await self.client(server)

        result = await sg.update(
            "Shot", 5, {"code": "b"}, multi_entity_update_modes={"code": "set"}
        )

        self.assertEqual("b", result["code"])
        self.assertEqual(
            {
                "type": "Shot",
                "id": 5,
                "fields": [
                    {
                        "field_name": "code",
                        "value": "b",
                        "multi_entity_update_mode": "set",
                    }
                ],
            },
            self._params(server, "update"),
        )

    async def test_update_without_data_makes_no_request(self):
        server = self.serve(_api({}))
        sg = await self.client(server)

        self.assertEqual({"id": 5, "type": "Shot"}, await sg.update("Shot", 5, {}))
        self.assertEqual([], server.requests)

    async def test_update_with_thumbnail_is_refused_before_any_request(self):
        server = self.serve(_api({"update": lambda p: [{"id": 1, "type": "Shot"}]}))
        sg = await self.client(server)

        with self.assertRaises(NotImplementedError):
            await sg.update("Shot", 5, {"code": "b", "image": "p.png"})

        self.assertNotIn("update", server.methods)

    async def test_update_can_clear_the_image(self):
        server = self.serve(_api({"update": lambda p: [{"id": 5, "type": "Shot"}]}))
        sg = await self.client(server)

        await sg.update("Shot", 5, {"image": None})

        self.assertEqual(
            [{"field_name": "image", "value": None}],
            self._params(server, "update")["fields"],
        )

    # delete
    async def test_delete(self):
        server = self.serve(_api({"delete": lambda p: True}))
        sg = await self.client(server)

        self.assertIs(True, await sg.delete("Shot", 5))
        self.assertEqual({"type": "Shot", "id": 5}, self._params(server, "delete"))

    # batch
    async def test_batch(self):
        server = self.serve(
            _api({"batch": lambda p: [{"type": "Shot", "id": 5}, True]})
        )
        sg = await self.client(server)

        result = await sg.batch(
            [
                {
                    "request_type": "create",
                    "entity_type": "Shot",
                    "data": {"code": "a"},
                },
                {"request_type": "delete", "entity_type": "Shot", "entity_id": 3},
            ]
        )

        self.assertEqual([{"type": "Shot", "id": 5}, True], result)
        calls = self._params(server, "batch")
        self.assertEqual(["create", "delete"], [c["request_type"] for c in calls])

    async def test_batch_empty_makes_no_request(self):
        server = self.serve(_api({}))
        sg = await self.client(server)

        self.assertEqual([], await sg.batch([]))
        self.assertEqual([], server.requests)

    async def test_batch_rejects_invalid_requests_before_any_request(self):
        server = self.serve(_api({}))
        sg = await self.client(server)

        with self.assertRaises(shotgun_api3.ShotgunError):
            await sg.batch([{"request_type": "nope", "entity_type": "Shot"}])
        with self.assertRaises(shotgun_api3.ShotgunError):
            await sg.batch(({},))

        self.assertEqual([], server.requests)


class _ParityBase(_RpcTestCase):
    """
    Each scenario runs against the sync client and the async client, each with its own
    identical server. Results, errors and the requests sent must all be equal.
    """

    async def _run(self, kind, respond, operation):
        server = self.serve(respond)
        kwargs = {"script_name": "script", "api_key": "key"}
        if kind == "sync":
            sg = shotgun_api3.Shotgun(server.url, connect=False, **kwargs)
            sg.BACKOFF = 0
            sg.config.rpc_attempt_interval = 0
            self.addCleanup(sg.close)
            call = lambda: asyncio.to_thread(operation, sg)  # noqa: E731
        else:
            sg = await self.client(server)
            call = lambda: operation(sg)  # noqa: E731

        try:
            outcome = ("result", await call())
        except Exception as e:  # compared by type, message and, for http errors, status
            host = server.url.split("//")[1]  # each client has its own server and port
            outcome = (
                "error",
                type(e),
                str(e).replace(host, "HOST"),
                getattr(e, "errcode", None),
            )
        return outcome, [r["payload"] for r in server.requests]

    async def assertParity(self, respond, operation, expect_error=None):
        sync = await self._run("sync", respond, operation)
        asynchronous = await self._run("async", respond, operation)

        self.assertEqual(sync, asynchronous)
        if expect_error is None:
            self.assertEqual("result", sync[0][0], sync)
        else:
            self.assertEqual(expect_error, sync[0][1])
        return sync[0]


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestParity(_ParityBase):
    # results
    async def test_find(self):
        entities = [{"type": "Shot", "id": 1, "at": "2020-01-02T03:04:05Z"}]
        outcome = await self.assertParity(
            _api({"read": lambda p: {"entities": entities}}),
            lambda sg: sg.find("Shot", [["id", "is", 1]], fields=["at"], limit=5),
        )
        self.assertIsInstance(outcome[1][0]["at"], datetime.datetime)

    async def test_find_with_every_option(self):
        await self.assertParity(
            _api({"read": lambda p: {"entities": []}}),
            lambda sg: sg.find(
                "Shot",
                [
                    ["code", "in", ["a", "b"]],
                    ["project", "is", {"type": "Project", "id": 1}],
                ],
                fields=["code"],
                order=[{"field_name": "code", "direction": "desc"}],
                limit=3,
                retired_only=True,
                include_archived_projects=False,
            ),
        )

    async def test_find_paginated(self):
        def read(params):
            page = params["paging"]["current_page"]
            return {
                "entities": [{"type": "Shot", "id": 10 * page + i} for i in range(2)],
                "paging_info": {"has_next_page": page < 3},
            }

        outcome = await self.assertParity(
            _api({"read": read}), lambda sg: sg.find("Shot", [], page=0)
        )
        self.assertEqual(6, len(outcome[1]))

    async def test_find_one(self):
        await self.assertParity(
            _api({"read": lambda p: {"entities": [{"type": "Shot", "id": 1}]}}),
            lambda sg: sg.find_one("Shot", [], order=[{"column": "id"}]),
        )

    async def test_find_one_without_match(self):
        outcome = await self.assertParity(
            _api({"read": lambda p: {"entities": []}}),
            lambda sg: sg.find_one("Shot", []),
        )
        self.assertIsNone(outcome[1])

    async def test_create(self):
        await self.assertParity(
            _api({"create": lambda p: [{"type": "Shot", "id": 5, "code": "a"}]}),
            lambda sg: sg.create(
                "Shot", {"code": "a", "at": datetime.date(2020, 1, 2)}, ["code"]
            ),
        )

    async def test_update(self):
        await self.assertParity(
            _api({"update": lambda p: [{"type": "Shot", "id": 5, "code": "b"}]}),
            lambda sg: sg.update(
                "Shot",
                5,
                {"code": "b", "tags": [{"type": "Tag", "id": 1}]},
                {"tags": "add"},
            ),
        )

    async def test_update_without_data(self):
        await self.assertParity(_api({}), lambda sg: sg.update("Shot", 5, {}))

    async def test_delete(self):
        await self.assertParity(
            _api({"delete": lambda p: True}), lambda sg: sg.delete("Shot", 5)
        )

    async def test_batch(self):
        await self.assertParity(
            _api({"batch": lambda p: [{"type": "Shot", "id": 5}, True]}),
            lambda sg: sg.batch(
                [
                    {
                        "request_type": "create",
                        "entity_type": "Shot",
                        "data": {"code": "a"},
                    },
                    {
                        "request_type": "update",
                        "entity_type": "Shot",
                        "entity_id": 5,
                        "data": {"code": "b"},
                    },
                    {"request_type": "delete", "entity_type": "Shot", "entity_id": 5},
                ]
            ),
        )

    async def test_info(self):
        await self.assertParity(_api({}), lambda sg: sg.info())

    async def test_session_token_authentication(self):
        server_kwargs = {"session_token": "tok"}

        async def run(kind):
            read = {"entities": [], "paging_info": {"has_next_page": False}}
            server = self.serve(_api({"read": lambda p: read}))
            if kind == "sync":
                sg = shotgun_api3.Shotgun(server.url, connect=False, **server_kwargs)
                self.addCleanup(sg.close)
                await asyncio.to_thread(sg.find, "Shot", [])
            else:
                sg = aio.AsyncShotgun(server.url, **server_kwargs)
                self.addAsyncCleanup(sg.close)
                await sg.find("Shot", [])
            return [r["payload"] for r in server.requests]

        self.assertEqual(await run("sync"), await run("async"))

    # errors
    async def test_server_fault(self):
        await self.assertParity(
            lambda p, i: (200, {"exception": True, "message": "boom"}),
            lambda sg: sg.delete("Shot", 5),
            expect_error=shotgun_api3.Fault,
        )

    async def test_each_authentication_failure(self):
        errors = {
            102: shotgun_api3.AuthenticationFault,
            106: shotgun_api3.MissingTwoFactorAuthenticationFault,
            108: shotgun_api3.shotgun.UserCredentialsNotAllowedForSSOAuthenticationFault,
            110: shotgun_api3.shotgun.UserCredentialsNotAllowedForOxygenAuthenticationFault,
        }
        for code, error in errors.items():
            body = {"exception": True, "error_code": code, "message": "m"}
            await self.assertParity(
                lambda p, i, body=body: (200, body),
                lambda sg: sg.delete("Shot", 5),
                expect_error=error,
            )

    async def test_http_errors(self):
        for status in (400, 403, 404, 500, 503):
            await self.assertParity(
                lambda p, i, status=status: (status, b"page"),
                lambda sg: sg.delete("Shot", 5),
                expect_error=shotgun_api3.ProtocolError,
            )

    async def test_gateway_errors_are_retried_the_same_way(self):
        await self.assertParity(
            lambda p, i: (502, b"x") if i < 2 else (200, {"results": True}),
            lambda sg: sg.delete("Shot", 5),
        )
        await self.assertParity(
            lambda p, i: (504, b"x"),
            lambda sg: sg.delete("Shot", 5),
            expect_error=shotgun_api3.ProtocolError,
        )

    async def test_argument_errors(self):
        no_server = _api({})
        for operation in (
            lambda sg: sg.find("Shot", [], limit=-1),
            lambda sg: sg.find("Shot", [], page=-1),
            lambda sg: sg.find("Shot", {}, filter_operator="all"),
            lambda sg: sg.find("Shot", [["code"]]),
            lambda sg: sg.batch("nope"),
            lambda sg: sg.batch([{"request_type": "create"}]),
            lambda sg: sg.batch([{"request_type": "x", "entity_type": "Shot"}]),
        ):
            sync = await self._run("sync", no_server, operation)
            asynchronous = await self._run("async", no_server, operation)
            self.assertEqual(sync, asynchronous)
            self.assertEqual("error", sync[0][0])
            self.assertEqual([], sync[1])  # rejected before any request


def _generic(version=(9, 0, 0)):
    """A server that answers ``info`` with ``version`` and echoes the rpc name otherwise."""

    def respond(payload, index):
        method = payload["method_name"]
        if method == "info":
            return 200, {"version": list(version)}
        return 200, {"results": {"ok": True, "rpc": method}}

    return respond


USER = {"type": "HumanUser", "id": 1}
SHOT = {"type": "Shot", "id": 2}
PROJECT = {"type": "Project", "id": 3}

# (method name, call): every method is run on both clients and compared.
PARITY_CALLS = [
    (
        "summarize",
        lambda sg: sg.summarize(
            "Shot",
            [["id", "is", 1]],
            [{"field": "id", "type": "count"}],
            grouping=[{"field": "code", "type": "exact", "direction": "asc"}],
        ),
    ),
    (
        "summarize_without_archived_projects",
        lambda sg: sg.summarize(
            "Shot",
            [],
            [{"field": "id", "type": "count"}],
            include_archived_projects=False,
        ),
    ),
    ("revive", lambda sg: sg.revive("Shot", 2)),
    (
        "work_schedule_read",
        lambda sg: sg.work_schedule_read("2020-01-01", "2020-01-31", PROJECT, USER),
    ),
    (
        "work_schedule_update",
        lambda sg: sg.work_schedule_update(
            "2020-01-02", True, "desc", PROJECT, USER, "f"
        ),
    ),
    ("export_page", lambda sg: sg.export_page(1, "csv", "layout")),
    ("follow", lambda sg: sg.follow(USER, SHOT)),
    ("unfollow", lambda sg: sg.unfollow(USER, SHOT)),
    ("followers", lambda sg: sg.followers(SHOT)),
    ("following", lambda sg: sg.following(USER, PROJECT, "Shot")),
    ("following_defaults", lambda sg: sg.following(USER)),
    ("schema_entity_read", lambda sg: sg.schema_entity_read()),
    ("schema_entity_read_project", lambda sg: sg.schema_entity_read(PROJECT)),
    ("schema_read", lambda sg: sg.schema_read()),
    ("schema_read_project", lambda sg: sg.schema_read(PROJECT)),
    ("schema_field_read", lambda sg: sg.schema_field_read("Shot")),
    (
        "schema_field_read_field",
        lambda sg: sg.schema_field_read("Shot", "code", PROJECT),
    ),
    (
        "schema_field_create",
        lambda sg: sg.schema_field_create(
            "Shot", "text", "Display", {"summary_default": "none"}
        ),
    ),
    (
        "schema_field_update",
        lambda sg: sg.schema_field_update(
            "Shot", "sg_x", {"description": "d"}, PROJECT
        ),
    ),
    ("schema_field_delete", lambda sg: sg.schema_field_delete("Shot", "sg_x")),
    ("nav_expand", lambda sg: sg.nav_expand("/p", {"a": 1}, {"b": 2})),
    ("nav_search_string", lambda sg: sg.nav_search_string("/p", "abc", {"a": 1})),
    ("nav_search_entity", lambda sg: sg.nav_search_entity("/p", SHOT, {"a": 1})),
    ("preferences_read", lambda sg: sg.preferences_read(["a", "b"])),
    ("preferences_read_defaults", lambda sg: sg.preferences_read()),
    ("user_subscriptions_read", lambda sg: sg.user_subscriptions_read()),
    (
        "user_subscriptions_create",
        lambda sg: sg.user_subscriptions_create(
            [{"user": USER, "subscriptions": ["a"]}]
        ),
    ),
    ("custom_entity_read", lambda sg: sg.custom_entity_read("CustomEntity01")),
    ("custom_entity_enable", lambda sg: sg.custom_entity_enable("CustomEntity01")),
    (
        "custom_entity_configure",
        lambda sg: sg.custom_entity_configure("CustomEntity01", "Name", {"a": True}),
    ),
    (
        "custom_entity_disable",
        lambda sg: sg.custom_entity_disable("CustomEntity01", True),
    ),
    ("note_thread_read", lambda sg: sg.note_thread_read(5, {"Note": ["subject"]})),
    (
        "text_search",
        lambda sg: sg.text_search("foo", {"Shot": [["id", "is", 1]]}, [1], 5),
    ),
    (
        "activity_stream_read",
        lambda sg: sg.activity_stream_read("Shot", 2, {"Note": ["subject"]}, 1, 9, 5),
    ),
]

# (name, version, call) that a server that is too old must refuse.
PARITY_VERSION_GATES = [
    (
        "summarize",
        (5, 3, 13),
        lambda sg: sg.summarize("Shot", [], [], include_archived_projects=False),
    ),
    (
        "work_schedule_read",
        (3, 1, 9),
        lambda sg: sg.work_schedule_read("2020-01-01", "2020-01-31"),
    ),
    (
        "work_schedule_update",
        (3, 1, 9),
        lambda sg: sg.work_schedule_update("2020-01-01", True),
    ),
    ("follow", (5, 1, 21), lambda sg: sg.follow(USER, SHOT)),
    ("unfollow", (5, 1, 21), lambda sg: sg.unfollow(USER, SHOT)),
    ("followers", (5, 1, 21), lambda sg: sg.followers(SHOT)),
    ("following", (7, 0, 11), lambda sg: sg.following(USER)),
    ("schema_read_project", (5, 4, 3), lambda sg: sg.schema_read(PROJECT)),
    (
        "schema_entity_read_project",
        (5, 4, 3),
        lambda sg: sg.schema_entity_read(PROJECT),
    ),
    (
        "schema_field_read_project",
        (5, 4, 3),
        lambda sg: sg.schema_field_read("Shot", None, PROJECT),
    ),
    ("preferences_read", (7, 9, 9), lambda sg: sg.preferences_read()),
    (
        "custom_entity_read",
        (8, 90, 9),
        lambda sg: sg.custom_entity_read("CustomEntity01"),
    ),
    (
        "custom_entity_enable",
        (8, 90, 9),
        lambda sg: sg.custom_entity_enable("CustomEntity01"),
    ),
    (
        "custom_entity_configure",
        (8, 90, 9),
        lambda sg: sg.custom_entity_configure("CustomEntity01"),
    ),
    (
        "custom_entity_disable",
        (8, 90, 9),
        lambda sg: sg.custom_entity_disable("CustomEntity01"),
    ),
    ("note_thread_read", (6, 1, 9), lambda sg: sg.note_thread_read(5)),
    ("text_search", (6, 1, 9), lambda sg: sg.text_search("foo", {})),
    ("activity_stream_read", (6, 1, 9), lambda sg: sg.activity_stream_read("Shot", 2)),
]

PARITY_ARGUMENT_ERRORS = [
    ("summarize_grouping", lambda sg: sg.summarize("Shot", [], [], grouping="x")),
    (
        "work_schedule_read_dates",
        lambda sg: sg.work_schedule_read(20200101, "2020-01-31"),
    ),
    ("work_schedule_update_date", lambda sg: sg.work_schedule_update(20200101, True)),
    ("note_thread_read_fields", lambda sg: sg.note_thread_read(5, entity_fields=["x"])),
    ("text_search_entity_types", lambda sg: sg.text_search("foo", ["x"])),
    ("text_search_filters", lambda sg: sg.text_search("foo", {"Shot": "x"})),
    (
        "activity_stream_fields",
        lambda sg: sg.activity_stream_read("Shot", 2, entity_fields=["x"]),
    ),
]


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestMoreMethodsParity(_ParityBase):
    async def test_every_method_matches_the_sync_client(self):
        for name, call in PARITY_CALLS:
            with self.subTest(name):
                await self.assertParity(_generic(), call)

    async def test_user_subscriptions_create_reports_success_like_the_sync_client(self):
        for body, expected in (
            ({"status": "success"}, True),
            ({"status": "failure"}, False),
            ("garbage", False),
        ):
            with self.subTest(body=body):
                outcome = await self.assertParity(
                    lambda p, i, body=body: (
                        (200, {"version": [9, 0, 0]})
                        if p["method_name"] == "info"
                        else (200, {"results": body})
                    ),
                    lambda sg: sg.user_subscriptions_create([]),
                )
                self.assertEqual(expected, outcome[1])

    async def test_requests_send_the_arguments_the_sync_client_sends(self):
        # Spot-check one payload so equality above cannot be two equally wrong requests.
        _, payloads = await self._run(
            "async", _generic(), lambda sg: sg.follow(USER, SHOT)
        )

        self.assertEqual("follow", payloads[-1]["method_name"])
        self.assertEqual({"user": USER, "entity": SHOT}, payloads[-1]["params"][-1])

    async def test_old_servers_are_refused_the_same_way(self):
        for name, version, call in PARITY_VERSION_GATES:
            with self.subTest(name):
                await self.assertParity(
                    _generic(version), call, expect_error=shotgun_api3.ShotgunError
                )

    async def test_gated_calls_are_refused_before_the_rpc(self):
        for name, version, call in PARITY_VERSION_GATES:
            with self.subTest(name):
                _, payloads = await self._run("async", _generic(version), call)
                self.assertEqual(["info"], [p["method_name"] for p in payloads])

    async def test_argument_errors_match_and_send_nothing(self):
        for name, call in PARITY_ARGUMENT_ERRORS:
            with self.subTest(name):
                sync = await self._run("sync", _generic(), call)
                asynchronous = await self._run("async", _generic(), call)

                self.assertEqual(sync, asynchronous)
                self.assertEqual("error", sync[0][0])
                self.assertEqual(
                    [], [p for p in sync[1] if p["method_name"] != "info"]
                )  # nothing but the version check was sent


UNSUPPORTED = (
    "upload",
    "upload_thumbnail",
    "upload_filmstrip_thumbnail",
    "share_thumbnail",
    "download_attachment",
    "get_attachment_download_url",
    "get_auth_cookie_handler",
    "get_session_token",
    "authenticate_human_user",
    "update_project_last_accessed",
)
# Deprecated: they only raise an error telling to use something else.
DELIBERATELY_ABSENT = {"schema", "entity_types"}


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestUnsupported(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _public(cls):
        return {
            n for n in dir(cls) if not n.startswith("_") and callable(getattr(cls, n))
        }

    def test_every_sync_method_is_either_supported_or_listed(self):
        """A new Shotgun method must be ported, or added to the lists above on purpose."""
        missing = self._public(shotgun_api3.Shotgun) - self._public(aio.AsyncShotgun)

        self.assertEqual(DELIBERATELY_ABSENT, missing)

    def test_the_only_async_additions_are_the_awaitable_caps(self):
        extra = self._public(aio.AsyncShotgun) - self._public(shotgun_api3.Shotgun)

        self.assertEqual({"get_server_caps"}, extra)

    def test_unsupported_methods_say_so_without_touching_the_network(self):
        sg = make()
        forbidden = mock.Mock(side_effect=AssertionError("network call"))
        with mock.patch.object(socket.socket, "connect", forbidden), mock.patch(
            "urllib.request.urlopen", forbidden
        ), mock.patch.object(httpx.AsyncClient, "request", forbidden):
            for name in UNSUPPORTED:
                with self.subTest(name):
                    with self.assertRaises(NotImplementedError) as ctx:
                        getattr(sg, name)("a", b="c")
                    self.assertIn("AsyncShotgun.%s()" % name, str(ctx.exception))
                    self.assertIn("Shotgun.%s()" % name, str(ctx.exception))
        forbidden.assert_not_called()

    def test_unsupported_methods_fail_when_called_not_when_awaited(self):
        with self.assertRaises(NotImplementedError):
            make().upload("Shot", 1, "/some/file")  # no await needed to learn it

    def test_unsupported_methods_are_documented_as_such(self):
        for name in UNSUPPORTED:
            self.assertIn("Not supported yet", getattr(aio.AsyncShotgun, name).__doc__)
            self.assertEqual(name, getattr(aio.AsyncShotgun, name).__name__)

    async def test_connect(self):
        server = _RpcServer(_api({}))
        self.addCleanup(server.stop)
        sg = aio.AsyncShotgun(server.url, "script", "key")
        self.addAsyncCleanup(sg.close)

        await sg.connect()

        self.assertEqual(["info"], server.methods)

    async def test_connect_reports_a_bad_connection(self):
        server = _RpcServer(_api({}))
        sg = aio.AsyncShotgun(server.url, "script", "key")
        self.addAsyncCleanup(sg.close)
        server.stop()

        with self.assertRaises(ConnectionRefusedError):
            await sg.connect()


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestConcurrency(_RpcTestCase):
    DELAY = 0.15  # how long the server takes to answer a read

    def _echo_server(self):
        """A server whose ``read`` answers slowly with the id it was asked for."""

        def read(params):
            time.sleep(self.DELAY)
            wanted = params["filters"]["conditions"][0]["values"][0]
            return {
                "entities": [{"type": "Shot", "id": wanted}],
                "paging_info": {"has_next_page": False},
            }

        return self.serve(_api({"read": read}))

    @staticmethod
    def _find(sg, shot_id):
        return sg.find("Shot", [["id", "is", shot_id]], limit=1)

    async def test_requests_overlap_and_results_stay_independent(self):
        server = self._echo_server()
        sg = await self.client(server, max_connections=20)
        await sg.get_server_caps()
        count = 20

        started = time.monotonic()
        results = await asyncio.gather(*(self._find(sg, i) for i in range(count)))
        elapsed = time.monotonic() - started

        self.assertEqual([[{"type": "Shot", "id": i}] for i in range(count)], results)
        self.assertGreaterEqual(server.max_inflight, count // 2)
        self.assertLess(elapsed, count * self.DELAY / 2)  # sequential would take 3s

    async def test_connection_limit_is_honored(self):
        server = self._echo_server()
        sg = await self.client(server, max_connections=3)
        await sg.get_server_caps()

        results = await asyncio.gather(*(self._find(sg, i) for i in range(12)))

        self.assertEqual(list(range(12)), [r[0]["id"] for r in results])
        self.assertLessEqual(server.max_inflight, 3)
        self.assertEqual(3, server.max_inflight)  # and it did use all of them
        self.assertLessEqual(server.connections, 3)  # kept alive and reused

    async def test_event_loop_stays_responsive(self):
        server = self._echo_server()
        sg = await self.client(server, max_connections=5)
        await sg.get_server_caps()
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        task = asyncio.create_task(ticker())
        await asyncio.gather(*(self._find(sg, i) for i in range(5)))
        task.cancel()

        # The requests took about DELAY seconds; a blocked loop would have ticked ~0 times.
        self.assertGreaterEqual(ticks, 5)

    async def test_one_failure_does_not_disturb_the_others(self):
        def read(params):
            wanted = params["filters"]["conditions"][0]["values"][0]
            if wanted == 3:
                return None  # becomes a server fault below
            return {
                "entities": [{"id": wanted}],
                "paging_info": {"has_next_page": False},
            }

        def respond(payload, index):
            if payload["method_name"] == "info":
                return 200, {"version": [8, 0, 0]}
            result = read(payload["params"][-1])
            if result is None:
                return 200, {"exception": True, "message": "boom"}
            return 200, {"results": result}

        sg = await self.client(self.serve(respond), max_connections=5)

        results = await asyncio.gather(
            *(self._find(sg, i) for i in range(6)), return_exceptions=True
        )

        self.assertIsInstance(results[3], shotgun_api3.Fault)
        self.assertEqual(
            [0, 1, 2, 4, 5], [r[0]["id"] for i, r in enumerate(results) if i != 3]
        )

    async def test_close_while_idle_then_keep_using(self):
        server = self._echo_server()
        sg = await self.client(server)

        await self._find(sg, 1)
        await sg.close()
        self.assertEqual([{"type": "Shot", "id": 2}], await self._find(sg, 2))


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@unittest.skipIf(httpx is None, "httpx is not installed")
class TestDocumentation(unittest.TestCase):
    def test_the_documented_example_runs_as_written(self):
        with open(os.path.join(ROOT, "docs", "advanced", "async.rst")) as f:
            text = f.read()
        block = re.search(
            r"\.\. code-block:: python\n\n((?:    .*\n|\n)+)", text
        ).group(1)
        code = "\n".join(line[4:] for line in block.split("\n"))

        entities = {"entities": [{"type": "Shot", "id": 1, "code": "a"}]}

        def read(params):
            time.sleep(0.02)  # slow enough for concurrent requests to overlap
            return entities

        server = _RpcServer(_api({"read": read}))
        self.addCleanup(server.stop)
        code = code.replace("https://yoursite.shotgrid.autodesk.com", server.url)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(code, "async.rst", "exec"), {"__name__": "__main__"})

        self.assertEqual("100 shots\n", output.getvalue())
        self.assertEqual(100, server.methods.count("read"))
        self.assertGreater(server.max_inflight, 1)  # the requests really ran together
        self.assertLessEqual(
            server.max_inflight, 10
        )  # max_connections=10 in the example


class TestOptionalImport(unittest.TestCase):
    @unittest.skipIf(httpx is None, "httpx is not installed")
    def test_exported_when_httpx_is_installed(self):
        self.assertIs(aio.AsyncShotgun, shotgun_api3.AsyncShotgun)

    def _run_without_httpx(self, code):
        # A fresh interpreter in which importing httpx fails, installed or not.
        prelude = (
            "import sys; sys.path.insert(0, %r); sys.modules['httpx'] = None\n" % ROOT
        )
        return subprocess.run(
            [sys.executable, "-c", prelude + code], capture_output=True, text=True
        )

    def test_package_imports_without_httpx(self):
        result = self._run_without_httpx(
            "import shotgun_api3\n"
            "sg = shotgun_api3.Shotgun('http://s', 'n', 'k', connect=False)\n"
            "print('sync ok')\n"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("sync ok", result.stdout)

    def test_using_the_async_client_without_httpx_names_the_extra(self):
        result = self._run_without_httpx(
            "import shotgun_api3\n"
            "try:\n"
            "    shotgun_api3.AsyncShotgun\n"
            "except ImportError as e:\n"
            "    print(e)\n"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("pip install shotgun_api3[async]", result.stdout)

    def test_from_import_without_httpx_names_the_extra(self):
        result = self._run_without_httpx("from shotgun_api3 import AsyncShotgun\n")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("ImportError", result.stderr)
        self.assertIn("pip install shotgun_api3[async]", result.stderr)

    def test_unknown_attributes_still_raise_attribute_error(self):
        result = self._run_without_httpx(
            "import shotgun_api3\n"
            "try:\n"
            "    shotgun_api3.nope\n"
            "except AttributeError as e:\n"
            "    print('AttributeError', e)\n"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("AttributeError", result.stdout)


if __name__ == "__main__":
    unittest.main()
