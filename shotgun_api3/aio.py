# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Asynchronous client, built on httpx. Install it with ``pip install shotgun_api3[async]``.

.. code-block:: python

    async with AsyncShotgun(url, script_name="name", api_key="key") as sg:
        shots = await asyncio.gather(*(sg.find("Shot", [["id", "is", i]]) for i in ids))
"""

from __future__ import annotations  # Required for compatibility with Python 3.7

import asyncio
import socket
import ssl
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx

from ._core import NEED_CAPS, _ServerCapsRequired
from .shotgun import (
    LOG,
    BaseEntity,
    GroupingItem,
    OrderItem,
    ProtocolError,
    ServerCapabilities,
    _SGClient,
)

# Simultaneous connections. Conservative on purpose: a fan-out of thousands of calls would
# otherwise open thousands of sockets to the server.
DEFAULT_MAX_CONNECTIONS = 10


def _os_error_cause(error: BaseException) -> Optional[OSError]:
    """
    The innermost ``OSError`` (a ``ConnectionRefusedError`` or ``ssl.SSLError``, say) that
    httpx and its backends wrapped in ``error``, if any.
    """
    found = None
    cause = error.__cause__ or error.__context__
    while cause is not None:
        if isinstance(cause, OSError):
            found = cause
        cause = cause.__cause__ or cause.__context__
    return found


def _not_supported(name: str):
    """
    Build a method that fails at once, without any network call, to say that ``Shotgun``
    has ``name`` and ``AsyncShotgun`` does not yet.
    """

    def method(self, *args, **kwargs):
        raise NotImplementedError(
            "AsyncShotgun.%s() is not supported yet. Use Shotgun.%s(), from a worker "
            "thread (asyncio.to_thread) if the event loop must stay free."
            % (name, name)
        )

    method.__name__ = name
    method.__qualname__ = "AsyncShotgun." + name
    method.__doc__ = "Not supported yet. See :meth:`Shotgun.%s`." % name
    return method


class AsyncShotgun(_SGClient):
    """
    Asynchronous Flow Production Tracking client.

    Takes the same connection and authentication arguments as
    :class:`~shotgun_api3.Shotgun` (except ``connect`` and ``auth_token``). Use it as an
    async context manager, or call :meth:`close` when done.

    Uploads, downloads and ``auth_token`` (2FA) authentication are not supported yet.
    """

    def __init__(
        self,
        base_url: str,
        script_name: Optional[str] = None,
        api_key: Optional[str] = None,
        convert_datetimes_to_utc: bool = True,
        http_proxy: Optional[str] = None,
        ca_certs: Optional[str] = None,
        login: Optional[str] = None,
        password: Optional[str] = None,
        sudo_as_login: Optional[str] = None,
        session_token: Optional[str] = None,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
    ) -> None:
        """
        :param int max_connections: Most simultaneous connections to the server; further
            requests wait for a free one.

        See :class:`~shotgun_api3.Shotgun` for the other arguments.
        """
        self._init_config(
            base_url,
            script_name,
            api_key,
            convert_datetimes_to_utc,
            http_proxy,
            True,
            login,
            password,
            sudo_as_login,
            session_token,
            None,
        )
        self._ca_certs_file = self._get_certs_file(ca_certs)
        self.max_connections = max_connections
        self._client: Optional[httpx.AsyncClient] = None
        # Created on first use, inside the running loop (older Pythons bind it on creation).
        self._caps_lock: Optional[asyncio.Lock] = None

    # ------------------------------------------------------------------------
    # Lifecycle

    async def __aenter__(self) -> "AsyncShotgun":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Close all connections. The client opens new ones if it is used again.
        """
        client, self._client = self._client, None
        if client is not None:
            await client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """
        Return the current ``httpx`` client, creating it on first use.
        """
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self) -> httpx.AsyncClient:
        """
        Build the ``httpx`` client from the configuration.
        """
        config = self.config

        proxy = None
        if config.proxy_server:
            credentials = ""
            if config.proxy_user and config.proxy_pass:
                # Percent-encode: a password may hold characters such as "@".
                credentials = "%s:%s@" % (
                    urllib.parse.quote(config.proxy_user, safe=""),
                    urllib.parse.quote(config.proxy_pass, safe=""),
                )
            proxy = "http://%s%s:%d" % (
                credentials,
                config.proxy_server,
                config.proxy_port,
            )

        return httpx.AsyncClient(
            verify=ssl.create_default_context(cafile=self._ca_certs_file),
            proxy=proxy,
            timeout=config.timeout_secs,
            limits=httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_connections,
                # Falsy means "never expire" for the sync client; httpx spells that None
                # (0 would mean "never reuse a connection").
                keepalive_expiry=config.max_connection_idle_secs or None,
            ),
        )

    async def connect(self) -> None:
        """
        Connect to the server, to check the connection and credentials early. See
        :meth:`Shotgun.connect`.
        """
        await self.info()

    # Uploads and downloads use blocking I/O outside the rpc path; the other three change the
    # credentials of the client while they run, or need a request in the middle of a call.
    upload = _not_supported("upload")
    upload_thumbnail = _not_supported("upload_thumbnail")
    upload_filmstrip_thumbnail = _not_supported("upload_filmstrip_thumbnail")
    share_thumbnail = _not_supported("share_thumbnail")
    download_attachment = _not_supported("download_attachment")
    get_attachment_download_url = _not_supported("get_attachment_download_url")
    get_auth_cookie_handler = _not_supported("get_auth_cookie_handler")
    get_session_token = _not_supported("get_session_token")
    authenticate_human_user = _not_supported("authenticate_human_user")
    update_project_last_accessed = _not_supported("update_project_last_accessed")

    # ------------------------------------------------------------------------
    # Server capabilities

    async def get_server_caps(self) -> ServerCapabilities:
        """
        Return the :class:`ServerCapabilities` of the server, asking it the first time.

        Tasks that ask at the same time share a single ``info()`` request.
        """
        if not self._caps_known():
            if self._caps_lock is None:
                self._caps_lock = asyncio.Lock()
            async with self._caps_lock:
                # Another task may have fetched them while this one waited for the lock.
                if not self._caps_known():
                    self._server_caps = ServerCapabilities(
                        self.config.server, await self.info()
                    )
        return self._server_caps

    @property
    def server_info(self) -> Dict[str, Any]:
        """
        The server's ``info()`` data. Unlike on :class:`Shotgun` this cannot ask the server,
        so it is only available once :meth:`get_server_caps` has run.
        """
        if not self._caps_known():
            raise RuntimeError(
                "The server info is not known yet: await get_server_caps() first."
            )
        return self._server_caps.server_info

    def _caps_known(self) -> bool:
        return bool(self._server_caps) and self._server_caps.host == self.config.server

    async def info(self) -> Dict[str, Any]:
        """
        Get the server's version and capabilities, see :meth:`Shotgun.info`.
        """
        return await self._call_rpc("info", None, include_auth_params=False)

    # ------------------------------------------------------------------------
    # Requests
    #
    # These do what the methods of the same name on Shotgun do, see their documentation. The
    # logic lives in the shared core; here it is only driven with awaited calls.

    async def find(
        self,
        entity_type: str,
        filters: Union[List, Tuple, Dict[str, Any]],
        fields: Optional[List[str]] = None,
        order: Optional[List[OrderItem]] = None,
        filter_operator: Optional[str] = None,
        limit: int = 0,
        retired_only: bool = False,
        page: int = 0,
        include_archived_projects: bool = True,
        additional_filter_presets: Optional[List[Dict[str, Any]]] = None,
    ) -> List[BaseEntity]:
        """
        Find entities matching the given filters, see :meth:`Shotgun.find`.
        """
        return await self._run_flow(
            self._find_flow(
                entity_type,
                filters,
                fields,
                order,
                filter_operator,
                limit,
                retired_only,
                page,
                include_archived_projects,
                additional_filter_presets,
            )
        )

    async def find_one(
        self,
        entity_type: str,
        filters: Union[List, Tuple, Dict[str, Any]],
        fields: Optional[List[str]] = None,
        order: Optional[List[OrderItem]] = None,
        filter_operator: Optional[str] = None,
        retired_only: bool = False,
        include_archived_projects: bool = True,
        additional_filter_presets: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[BaseEntity]:
        """
        Find the first entity matching the given filters, see :meth:`Shotgun.find_one`.
        """
        results = await self.find(
            entity_type,
            filters,
            fields,
            order,
            filter_operator,
            1,
            retired_only,
            include_archived_projects=include_archived_projects,
            additional_filter_presets=additional_filter_presets,
        )

        if results:
            return results[0]
        return None

    async def create(
        self,
        entity_type: str,
        data: Dict[str, Any],
        return_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create an entity, see :meth:`Shotgun.create`. Thumbnail uploads are not supported.
        """
        params, upload_image, upload_filmstrip_image = await self._with_caps(
            self._prepare_create, entity_type, data, return_fields
        )
        self._ensure_no_uploads(upload_image, upload_filmstrip_image)

        record = await self._call_rpc("create", params, first=True)
        return (await self._with_caps(self._parse_records, record))[0]

    async def update(
        self,
        entity_type: str,
        entity_id: int,
        data: Dict[str, Any],
        multi_entity_update_modes: Optional[Dict[str, Any]] = None,
    ) -> BaseEntity:
        """
        Update an entity, see :meth:`Shotgun.update`. Thumbnail uploads are not supported.
        """
        params, upload_image, upload_filmstrip_image = await self._with_caps(
            self._prepare_update,
            entity_type,
            entity_id,
            data,
            multi_entity_update_modes,
        )
        self._ensure_no_uploads(upload_image, upload_filmstrip_image)

        if params is None:
            return {"id": entity_id, "type": entity_type}

        record = await self._call_rpc("update", params)
        return (await self._with_caps(self._parse_records, record))[0]

    async def delete(self, entity_type: str, entity_id: int) -> bool:
        """
        Retire an entity, see :meth:`Shotgun.delete`.
        """
        params = {"type": entity_type, "id": entity_id}

        return await self._call_rpc("delete", params)

    async def batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Make several create, update and delete calls in one transaction, see
        :meth:`Shotgun.batch`.
        """
        calls = self._build_batch_calls(requests)

        # Nothing to process means nothing to get results of.
        if not calls:
            return []

        records = await self._call_rpc("batch", calls)
        return await self._with_caps(self._parse_records, records)

    async def summarize(
        self,
        entity_type: str,
        filters: Union[List, Dict[str, Any]],
        summary_fields: List[Dict[str, str]],
        filter_operator: Optional[str] = None,
        grouping: Optional[List[GroupingItem]] = None,
        include_archived_projects: bool = True,
    ) -> Dict[str, Any]:
        """
        Summarize field data returned by a query. See :meth:`Shotgun.summarize`.
        """
        rpc, params = await self._with_caps(
            self._prepare_summarize,
            entity_type,
            filters,
            summary_fields,
            filter_operator,
            grouping,
            include_archived_projects,
        )
        return await self._call_rpc(rpc, params)

    async def revive(self, entity_type: str, entity_id: int) -> bool:
        """
        Revive an entity that has previously been deleted. See :meth:`Shotgun.revive`.
        """
        rpc, params = await self._with_caps(
            self._prepare_revive, entity_type, entity_id
        )
        return await self._call_rpc(rpc, params)

    async def work_schedule_read(
        self,
        start_date: str,
        end_date: str,
        project: Optional[Dict[str, Any]] = None,
        user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Return the work day rules for a given date range. See :meth:`Shotgun.work_schedule_read`.
        """
        rpc, params = await self._with_caps(
            self._prepare_work_schedule_read, start_date, end_date, project, user
        )
        return await self._call_rpc(rpc, params)

    async def work_schedule_update(
        self,
        date: str,
        working: bool,
        description: Optional[str] = None,
        project: Optional[Dict[str, Any]] = None,
        user: Optional[Dict[str, Any]] = None,
        recalculate_field: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update the work schedule for a given date. See :meth:`Shotgun.work_schedule_update`.
        """
        rpc, params = await self._with_caps(
            self._prepare_work_schedule_update,
            date,
            working,
            description,
            project,
            user,
            recalculate_field,
        )
        return await self._call_rpc(rpc, params)

    async def export_page(self, page_id, format, layout_name=None):
        """
        Export the specified page to the given format. See :meth:`Shotgun.export_page`.
        """
        rpc, params = await self._with_caps(
            self._prepare_export_page, page_id, format, layout_name
        )
        return await self._call_rpc(rpc, params)

    async def follow(
        self, user: Dict[str, Any], entity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add the entity to the user's followed entities. See :meth:`Shotgun.follow`.
        """
        rpc, params = await self._with_caps(self._prepare_follow, user, entity)
        return await self._call_rpc(rpc, params)

    async def unfollow(
        self, user: Dict[str, Any], entity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Remove entity from the user's followed entities. See :meth:`Shotgun.unfollow`.
        """
        rpc, params = await self._with_caps(self._prepare_unfollow, user, entity)
        return await self._call_rpc(rpc, params)

    async def followers(self, entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Return all followers for an entity. See :meth:`Shotgun.followers`.
        """
        rpc, params = await self._with_caps(self._prepare_followers, entity)
        return await self._call_rpc(rpc, params)

    async def following(
        self,
        user: Dict[str, Any],
        project: Optional[Dict[str, Any]] = None,
        entity_type: Optional[str] = None,
    ) -> List[BaseEntity]:
        """
        Return all entity instances a user is following. See :meth:`Shotgun.following`.
        """
        rpc, params = await self._with_caps(
            self._prepare_following, user, project, entity_type
        )
        return await self._call_rpc(rpc, params)

    async def schema_entity_read(
        self, project_entity: Optional[BaseEntity] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return all active entity types, their display names, and their visibility. See :meth:`Shotgun.schema_entity_read`.
        """
        rpc, params = await self._with_caps(
            self._prepare_schema_entity_read, project_entity
        )
        return await self._call_rpc(rpc, params)

    async def schema_read(
        self, project_entity: Optional[BaseEntity] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get the schema for all fields on all entities. See :meth:`Shotgun.schema_read`.
        """
        rpc, params = await self._with_caps(self._prepare_schema_read, project_entity)
        return await self._call_rpc(rpc, params)

    async def schema_field_read(
        self,
        entity_type: str,
        field_name: Optional[str] = None,
        project_entity: Optional[BaseEntity] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get schema for all fields on the specified entity type or just the field name specified See :meth:`Shotgun.schema_field_read`.
        """
        rpc, params = await self._with_caps(
            self._prepare_schema_field_read, entity_type, field_name, project_entity
        )
        return await self._call_rpc(rpc, params)

    async def schema_field_create(
        self,
        entity_type: str,
        data_type: str,
        display_name: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a field for the specified entity type. See :meth:`Shotgun.schema_field_create`.
        """
        rpc, params = await self._with_caps(
            self._prepare_schema_field_create,
            entity_type,
            data_type,
            display_name,
            properties,
        )
        return await self._call_rpc(rpc, params)

    async def schema_field_update(
        self,
        entity_type: str,
        field_name: str,
        properties: Dict[str, Any],
        project_entity: Optional[BaseEntity] = None,
    ) -> bool:
        """
        Update the properties for the specified field on an entity. See :meth:`Shotgun.schema_field_update`.
        """
        rpc, params = await self._with_caps(
            self._prepare_schema_field_update,
            entity_type,
            field_name,
            properties,
            project_entity,
        )
        return await self._call_rpc(rpc, params)

    async def schema_field_delete(self, entity_type: str, field_name: str) -> bool:
        """
        Delete the specified field from the entity type. See :meth:`Shotgun.schema_field_delete`.
        """
        rpc, params = await self._with_caps(
            self._prepare_schema_field_delete, entity_type, field_name
        )
        return await self._call_rpc(rpc, params)

    async def nav_expand(self, path: str, seed_entity_field=None, entity_fields=None):
        """
        Expand the navigation hierarchy for the supplied path. See :meth:`Shotgun.nav_expand`.
        """
        rpc, params = await self._with_caps(
            self._prepare_nav_expand, path, seed_entity_field, entity_fields
        )
        return await self._call_rpc(rpc, params)

    async def nav_search_string(
        self, root_path: str, search_string: str, seed_entity_field=None
    ):
        """
        Search function adapted to work with the navigation hierarchy. See :meth:`Shotgun.nav_search_string`.
        """
        rpc, params = await self._with_caps(
            self._prepare_nav_search_string, root_path, search_string, seed_entity_field
        )
        return await self._call_rpc(rpc, params)

    async def nav_search_entity(
        self,
        root_path: str,
        entity: Dict[str, Any],
        seed_entity_field: Optional[Dict[str, Any]] = None,
    ):
        """
        Search function adapted to work with the navigation hierarchy. See :meth:`Shotgun.nav_search_entity`.
        """
        rpc, params = await self._with_caps(
            self._prepare_nav_search_entity, root_path, entity, seed_entity_field
        )
        return await self._call_rpc(rpc, params)

    async def preferences_read(self, prefs: Optional[List] = None) -> Dict[str, Any]:
        """
        Get a subset of the site preferences. See :meth:`Shotgun.preferences_read`.
        """
        rpc, params = await self._with_caps(self._prepare_preferences_read, prefs)
        return await self._call_rpc(rpc, params)

    async def user_subscriptions_read(self) -> List:
        """
        Get the list of user subscriptions. See :meth:`Shotgun.user_subscriptions_read`.
        """
        rpc, params = await self._with_caps(self._prepare_user_subscriptions_read)
        return await self._call_rpc(rpc, params)

    async def custom_entity_read(self, entity_type: str) -> Dict[str, Any]:
        """
        Read the current configuration of a Custom Entity. See :meth:`Shotgun.custom_entity_read`.
        """
        rpc, params = await self._with_caps(
            self._prepare_custom_entity_read, entity_type
        )
        return await self._call_rpc(rpc, params)

    async def custom_entity_enable(self, entity_type: str) -> Dict[str, Any]:
        """
        Enable a Custom Entity. See :meth:`Shotgun.custom_entity_enable`.
        """
        rpc, params = await self._with_caps(
            self._prepare_custom_entity_enable, entity_type
        )
        return await self._call_rpc(rpc, params)

    async def custom_entity_configure(
        self,
        entity_type: str,
        display_name: Optional[str] = None,
        entity_config: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """
        Update an already-enabled Custom Entity's display name and/or feature flags. See :meth:`Shotgun.custom_entity_configure`.
        """
        rpc, params = await self._with_caps(
            self._prepare_custom_entity_configure,
            entity_type,
            display_name,
            entity_config,
        )
        return await self._call_rpc(rpc, params)

    async def custom_entity_disable(
        self, entity_type: str, force: bool = False
    ) -> Dict[str, Any]:
        """
        Disable a Custom Entity, clearing its feature flags. See :meth:`Shotgun.custom_entity_disable`.
        """
        rpc, params = await self._with_caps(
            self._prepare_custom_entity_disable, entity_type, force
        )
        return await self._call_rpc(rpc, params)

    async def note_thread_read(
        self, note_id: int, entity_fields: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Return the full conversation for a given note, including Replies and Attachments. See :meth:`Shotgun.note_thread_read`.
        """
        rpc, params = await self._with_caps(
            self._prepare_note_thread_read, note_id, entity_fields
        )
        record = await self._call_rpc(rpc, params)
        result = await self._with_caps(self._parse_records, record)
        return result

    async def text_search(
        self,
        text: str,
        entity_types: Dict[str, Any],
        project_ids: Optional[List] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search across the specified entity types for the given text. See :meth:`Shotgun.text_search`.
        """
        rpc, params = await self._with_caps(
            self._prepare_text_search, text, entity_types, project_ids, limit
        )
        record = await self._call_rpc(rpc, params)
        result = (await self._with_caps(self._parse_records, record))[0]
        return result

    async def activity_stream_read(
        self,
        entity_type: str,
        entity_id: int,
        entity_fields: Optional[Dict[str, Any]] = None,
        min_id: Optional[int] = None,
        max_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve activity stream data from Shotgun. See :meth:`Shotgun.activity_stream_read`.
        """
        rpc, params = await self._with_caps(
            self._prepare_activity_stream_read,
            entity_type,
            entity_id,
            entity_fields,
            min_id,
            max_id,
            limit,
        )
        record = await self._call_rpc(rpc, params)
        result = (await self._with_caps(self._parse_records, record))[0]
        return result

    async def user_subscriptions_create(
        self, users: List[Dict[str, Union[str, List[str], None]]]
    ) -> bool:
        """
        Create the subscriptions of the given users. See
        :meth:`Shotgun.user_subscriptions_create`.
        """
        response = await self._call_rpc("user_subscriptions_create", {"users": users})

        return self._user_subscriptions_created(response)

    @staticmethod
    def _ensure_no_uploads(*uploads) -> None:
        """
        Raise before any request is made if a thumbnail upload was asked for.
        """
        if any(uploads):
            raise NotImplementedError(
                "Thumbnail uploads are not supported by AsyncShotgun yet."
            )

    async def _with_caps(self, fn, *args, **kwargs):
        """
        Call a core helper that takes ``caps``. It is called without them first and only
        given the server capabilities (fetched once) if it asks.
        """
        try:
            return fn(*args, **kwargs)
        except _ServerCapsRequired:
            return fn(*args, caps=await self.get_server_caps(), **kwargs)

    async def _run_flow(self, flow):
        """
        Drive a generator flow from the core (see ``_SGCore._find_flow``) with awaited calls.
        """
        reply = None
        while True:
            try:
                step = flow.send(reply)
            except StopIteration as stop:
                return stop.value
            if step is NEED_CAPS:
                reply = await self.get_server_caps()
            else:
                reply = await self._call_rpc(*step)

    # ------------------------------------------------------------------------
    # Transport

    async def _call_rpc(
        self,
        method: str,
        params: Any,
        include_auth_params: bool = True,
        first: bool = False,
    ) -> Any:
        """
        Call the specified method on the server sending the supplied payload.
        """
        LOG.debug("Starting rpc call to %s with params %s" % (method, params))

        params = self._transform_outbound(params)
        try:
            payload = self._build_payload(
                method, params, include_auth_params=include_auth_params
            )
        except _ServerCapsRequired:
            payload = self._build_payload(
                method,
                params,
                include_auth_params=include_auth_params,
                caps=await self.get_server_caps(),
            )
        encoded_payload = self._encode_payload(payload)
        req_headers = self._rpc_request_headers()

        attempt = 1
        while attempt <= self.MAX_ATTEMPTS:
            http_status, resp_headers, body = await self._make_call(
                "POST", self.config.api_path, encoded_payload, req_headers
            )

            LOG.debug("Completed rpc call to %s" % (method))

            try:
                self._parse_http_status(http_status)
            except ProtocolError as e:
                self._annotate_protocol_error(e, resp_headers, body)

                # Allow limited retries for gateway errors specifically.
                delay = self._gateway_retry_delay(e, attempt)
                if delay is not None:
                    LOG.debug("Got a 502 or 504 response. Waiting and retrying...")
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise
            else:
                break

        return self._finish_rpc(resp_headers, body, first)

    async def _make_call(
        self, verb: str, path: str, body, headers: Optional[Dict[str, Any]]
    ) -> Tuple[Tuple[int, str], Dict[str, Any], bytes]:
        """
        Make an HTTP call to the server, retrying the failures worth retrying.
        """
        attempt = 0
        req_headers = self._call_headers(headers)
        body = body or None

        max_rpc_attempts = self.config.max_rpc_attempts
        rpc_attempt_interval = self.config.rpc_attempt_interval / 1000.0

        while attempt < max_rpc_attempts:
            attempt += 1
            try:
                return await self._http_request(verb, path, body, req_headers)
            except Exception as e:
                # The sync client closes its single connection here. This client's
                # connections are shared by concurrent requests, and httpx already drops
                # a connection that failed, so only this request is retried.
                if not self._is_retryable_connection_error(e):
                    LOG.debug(f"Request failed.  Reason: {e}", exc_info=True)
                    raise
                if isinstance(e, ssl.SSLEOFError):
                    # SG-34910 - EOF occurred in violation of protocol (_ssl.c:2426)
                    LOG.debug("SSLEOFError: {}".format(e))
                if attempt == max_rpc_attempts:
                    LOG.debug("Request failed.  Giving up after %d attempts." % attempt)
                    raise

            LOG.debug(
                "Request failed, attempt %d of %d.  Retrying in %.2f seconds..."
                % (attempt, max_rpc_attempts, rpc_attempt_interval)
            )
            await asyncio.sleep(rpc_attempt_interval)

    async def _http_request(
        self, verb: str, path: str, body, headers: Dict[str, Any]
    ) -> Tuple[Tuple[int, str], Dict[str, Any], bytes]:
        """
        Make the actual HTTP request.

        Raises the same errors as the sync client does: ``socket.timeout`` on a timeout and
        the underlying ``OSError`` (an ``ssl.SSLError``, say) on a connection failure.
        """
        url = urllib.parse.urlunparse(
            (self.config.scheme, self.config.server, path, None, None, None)
        )
        LOG.debug("Request is %s:%s" % (verb, url))
        LOG.debug("Request headers are %s" % headers)
        LOG.debug("Request body is %s" % body)

        try:
            resp = await self._get_client().request(
                verb, url, content=body, headers=headers
            )
        except httpx.TimeoutException as e:
            raise socket.timeout(str(e)) from e
        except httpx.TransportError as e:
            cause = _os_error_cause(e)
            if cause is None:
                raise
            raise cause from e

        # http response code is handled else where
        http_status = (resp.status_code, resp.reason_phrase)
        resp_headers = dict((k.lower(), v) for k, v in resp.headers.items())

        LOG.debug("Response status is %s %s" % http_status)
        LOG.debug("Response headers are %s" % resp_headers)
        LOG.debug("Response body is %s" % resp.content)

        return (http_status, resp_headers, resp.content)
