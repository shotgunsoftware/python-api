# Tasks

## 1. Spikes

- [x] 1.1 Write a throwaway script showing httpx honors `ca_certs`, proxy host/port/auth and `timeout_secs` against a test server; record any differences from httplib2 in design.md
- [x] 1.2 Verify `max_connection_idle_secs` maps onto httpx `keepalive_expiry` (idle connection is dropped and re-opened rather than reused); record the result in design.md

## 2. Core extraction (no behavior change)

- [x] 2.1 Create `shotgun_api3/_core.py` with `_SGCore`; move the pure helpers (`_transform_*`, `_visit_data`, `_encode_payload`, `_decode_response`, `_json_loads`, `_response_errors`, `_parse_http_status`); verify the existing test suite passes unchanged
- [x] 2.2 Change `_auth_params` and `_build_payload` to take `caps` as an argument (lazily, via `_ServerCapsRequired`, see design D2); verify the existing suite passes and a unit test covers each version gate (session token, `sudo_as_login`)
- [x] 2.3 Factor retry decisions (which SSL errors retry, 502/504 backoff formula) into core helpers; verify existing retry tests pass and new unit tests cover the helpers
- [x] 2.4 Move the pure helpers (filter translation, entity-optimization flag, record parsing, param builders) into the core; give `create`, `update` and `batch` shared prepare/build helpers and `find` a shared generator flow (design D1a); `info`, `find_one` and `delete` need no shared helper. Verify the existing suite passes unchanged and new unit tests cover the helpers and the `find` flow

## 3. Async transport

- [x] 3.1 Add `extras_require={"async": ["httpx"]}` in `setup.py`; verify `pip install .[async]` installs httpx and a plain install does not
- [x] 3.2 Create `shotgun_api3/aio.py` with `AsyncShotgun`: config handling, `httpx.AsyncClient` built from `_Config` (verify, proxy, timeout, keepalive, connection limit), `async with` and `await close()`; verify a lifecycle test shows connections are closed on exit
- [x] 3.3 Implement the async `_make_call` and 502/504 loop with `asyncio.sleep`, using the core retry helpers; verify tests for success after one 502, SSL retry, and retries exhausted
- [x] 3.4 Implement `await get_server_caps()` with an `asyncio.Lock` and cache; verify a test shows concurrent first calls send one `info()` request
- [x] 3.5 Conditionally export `AsyncShotgun` from `shotgun_api3/__init__.py` and raise an error naming the `async` extra when httpx is missing; verify both import cases with tests

## 4. Async core methods

- [x] 4.1 Add async `info`, `find`, `find_one`, `create`, `update`, `delete` and `batch` built on the shared core helpers and `find` flow; verify each with a test
- [x] 4.2 Add an async test base and parity adapter that runs shared cases against both clients; verify find, create, update, delete and error cases produce equal results and error types
- [x] 4.3 Add a concurrency test: many parallel finds on one client overlap in time, honor the connection limit, and leave the event loop responsive
- [x] 4.4 Document `AsyncShotgun` usage, install extra and the deferred upload/download/Mockgun scope in `docs/` and `HISTORY.rst`; verify the documented example runs as written

## 5. Remaining methods

- [x] 5.1 Add async versions of the schema, follow/unfollow, activity stream, preferences, subscriptions, work schedule and custom-entity methods using the shared prepare helpers; verify each has a parity test. (Not ported, see design: `update_project_last_accessed`, `get_session_token`, `authenticate_human_user`.)
- [x] 5.2 Make unsupported upload and download operations absent or raise a clear not-supported error on `AsyncShotgun`; verify a test that no blocking network call is made

## 6. Integration check

- [x] 6.1 Run the full sync suite and the full async parity suite together; verify both pass and the sync client's public interface is unchanged
