# Spec Delta

## Purpose

Lets callers issue many concurrent requests to the server from asyncio code, with the same results and errors as the existing synchronous client.

## ADDED Requirements

### Requirement: Async client is optional
The package SHALL provide an asyncio-based client that is available only when the `async` install extra is present. Importing the package without that extra MUST NOT fail.

#### Scenario: Package imported without the extra
- **WHEN** the package is imported in an environment without the async HTTP dependency
- **THEN** the import succeeds and the synchronous client is fully usable

#### Scenario: Async client used without the extra
- **WHEN** a caller tries to use the async client without the async HTTP dependency installed
- **THEN** the caller receives an error naming the `async` install extra

### Requirement: Same configuration as the sync client
The async client SHALL accept the same connection and authentication settings as the sync client: server URL, script, user or session credentials, proxy, CA certificates, timeouts and retry settings.

#### Scenario: Script authentication
- **WHEN** an async client is created with a script name and key
- **THEN** requests authenticate as that script

#### Scenario: Proxy configured
- **WHEN** an async client is created with a proxy server, port and credentials
- **THEN** requests are sent through that proxy

### Requirement: Request methods return the same results as the sync client
For each supported request method, the async client SHALL return a result equal to the sync client's for the same inputs and server state, including date, time and timezone handling.

#### Scenario: Find parity
- **WHEN** the same find call is made with the sync and async clients against the same data
- **THEN** both return equal records with identically typed field values

#### Scenario: Create then read
- **WHEN** a record is created with the async client and then read back
- **THEN** the returned fields match the values that were sent, after server-side normalization

### Requirement: Errors match the sync client
The async client SHALL raise the same error types as the sync client for authentication failures, server faults and non-success HTTP statuses.

#### Scenario: Bad credentials
- **WHEN** a request is made with invalid script credentials
- **THEN** the same authentication error type as the sync client is raised

#### Scenario: Server fault
- **WHEN** the server returns an exception payload
- **THEN** the same fault error type as the sync client is raised, with the server's message

### Requirement: Requests run concurrently
The async client SHALL allow multiple requests in flight at once from a single client instance without blocking the event loop.

#### Scenario: Parallel reads
- **WHEN** a caller awaits many find calls together on one client
- **THEN** the calls overlap in time and all complete with correct, independent results

#### Scenario: Event loop stays responsive
- **WHEN** a request is waiting on the network
- **THEN** other tasks on the same event loop continue to run

### Requirement: Concurrency is bounded
The async client SHALL limit the number of simultaneous connections to a configurable maximum, queuing excess requests instead of opening more connections.

#### Scenario: More requests than the limit
- **WHEN** more concurrent requests are issued than the configured limit
- **THEN** no more than the limit are in flight at once and all eventually complete

### Requirement: Transient failures are retried
The async client SHALL retry the same transient failures as the sync client (SSL connection errors up to the configured attempt count, and 502 and 504 responses with increasing backoff) without blocking the event loop while waiting.

#### Scenario: Gateway error then success
- **WHEN** the server returns 502 once and then succeeds
- **THEN** the request is retried after a delay and returns the successful result

#### Scenario: Retries exhausted
- **WHEN** a transient failure persists through all allowed attempts
- **THEN** the final error is raised to the caller

### Requirement: Server capabilities are explicit
The async client SHALL expose server capabilities through an awaitable method, and concurrent first callers MUST trigger at most one capability request to the server. Requests that depend on a server version MUST enforce the same minimum-version checks as the sync client.

#### Scenario: Concurrent first use
- **WHEN** several requests that need server capabilities start at the same time on a new client
- **THEN** the server receives a single capabilities request and all callers get the same result

#### Scenario: Unsupported server version
- **WHEN** an option requires a newer server version than the connected server supports
- **THEN** the same error as the sync client is raised

### Requirement: Client lifecycle is managed
The async client SHALL support use as an async context manager and an explicit awaitable close, and SHALL release its connections on close.

#### Scenario: Context manager exit
- **WHEN** the async context block exits
- **THEN** all connections are closed

#### Scenario: Explicit close
- **WHEN** the caller awaits close on the client
- **THEN** all connections are closed

### Requirement: Sync client behavior is unchanged
Introducing the async client MUST NOT change the sync client's public interface, results, errors or retry behavior.

#### Scenario: Existing sync usage
- **WHEN** existing code uses the sync client after this change
- **THEN** it behaves exactly as before and the existing test suite passes unchanged

### Requirement: Unsupported operations fail clearly
Operations deferred from the first release (file uploads and downloads, and the methods that rely on swapping credentials or on a nested request) SHALL raise a clear not-supported error on the async client, immediately and without any network call, rather than silently using blocking I/O.

#### Scenario: Upload attempted
- **WHEN** a caller attempts an upload or download through the async client
- **THEN** the caller receives a not-supported error that names the blocking client's method to use, and no network call is made
