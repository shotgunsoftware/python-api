# Design

## Context

See proposal.md for motivation. Current state of `shotgun_api3/shotgun.py`:

- Nearly every public method (~55) goes through `_call_rpc`, which does PREPARE (transform, build payload, encode), SEND (`_make_call` retry loop then `_http_request` over vendored httplib2, blocking) and FINISH (status parse, decode, error mapping, inbound transform, results unwrap).
- PREPARE is not fully pure: `_build_payload` calls `_auth_params`, which reads the `server_caps` property. That property lazily calls `info()` over the network. `server_caps` is also read at about 53 sites for server-version gates.
- Two retry loops exist, both with `time.sleep`: SSL errors in `_make_call`, and 502/504 in `_call_rpc`.
- A single shared `KeepaliveHttp` connection with an idle-staleness check (`max_connection_idle_secs`) is not thread-safe.
- The package has no runtime dependencies and vendors its libraries.
- Uploads (`_send_form`) and downloads (`download_attachment`) bypass `_call_rpc` and use urllib.

## Goals / Non-Goals

**Goals:**
- Share all non-I/O logic between sync and async clients so results and errors cannot drift.
- Leave the sync client's behavior and public interface untouched.
- Keep httpx an opt-in dependency.

**Non-Goals:**
- Making the existing `Shotgun` class async or hybrid. Python has no async properties, and a sync/async hybrid breaks sync callers.
- Async uploads, downloads and Mockgun (deferred).
- Replacing httplib2 in the sync client.

## Decisions

### D1: Two classes over a shared sync-agnostic core (option B)
Extract `_SGCore` (`shotgun_api3/_core.py`) holding the pure logic: `_transform_*`, `_visit_data`, `_encode_payload`, `_decode_response`, `_response_errors`, `_parse_http_status`, `_auth_params(caps)`, `_build_payload(..., caps)`, and per-method `_build_X_params` and `_finish_X(result)` pairs. `Shotgun(_SGCore)` keeps its transport. `AsyncShotgun(_SGCore)` adds an httpx transport.

Alternatives: a thread wrapper (`asyncio.to_thread`) is not real async and the shared httplib2 connection is not thread-safe; async-first with generated sync code (`unasync`) adds a build step and risks sync drift; duplicating the class means two codebases to maintain.

#### D1a: Hybrid method sharing (build/prepare pairs, plus one generator for `find`)
Most methods are "validate, build params, one RPC, post-process", so the core exposes `_build_X`/`_prepare_X` builders and each client does its own RPC. `find` is the exception: its pagination loop decides from each response whether to fetch the next page, and interleaves `server_caps` checks. It is written once in the core as a generator (`_find_flow`) that yields `NEED_CAPS` to request server capabilities and `("read", params)` to request an RPC. The sync client drives it with blocking calls (`_run_flow`) and the async client with `await`. Alternative considered: generators for every method; rejected because it rewrites all ~55 sync methods and risks the "sync unchanged" guarantee.

Where the sync client must stay lazy about caps (it only fetched `info()` when a gate was reached), core helpers take `caps=None` and raise `_ServerCapsRequired`; the sync `_with_caps` wrapper resolves it. The async client resolves caps eagerly (`await get_server_caps()`, cached), so it has no such wrapper. `_parse_records` follows this pattern; the pre-3.3.0 server thumbnail-URL fallback (`_build_thumb_url`, a network call) is not supported by the async client.

The `SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION` flag and the filter-translation helpers move to `_core.py` (the flag's single owner), so the core stays free of an import cycle with `shotgun.py`. `Shotgun.__init__` sets the flag there; tests patch `shotgun_api3._core.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION`. The documented knob (the environment variable) is unchanged.

### D2: Pass server capabilities into the pure core, lazily
`_auth_params` and `_build_payload` take an optional `caps` argument instead of reading the `server_caps` property. Caps are needed only on version-gated paths (session-token auth and `sudo_as_login`), so they are NOT passed eagerly: reading `server_caps` costs an `info()` round trip, and doing it on every request would add a request for every script-auth client and recurse for `info()` itself. Instead the core raises an internal `_ServerCapsRequired` when it reaches a gate without `caps`. The sync `Shotgun._auth_params` catches it and retries with `self.server_caps` (same lazy, cached behavior as before). The async class catches it, awaits `get_server_caps()` and retries with the result. This removes the hidden I/O from PREPARE so the core is truly pure.

Alternatives: always passing `caps` (extra request and recursion, see above); a lazy callable argument (cannot await inside a sync callable).

### D3: Explicit `await sg.get_server_caps()`
No awaitable property. An explicit method works with linters and type checkers and avoids silent "never awaited" bugs. Guard with an `asyncio.Lock` and cache so concurrent first callers cause one `info()` request. Re-fetch if `config.server` changes, as the sync property does.

### D4: httpx as an optional extra
`extras_require={"async": ["httpx"]}`. `AsyncShotgun` lives in `shotgun_api3/aio.py`, which imports httpx at module top. `shotgun_api3/__init__.py` exports it only if that import succeeds, so `import shotgun_api3` never needs httpx and no function-local imports are used. Accessing it without the extra raises an error naming the `async` extra.

Alternative: aiohttp is lighter at very high concurrency, but its proxy and SSL handling is more awkward.

### D5: Async twins of both retry loops
`_make_call` (SSL retry) and the 502/504 loop each get an async version using `asyncio.sleep`. The decision logic (which errors retry, how many attempts, backoff formula) is factored into the core as small helpers so only the loop and sleep are duplicated.

### D6: Connection management maps onto httpx
One `httpx.AsyncClient` per `AsyncShotgun`, configured from `_Config`: `timeout_secs` to timeout, `ca_certs` to `verify`, proxy settings to `proxy`, `max_connection_idle_secs` to `keepalive_expiry`, and a new concurrency setting to `limits`. The sync `_is_connection_stale` logic is not ported. Lifecycle through `async with` and `await close()`.

### D7: Sync/async parity enforced by tests
Shared test cases run against both clients through a thin adapter, so equal results and errors are asserted rather than assumed.

### Spike results (httpx 0.28.1)

- `ca_certs`: the library holds a CA bundle file path. Pass `verify=ssl.create_default_context(cafile=path)`. A self-signed server is accepted with it and rejected (`ConnectError`) without it. Passing a path string directly to `verify=` is deprecated in httpx, so build the context.
- Proxy: `proxy="http://user:pass@host:port"` sends `Proxy-Authorization: Basic ...` on both plain forwarding and `CONNECT` (https). Credentials MUST be percent-encoded when building the URL (`urllib.parse.quote(..., safe="")`); a `@` in a password was decoded correctly once encoded.
- Timeout: `timeout=secs` raises `httpx.ReadTimeout` after about `secs`. httpx timeouts are per phase (connect, read, write, pool), like httplib2's per-operation socket timeout, so the semantics are close but not identical to a total deadline. The async client SHALL map httpx timeout exceptions to the error the sync client raises for socket timeouts.
- Keepalive: `limits=httpx.Limits(keepalive_expiry=N)` reuses a connection idle for less than N seconds and replaces one idle for longer. Mapping gotcha: the sync client treats a falsy `max_connection_idle_secs` (0 or None) as "never expire", whereas httpx treats `keepalive_expiry=0` as "never reuse" and only `None` as "never expire". Map with `keepalive_expiry = max_idle or None`.

### Implementation notes (from building the async transport)

- `AsyncShotgun` derives from a shared `_SGClient` base (config validation and setup, `_split_url`, `_get_certs_file`, user-agent methods, `_call_headers`) so the constructor arguments and validation are identical to `Shotgun`. `auth_token` (2FA) is not supported yet: switching to a session token needs an awaited RPC, which a constructor can't do.
- The concurrency limit is `max_connections`, default 10 (conservative; httpx's own default is 100). It also sets `max_keepalive_connections`.
- The sync client closes its single connection when a call fails. The async client does not: its connections are shared by concurrent requests, httpx already discards a connection that failed, and closing the client would abort other tasks' in-flight requests. Only the failed request is retried.
- Transport errors are unwrapped to the innermost `OSError` (for example `ssl.SSLCertVerificationError` or `ConnectionRefusedError`) and httpx timeouts become `socket.timeout`, so error types and the retry predicate match the sync client.
- Not ported yet: `update_project_last_accessed` (calls `find_one` partway through, so it needs a flow like `find`), and `get_session_token` and `authenticate_human_user`. The last one swaps the client's credentials around a request, which would corrupt the authentication of requests running at the same time, so it is deliberately left out. `schema` and `entity_types` only raise deprecation errors and are not ported.
- Redirects are not followed (httpx default), as httplib2 does not follow a redirected POST by default either; a 3xx response raises `ProtocolError` like any status of 300 or above.

## Risks / Trade-offs

- [Core extraction regresses the sync client] → Do it as its own phase and PR with no behavior change; require the existing suite green before any async work.
- [Sync and async drift in the duplicated I/O pieces] → Keep the I/O pieces minimal, share the decision logic (D5), and run the parity tests (D7).
- [httpx does not honor `ca_certs`, proxy auth or timeout semantics the same way httplib2 does] → Spike before the async transport phase; document any differences.
- [Keepalive semantics differ from `max_connection_idle_secs`] → Spike the mapping; accept httpx semantics if they cover the stale-connection failure mode.
- [Version gates missed at some of the ~53 `server_caps` sites] → Pass `caps` explicitly, so a missed site is a type or call error instead of a silent skip; cover with a version-gate test per gated method.
- [Unbounded fan-out opens too many sockets] → Default connection limit, configurable.

## Migration Plan

Additive release; sync users need no change. Phase 1 (core extraction) ships behavior-neutral. Async ships behind the optional extra. Rollback is not installing the extra, or reverting the async phases, since the sync path depends only on the core.

## Open Questions

None. (`AsyncShotgun` is exported from the package root when httpx is installed, and always importable as `shotgun_api3.aio.AsyncShotgun`.)
