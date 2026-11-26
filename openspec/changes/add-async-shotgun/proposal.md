# Proposal

## Why

The Python API is sync-only and built on a blocking, vendored httplib2 transport. Callers that need many concurrent requests (for example, hundreds of parallel reads) must use threads, and the shared `Shotgun` connection is not thread-safe. An async client gives real concurrent throughput without changing how existing sync users work.

## What Changes

- Add an `AsyncShotgun` client in `shotgun_api3/aio.py`, built on `httpx.AsyncClient`, alongside the existing `Shotgun` class.
- Extract the pure, sync-agnostic logic from `Shotgun` into a shared core (`_SGCore`) used by both clients: payload building, response decoding, error mapping, data transforms, and per-method param and result builders. No change in sync behavior.
- Server capabilities become an explicit `await sg.get_server_caps()` on the async client, guarded so concurrent first calls trigger one `info()` request.
- Provide async equivalents of both retry loops (SSL errors, 502/504 responses) using `asyncio.sleep`.
- Support `async with AsyncShotgun(...)` and `await sg.close()`, with a configurable concurrency limit.
- Ship httpx as an optional extra: `shotgun_api3[async]`. Importing `shotgun_api3` does not require httpx.
- Phased rollout: core extraction, then core CRUD methods, then the remaining methods.

Out of scope for now:

- Async uploads and downloads (`_send_form`, `download_attachment`).
- Async Mockgun.

## Capabilities

### New Capabilities
- `async-client`: an asyncio-based client exposing the API's request methods with the same results and errors as the sync client, plus lifecycle management, concurrency limits and explicit server-capability access.

### Modified Capabilities

None. Existing sync behavior does not change.

## Impact

- Code: `shotgun_api3/shotgun.py` (core extraction), new `shotgun_api3/_core.py` and `shotgun_api3/aio.py`, `shotgun_api3/__init__.py` (conditional export).
- Dependencies: optional `httpx` through `extras_require={"async": [...]}` in `setup.py`. Python 3.9 floor is unchanged.
- Tests: new async test base alongside the live-server `tests/base.py`. The existing suite must stay green after the core extraction.
- Docs and release notes: document `AsyncShotgun` and the install extra.
