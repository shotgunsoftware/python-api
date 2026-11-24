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
Logic shared by the synchronous and asynchronous clients.

Nothing in this module performs network I/O.
"""

from __future__ import annotations  # Required for compatibility with Python 3.7

import datetime
import copy
import json
import re
import ssl
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Union
from xmlrpc.client import ProtocolError

from .lib.sgtimezone import SgTimezone

SG_TIMEZONE = SgTimezone()

T = TypeVar("T")

# Set from the SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION environment variable by Shotgun().
SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION = False


# Yielded by a shared generator flow (see ``_SGCore._find_flow``) to ask its driver for the
# server's ServerCapabilities, which the driver sends back.
NEED_CAPS = object()


class _ServerCapsRequired(Exception):
    """
    Internal signal: the requested auth params depend on the server version.

    Raised by ``_SGCore._auth_params`` when called without ``caps``. The caller
    fetches the server capabilities (blocking or awaited, as appropriate) and calls
    again with them, so the shared logic never performs I/O itself.
    """


# ----------------------------------------------------------------------------
# Errors


class ShotgunError(Exception):
    """
    Base for all Shotgun API Errors.
    """

    pass


class ShotgunFileDownloadError(ShotgunError):
    """
    Exception for file download-related errors.
    """

    pass


class ShotgunThumbnailNotReady(ShotgunError):
    """
    Exception for when trying to use a 'pending thumbnail' (aka transient thumbnail) in an operation
    """

    pass


class Fault(ShotgunError):
    """
    Exception when server-side exception detected.
    """

    pass


class AuthenticationFault(Fault):
    """
    Exception when the server side reports an error related to authentication.
    """

    pass


class MissingTwoFactorAuthenticationFault(Fault):
    """
    Exception when the server side reports an error related to missing two-factor authentication
    credentials.
    """

    pass


class UserCredentialsNotAllowedForSSOAuthenticationFault(Fault):
    """
    Exception when the server is configured to use SSO. It is not possible to use
    a username/password pair to authenticate on such server.
    """

    pass


class UserCredentialsNotAllowedForOxygenAuthenticationFault(Fault):
    """
    Exception when the server is configured to use Oxygen. It is not possible to use
    a username/password pair to authenticate on such server.
    """

    pass


# ----------------------------------------------------------------------------
# Shared logic


class _SGCore(object):
    """
    Pure, transport-agnostic behavior shared by ``Shotgun`` and ``AsyncShotgun``.

    Relies on the subclass providing ``self.config``.
    """

    # Note a length check is done before checking the reg ex
    _DATE_TIME_PATTERN = re.compile(
        r"^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])"
        r"(\D?([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?)?$"
    )

    MAX_ATTEMPTS = 3  # Retries on failure
    BACKOFF = 0.75  # Seconds to wait before retry, times the attempt number

    # HTTP statuses worth retrying: we've seen rare instances of PTR returning 502 for
    # issues that appear to be caused by something internal to PTR.
    _GATEWAY_RETRY_STATUSES = (502, 504)

    @staticmethod
    def _is_retryable_connection_error(error: BaseException) -> bool:
        """
        Whether a failed HTTP call is worth repeating (up to ``config.max_rpc_attempts``).

        SSL errors are, since proxies sometimes drop a keep-alive connection at the
        TCP/TLS level (SG-34910). Anything else fails immediately.
        """
        return isinstance(error, (ssl.SSLError, ssl.CertificateError))

    def _rpc_request_headers(self) -> Dict[str, Any]:
        """
        Headers of an rpc request.
        """
        req_headers = {
            "content-type": "application/json; charset=utf-8",
            "connection": "keep-alive",
        }

        if self.config.localized is True:
            req_headers["locale"] = "auto"
        return req_headers

    def _finish_rpc(self, resp_headers: Dict[str, Any], body: Any, first: bool) -> Any:
        """
        Turn the response of a successful rpc call into its result, raising the errors the
        server reported.
        """
        response = self._decode_response(resp_headers, body)
        self._response_errors(response)
        response = self._transform_inbound(response)

        if not isinstance(response, dict) or "results" not in response:
            return response

        results = response.get("results")
        if first and isinstance(results, list):
            return results[0]
        return results

    def _gateway_retry_delay(
        self, error: ProtocolError, attempt: int
    ) -> Optional[float]:
        """
        Seconds to wait before retrying a call that failed with ``error`` on the given
        (1-based) attempt, or ``None`` if the error must be raised instead.
        """
        if (
            attempt != self.MAX_ATTEMPTS
            and error.errcode in self._GATEWAY_RETRY_STATUSES
        ):
            return float(attempt) * self.BACKOFF
        return None

    @staticmethod
    def _annotate_protocol_error(
        error: ProtocolError, headers: Dict[str, Any], body: Any
    ) -> ProtocolError:
        """
        Attach the response headers (and, for a 403, the custom error page) to ``error``.
        """
        error.headers = headers
        if error.errcode == 403:
            # 403 is returned with custom error page when api access is blocked
            error.errmsg += ": %s" % body
        return error

    def _encode_payload(self, payload) -> bytes:
        """
        Encode the payload to a string to be passed to the rpc endpoint.

        The payload is json encoded as a unicode string if the content
        requires it. The unicode string is then encoded as 'utf-8' as it must
        be in a single byte encoding to go over the wire.
        """

        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _decode_response(
        self, headers: Dict[str, Any], body: str
    ) -> Union[str, Dict[str, Any]]:
        """
        Decode the response from the server from the wire format to
        a python data structure.

        :param dict headers: Headers from the server.
        :param str body: Raw response body from the server.
        :returns: If the content-type starts with application/json or
            text/javascript the body is json decoded. Otherwise the raw body is
            returned.
        :rtype: str
        """
        if not body:
            return body

        ct = (headers.get("content-type") or "application/json").lower()

        if ct.startswith("application/json") or ct.startswith("text/javascript"):
            return self._json_loads(body)
        return body

    def _json_loads(self, body: str) -> Any:
        return json.loads(body)

    def _response_errors(self, sg_response):
        """
        Raise any API errors specified in the response.

        :raises ShotgunError: If the server response contains an exception.
        """

        # error code for authentication related problems
        ERR_AUTH = 102
        # error code when 2FA authentication is required but no 2FA token provided.
        ERR_2FA = 106
        # error code when SSO is activated on the site, preventing the use of username/password for authentication.
        ERR_SSO = 108
        # error code when Oxygen is activated on the site, preventing the use of username/password for authentication.
        ERR_OXYG = 110

        if isinstance(sg_response, dict) and sg_response.get("exception"):
            if sg_response.get("error_code") == ERR_AUTH:
                raise AuthenticationFault(
                    sg_response.get("message", "Unknown Authentication Error")
                )
            elif sg_response.get("error_code") == ERR_2FA:
                raise MissingTwoFactorAuthenticationFault(
                    sg_response.get("message", "Unknown 2FA Authentication Error")
                )
            elif sg_response.get("error_code") == ERR_SSO:
                raise UserCredentialsNotAllowedForSSOAuthenticationFault(
                    sg_response.get(
                        "message",
                        "Authentication using username/password is not "
                        "allowed for an SSO-enabled Flow Production Tracking site",
                    )
                )
            elif sg_response.get("error_code") == ERR_OXYG:
                raise UserCredentialsNotAllowedForOxygenAuthenticationFault(
                    sg_response.get(
                        "message",
                        "Authentication using username/password is not "
                        "allowed for an Autodesk Identity enabled Flow Production Tracking site",
                    )
                )
            else:
                # raise general Fault
                raise Fault(sg_response.get("message", "Unknown Error"))
        return

    def _parse_http_status(self, status: Tuple) -> None:
        """
        Parse the status returned from the http request.

        :param tuple status: Tuple of (code, reason).
        :raises: RuntimeError if the http status is non success.
        """
        error_code = status[0]
        errmsg = status[1]

        if status[0] >= 300:
            headers = "HTTP error from server"
            if status[0] == 503:
                errmsg = "Flow Production Tracking is currently down for maintenance or too busy to reply. Please try again later."
            raise ProtocolError(self.config.server, error_code, errmsg, headers)

        return

    def _visit_data(self, data: T, visitor) -> T:
        """
        Walk the data (simple python types) and call the visitor.
        """

        if not data:
            return data

        recursive = self._visit_data
        if isinstance(data, list):
            return [recursive(i, visitor) for i in data]  # type: ignore[return-value]

        if isinstance(data, tuple):
            return tuple(recursive(i, visitor) for i in data)  # type: ignore[return-value]

        if isinstance(data, dict):
            return dict((k, recursive(v, visitor)) for k, v in data.items())  # type: ignore[return-value]

        return visitor(data)

    def _transform_outbound(self, data: T) -> T:
        """
        Transform data types or values before they are sent by the client.

        - changes timezones
        - converts dates and times to strings
        """

        if self.config.convert_datetimes_to_utc:

            def _change_tz(value):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=SG_TIMEZONE.local)
                return value.astimezone(SG_TIMEZONE.utc)

        else:
            _change_tz = None

        local_now = datetime.datetime.now()

        def _outbound_visitor(value):

            if isinstance(value, datetime.datetime):
                if _change_tz:
                    value = _change_tz(value)

                return value.strftime("%Y-%m-%dT%H:%M:%SZ")

            if isinstance(value, datetime.date):
                # existing code did not tz transform dates.
                return value.strftime("%Y-%m-%d")

            if isinstance(value, datetime.time):
                value = local_now.replace(
                    hour=value.hour,
                    minute=value.minute,
                    second=value.second,
                    microsecond=value.microsecond,
                )
                if _change_tz:
                    value = _change_tz(value)
                return value.strftime("%Y-%m-%dT%H:%M:%SZ")

            return value

        return self._visit_data(data, _outbound_visitor)

    def _transform_inbound(self, data: T) -> T:
        """
        Transforms data types or values after they are received from the server.
        """
        # NOTE: The time zone is removed from the time after it is transformed
        # to the local time, otherwise it will fail to compare to datetimes
        # that do not have a time zone.
        if self.config.convert_datetimes_to_utc:

            def _change_tz(x):
                return x.replace(tzinfo=SG_TIMEZONE.utc).astimezone(SG_TIMEZONE.local)

        else:
            _change_tz = None

        def _inbound_visitor(value):
            if isinstance(value, str):
                if len(value) == 20 and self._DATE_TIME_PATTERN.match(value):
                    try:
                        value = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
                    except ValueError:
                        return value
                    if _change_tz:
                        return _change_tz(value)
                    return value

            return value

        return self._visit_data(data, _inbound_visitor)

    def _auth_params(self, caps: Optional[Any] = None) -> Dict[str, Any]:
        """
        Return a dictionary of the authentication parameters being used.

        :param caps: ``ServerCapabilities`` of the server, needed only for version-gated
            options (session token, ``sudo_as_login``).
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        # Used to authenticate HumanUser credentials
        if self.config.user_login and self.config.user_password:
            auth_params = {
                "user_login": str(self.config.user_login),
                "user_password": str(self.config.user_password),
            }
            if self.config.auth_token:
                auth_params["auth_token"] = str(self.config.auth_token)

        # Use script name instead
        elif self.config.script_name and self.config.api_key:
            auth_params = {
                "script_name": str(self.config.script_name),
                "script_key": str(self.config.api_key),
            }

        # Authenticate using session_id
        elif self.config.session_token:
            if caps is None:
                raise _ServerCapsRequired()
            if caps.version and caps.version < (5, 3, 0):
                raise ShotgunError(
                    "Session token based authentication requires server version "
                    "5.3.0 or higher, server is %s" % (caps.version,)
                )

            auth_params = {"session_token": str(self.config.session_token)}

            # Request server side to raise exception for expired sessions.
            # This was added in as part of Shotgun 5.4.4
            if caps.version and caps.version > (5, 4, 3):
                auth_params["reject_if_expired"] = True

        else:
            raise ValueError("invalid auth params")

        if self.config.session_uuid:
            auth_params["session_uuid"] = self.config.session_uuid

        # Make sure sudo_as_login is supported by server version
        if self.config.sudo_as_login:
            if caps is None:
                raise _ServerCapsRequired()
            if caps.version and caps.version < (5, 3, 12):
                raise ShotgunError(
                    "Option 'sudo_as_login' requires server version 5.3.12 or "
                    "higher, server is %s" % (caps.version,)
                )
            auth_params["sudo_as_login"] = self.config.sudo_as_login

        if self.config.extra_auth_params:
            auth_params.update(self.config.extra_auth_params)

        return auth_params

    def _sanitize_auth_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Given an authentication parameter dictionary, sanitize any sensitive
        information and return the sanitized dict copy.
        """
        sanitized_params = copy.copy(params)
        for k in ["user_password", "script_key", "session_token"]:
            if k in sanitized_params:
                sanitized_params[k] = "********"
        return sanitized_params

    def _build_payload(
        self,
        method: str,
        params,
        include_auth_params: bool = True,
        caps: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Build the payload to be send to the rpc endpoint.
        """
        if not method:
            raise ValueError("method is empty")

        call_params = []

        if include_auth_params:
            auth_params = self._auth_params(caps)
            call_params.append(auth_params)

        if params:
            call_params.append(params)

        return {"method_name": method, "params": call_params}

    def _construct_read_parameters(
        self,
        entity_type: str,
        fields: Optional[List[str]],
        filters: Dict[str, Any],
        retired_only: bool,
        order: Optional[List[Dict[str, Any]]],
        include_archived_projects: bool,
        additional_filter_presets: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        params["type"] = entity_type
        params["return_fields"] = fields or ["id"]
        params["filters"] = filters
        params["return_only"] = (retired_only and "retired") or "active"
        params["paging"] = {
            "entities_per_page": self.config.records_per_page,
            "current_page": 1,
        }

        if additional_filter_presets:
            params["additional_filter_presets"] = additional_filter_presets

        if include_archived_projects is False:
            # Defaults to True on the server, so only pass it if it's False
            params["include_archived_projects"] = False

        if order:
            sort_list = []
            for sort in order:
                if "column" in sort:
                    # TODO: warn about deprecation of 'column' param name
                    sort["field_name"] = sort["column"]
                sort.setdefault("direction", "asc")
                sort_list.append(
                    {"field_name": sort["field_name"], "direction": sort["direction"]}
                )
            params["sorts"] = sort_list
        return params

    def _translate_update_params(
        self,
        entity_type: str,
        entity_id: int,
        data: Dict,
        multi_entity_update_modes: Optional[Dict],
    ) -> Dict[str, Any]:
        global SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION

        def optimize_field(field_dict):
            if SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION:
                return field_dict
            return {k: _optimize_filter_field(v) for k, v in field_dict.items()}

        full_fields = self._dict_to_list(
            data,
            extra_data=self._dict_to_extra_data(
                multi_entity_update_modes, "multi_entity_update_mode"
            ),
        )
        return {
            "type": entity_type,
            "id": entity_id,
            "fields": [optimize_field(field_dict) for field_dict in full_fields],
        }

    def _dict_to_list(
        self,
        d: Optional[Dict[str, Any]],
        key_name: str = "field_name",
        value_name: str = "value",
        extra_data=None,
    ) -> List[Dict[str, Any]]:
        """
        Utility function to convert a dict into a list dicts using the key_name and value_name keys.

        e.g. d {'foo' : 'bar'} changed to [{'field_name':'foo', 'value':'bar'}]

        Any dictionary passed in via extra_data will be merged into the resulting dictionary.
        e.g. d as above and extra_data of {'foo': {'thing1': 'value1'}} changes into
        [{'field_name': 'foo', 'value': 'bar', 'thing1': 'value1'}]
        """
        ret = []
        for k, v in (d or {}).items():
            d = {key_name: k, value_name: v}
            d.update((extra_data or {}).get(k, {}))
            ret.append(d)
        return ret

    def _dict_to_extra_data(
        self, d: Optional[Dict[str, Any]], key_name="value"
    ) -> Dict[str, Any]:
        """
        Utility function to convert a dict into a dict compatible with the extra_data arg
        of _dict_to_list.

        e.g. d {'foo' : 'bar'} changed to {'foo': {"value": 'bar'}]
        """
        return dict([(k, {key_name: v}) for (k, v) in (d or {}).items()])

    def _parse_records(self, records: List, caps: Optional[Any] = None) -> List:
        """
        Parse 'records' returned from the api to do local modifications:

        - Insert thumbnail urls
        - Insert local file paths.
        - Revert &lt; html entities that may be the result of input sanitization
          mechanisms back to a litteral < character.

        :param records: List of records (dicts) to process or a single record.
        :param caps: ``ServerCapabilities``, needed only when a record has an image.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.

        :returns: A list of the records processed.
        """

        if not records:
            return []

        if not isinstance(records, (list, tuple)):
            records = [
                records,
            ]

        for rec in records:
            # skip results that aren't entity dictionaries
            if not isinstance(rec, dict):
                continue

            # iterate over each item and check each field for possible injection
            for k, v in rec.items():
                if not v:
                    continue

                # Check for html entities in strings
                if isinstance(v, str):
                    rec[k] = rec[k].replace("&lt;", "<")

                # check for thumbnail for older version (<3.3.0) of shotgun
                if k == "image":
                    if caps is None:
                        raise _ServerCapsRequired()
                    if caps.version and caps.version < (3, 3, 0):
                        rec["image"] = self._build_thumb_url(rec["type"], rec["id"])
                        continue

                if (
                    isinstance(v, dict)
                    and v.get("link_type") == "local"
                    and self.client_caps.local_path_field in v
                ):
                    local_path = v[self.client_caps.local_path_field]
                    v["local_path"] = local_path
                    v["url"] = "file://%s" % (local_path or "",)

        return records

    def _build_thumb_url(self, entity_type: str, entity_id: int) -> str:
        """
        Thumbnail URL for servers older than 3.3.0. Needs a network call, so only clients
        that can make one in place implement it.
        """
        raise NotImplementedError(
            "Servers older than 3.3.0 are not supported by this client."
        )

    @staticmethod
    def _ensure_filmstrip_support(caps: Optional[Any]) -> None:
        if caps is None:
            raise _ServerCapsRequired()
        if not caps.version or caps.version < (3, 1, 0):
            raise ShotgunError(
                "Filmstrip thumbnail support requires server version 3.1 or "
                "higher, server is %s" % (caps.version,)
            )

    def _prepare_create(self, entity_type, data, return_fields, caps=None):
        """
        Build the ``create`` rpc params.

        :returns: ``(params, upload_image, upload_filmstrip_image)``; the uploads are
            split out of ``data`` for the caller to handle.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        data = data.copy()
        if not return_fields:
            return_fields = ["id"]

        upload_image = None
        if "image" in data:
            upload_image = data.pop("image")

        upload_filmstrip_image = None
        if "filmstrip_image" in data:
            self._ensure_filmstrip_support(caps)
            upload_filmstrip_image = data.pop("filmstrip_image")

        params = {
            "type": entity_type,
            "fields": self._dict_to_list(data),
            "return_fields": return_fields,
        }
        return params, upload_image, upload_filmstrip_image

    def _prepare_update(
        self, entity_type, entity_id, data, multi_entity_update_modes, caps=None
    ):
        """
        Build the ``update`` rpc params.

        :returns: ``(params, upload_image, upload_filmstrip_image)``; ``params`` is ``None``
            when ``data`` held nothing but uploads, so no rpc is needed.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        data = data.copy()
        upload_image = None
        if "image" in data and data["image"] is not None:
            upload_image = data.pop("image")
        upload_filmstrip_image = None
        if "filmstrip_image" in data:
            self._ensure_filmstrip_support(caps)
            upload_filmstrip_image = data.pop("filmstrip_image")

        params = None
        if data:
            params = self._translate_update_params(
                entity_type, entity_id, data, multi_entity_update_modes
            )
        return params, upload_image, upload_filmstrip_image

    def _build_batch_calls(self, requests) -> List[Dict[str, Any]]:
        """
        Validate ``requests`` and build the ``batch`` rpc params (empty if no requests).
        """
        if not isinstance(requests, list):
            raise ShotgunError(
                "batch() expects a list.  Instead was sent a %s" % type(requests)
            )

        calls = []

        def _required_keys(message, required_keys, data):
            missing = set(required_keys) - set(data.keys())
            if missing:
                raise ShotgunError(
                    "%s missing required key: %s. "
                    "Value was: %s." % (message, ", ".join(missing), data)
                )

        for req in requests:
            _required_keys("Batched request", ["request_type", "entity_type"], req)
            request_params = {
                "request_type": req["request_type"],
                "type": req["entity_type"],
            }

            if req["request_type"] == "create":
                _required_keys("Batched create request", ["data"], req)
                request_params["fields"] = self._dict_to_list(req["data"])
                request_params["return_fields"] = req.get("return_fields") or ["id"]
            elif req["request_type"] == "update":
                _required_keys("Batched update request", ["entity_id", "data"], req)
                request_params["id"] = req["entity_id"]
                request_params["fields"] = self._dict_to_list(
                    req["data"],
                    extra_data=self._dict_to_extra_data(
                        req.get("multi_entity_update_modes"), "multi_entity_update_mode"
                    ),
                )
                if "multi_entity_update_mode" in req:
                    request_params["multi_entity_update_mode"] = req[
                        "multi_entity_update_mode"
                    ]
            elif req["request_type"] == "delete":
                _required_keys("Batched delete request", ["entity_id"], req)
                request_params["id"] = req["entity_id"]
            else:
                raise ShotgunError(
                    "Invalid request_type '%s' for batch" % (req["request_type"])
                )
            calls.append(request_params)
        return calls

    def _find_flow(
        self,
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
    ):
        """
        The logic of ``find`` as a generator, so the sync and async clients share it.

        Yields ``NEED_CAPS`` (the driver sends back the ServerCapabilities) and
        ``("read", params)`` (the driver sends back the rpc result); returns the records.
        """
        if not isinstance(limit, int) or limit < 0:
            raise ValueError("limit parameter must be a positive integer")

        if not isinstance(page, int) or page < 0:
            raise ValueError("page parameter must be a positive integer")

        if isinstance(filters, (list, tuple)):
            filters = _translate_filters(filters, filter_operator)
        elif filter_operator:
            # TODO: Not sure if this test is correct, replicated from prev api
            raise ShotgunError(
                "Deprecated: Use of filter_operator for find() is not valid any more."
                " See the documentation on find()"
            )

        caps = yield NEED_CAPS

        if not include_archived_projects:
            # This defaults to True on the server (no argument is sent)
            # So we only need to check the server version if it is False
            caps.ensure_include_archived_projects()

        if additional_filter_presets:
            caps.ensure_support_for_additional_filter_presets()

        params = self._construct_read_parameters(
            entity_type,
            fields,
            filters,
            retired_only,
            order,
            include_archived_projects,
            additional_filter_presets,
        )

        if caps.ensure_return_image_urls_support():
            params["api_return_image_urls"] = True

        paging_without_counts = caps.ensure_paging_info_without_counts_support()
        if paging_without_counts:
            paging_info_param = "return_paging_info_without_counts"
        else:
            paging_info_param = "return_paging_info"

        params[paging_info_param] = False

        if limit and limit <= self.config.records_per_page:
            params["paging"]["entities_per_page"] = limit
            # If page isn't set and the limit doesn't require pagination,
            # then trigger the faster code path.
            if page == 0:
                page = 1

        # if page is specified, then only return the page of records requested
        if page != 0:
            params["paging"]["current_page"] = page
            result = yield ("read", params)
            return self._parse_records(result.get("entities", []), caps)

        params[paging_info_param] = True
        records = []

        if paging_without_counts:
            has_next_page = True
            while has_next_page:
                result = yield ("read", params)
                records.extend(result.get("entities"))

                if limit and len(records) >= limit:
                    records = records[:limit]
                    break

                has_next_page = result["paging_info"]["has_next_page"]
                params["paging"]["current_page"] += 1
        else:
            result = yield ("read", params)
            while result.get("entities"):
                records.extend(result.get("entities"))

                if limit and len(records) >= limit:
                    records = records[:limit]
                    break
                if len(records) == result["paging_info"]["entity_count"]:
                    break

                params["paging"]["current_page"] += 1
                result = yield ("read", params)

        return self._parse_records(records, caps)

    @staticmethod
    def _user_subscriptions_created(response) -> bool:
        """
        Whether the response to a ``user_subscriptions_create`` call reports success.
        """
        if not isinstance(response, dict):
            return False

        return response.get("status") == "success"

    @staticmethod
    def _require_caps(caps):
        """
        ``caps``, or ``_ServerCapsRequired`` if they were not given.
        """
        if caps is None:
            raise _ServerCapsRequired()
        return caps

    def _prepare_summarize(
        self,
        entity_type,
        filters,
        summary_fields,
        filter_operator=None,
        grouping=None,
        include_archived_projects=True,
        caps=None,
    ):
        """
        Validate the arguments of ``summarize`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        if not isinstance(grouping, list) and grouping is not None:
            msg = "summarize() 'grouping' parameter must be a list or None"
            raise ValueError(msg)

        if isinstance(filters, (list, tuple)):
            filters = _translate_filters(filters, filter_operator)

        if not include_archived_projects:
            # This defaults to True on the server (no argument is sent)
            # So we only need to check the server version if it is False
            caps = self._require_caps(caps)
            caps.ensure_include_archived_projects()

        params = {"type": entity_type, "summaries": summary_fields, "filters": filters}

        if include_archived_projects is False:
            # Defaults to True on the server, so only pass it if it's False
            params["include_archived_projects"] = False

        if grouping is not None:
            params["grouping"] = grouping

        return ("summarize", params)

    def _prepare_revive(self, entity_type, entity_id, caps=None):
        """
        Validate the arguments of ``revive`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        params = {"type": entity_type, "id": entity_id}

        return ("revive", params)

    def _prepare_work_schedule_read(
        self, start_date, end_date, project=None, user=None, caps=None
    ):
        """
        Validate the arguments of ``work_schedule_read`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        if not caps.version or caps.version < (3, 2, 0):
            raise ShotgunError(
                "Work schedule support requires server version 3.2 or "
                "higher, server is %s" % (caps.version,)
            )

        if not isinstance(start_date, str) or not isinstance(end_date, str):
            raise ShotgunError(
                "The start_date and end_date arguments must be strings in YYYY-MM-DD format"
            )

        params = dict(
            start_date=start_date, end_date=end_date, project=project, user=user
        )

        return ("work_schedule_read", params)

    def _prepare_work_schedule_update(
        self,
        date,
        working,
        description=None,
        project=None,
        user=None,
        recalculate_field=None,
        caps=None,
    ):
        """
        Validate the arguments of ``work_schedule_update`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        if not caps.version or caps.version < (3, 2, 0):
            raise ShotgunError(
                "Work schedule support requires server version 3.2 or "
                "higher, server is %s" % (caps.version,)
            )

        if not isinstance(date, str):
            raise ShotgunError("The date argument must be string in YYYY-MM-DD format")

        params = dict(
            date=date,
            working=working,
            description=description,
            project=project,
            user=user,
            recalculate_field=recalculate_field,
        )

        return ("work_schedule_update", params)

    def _prepare_export_page(self, page_id, format, layout_name=None, caps=None):
        """
        Validate the arguments of ``export_page`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        params = dict(format=format, page_id=page_id, layout_name=layout_name)

        return ("export_page", params)

    def _prepare_follow(self, user, entity, caps=None):
        """
        Validate the arguments of ``follow`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        if not caps.version or caps.version < (5, 1, 22):
            raise ShotgunError(
                "Follow support requires server version 5.2 or "
                "higher, server is %s" % (caps.version,)
            )

        params = dict(user=user, entity=entity)

        return ("follow", params)

    def _prepare_unfollow(self, user, entity, caps=None):
        """
        Validate the arguments of ``unfollow`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        if not caps.version or caps.version < (5, 1, 22):
            raise ShotgunError(
                "Follow support requires server version 5.2 or "
                "higher, server is %s" % (caps.version,)
            )

        params = dict(user=user, entity=entity)

        return ("unfollow", params)

    def _prepare_followers(self, entity, caps=None):
        """
        Validate the arguments of ``followers`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        if not caps.version or caps.version < (5, 1, 22):
            raise ShotgunError(
                "Follow support requires server version 5.2 or "
                "higher, server is %s" % (caps.version,)
            )

        params = dict(entity=entity)

        return ("followers", params)

    def _prepare_following(self, user, project=None, entity_type=None, caps=None):
        """
        Validate the arguments of ``following`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        caps.ensure_user_following_support()

        params = {"user": user}
        if project:
            params["project"] = project
        if entity_type:
            params["entity_type"] = entity_type

        return ("following", params)

    def _prepare_schema_entity_read(self, project_entity=None, caps=None):
        """
        Validate the arguments of ``schema_entity_read`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        params: Dict[str, Any] = {}

        params = self._add_project_param(params, project_entity, caps)

        if params:
            return ("schema_entity_read", params)
        else:
            return ("schema_entity_read", None)

    def _prepare_schema_read(self, project_entity=None, caps=None):
        """
        Validate the arguments of ``schema_read`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        params: Dict[str, Any] = {}

        params = self._add_project_param(params, project_entity, caps)

        if params:
            return ("schema_read", params)
        else:
            return ("schema_read", None)

    def _prepare_schema_field_read(
        self, entity_type, field_name=None, project_entity=None, caps=None
    ):
        """
        Validate the arguments of ``schema_field_read`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        params = {
            "type": entity_type,
        }

        if field_name:
            params["field_name"] = field_name

        params = self._add_project_param(params, project_entity, caps)

        return ("schema_field_read", params)

    def _prepare_schema_field_create(
        self, entity_type, data_type, display_name, properties=None, caps=None
    ):
        """
        Validate the arguments of ``schema_field_create`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        params = {
            "type": entity_type,
            "data_type": data_type,
            "properties": [{"property_name": "name", "value": display_name}],
        }
        params["properties"].extend(
            self._dict_to_list(properties, key_name="property_name", value_name="value")
        )

        return ("schema_field_create", params)

    def _prepare_schema_field_update(
        self, entity_type, field_name, properties, project_entity=None, caps=None
    ):
        """
        Validate the arguments of ``schema_field_update`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        params = {
            "type": entity_type,
            "field_name": field_name,
            "properties": [
                {"property_name": k, "value": v} for k, v in (properties or {}).items()
            ],
        }
        params = self._add_project_param(params, project_entity, caps)
        return ("schema_field_update", params)

    def _prepare_schema_field_delete(self, entity_type, field_name, caps=None):
        """
        Validate the arguments of ``schema_field_delete`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        params = {"type": entity_type, "field_name": field_name}

        return ("schema_field_delete", params)

    def _prepare_nav_expand(
        self, path, seed_entity_field=None, entity_fields=None, caps=None
    ):
        """
        Validate the arguments of ``nav_expand`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        return (
            "nav_expand",
            {
                "path": path,
                "seed_entity_field": seed_entity_field,
                "entity_fields": entity_fields,
            },
        )

    def _prepare_nav_search_string(
        self, root_path, search_string, seed_entity_field=None, caps=None
    ):
        """
        Validate the arguments of ``nav_search_string`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        return (
            "nav_search",
            {
                "root_path": root_path,
                "seed_entity_field": seed_entity_field,
                "search_criteria": {"search_string": search_string},
            },
        )

    def _prepare_nav_search_entity(
        self, root_path, entity, seed_entity_field=None, caps=None
    ):
        """
        Validate the arguments of ``nav_search_entity`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        return (
            "nav_search",
            {
                "root_path": root_path,
                "seed_entity_field": seed_entity_field,
                "search_criteria": {"entity": entity},
            },
        )

    def _prepare_preferences_read(self, prefs=None, caps=None):
        """
        Validate the arguments of ``preferences_read`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        if caps.version and caps.version < (7, 10, 0):
            raise ShotgunError(
                "preferences_read requires server version 7.10.0 or "
                "higher, server is %s" % (caps.version,)
            )

        prefs = prefs or []

        return ("preferences_read", {"prefs": prefs})

    def _prepare_user_subscriptions_read(self, caps=None):
        """
        Validate the arguments of ``user_subscriptions_read`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        return ("user_subscriptions_read", None)

    def _prepare_custom_entity_read(self, entity_type, caps=None):
        """
        Validate the arguments of ``custom_entity_read`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        caps.ensure_custom_entity_config_support()

        return ("custom_entity_read", {"entity_type": entity_type})

    def _prepare_custom_entity_enable(self, entity_type, caps=None):
        """
        Validate the arguments of ``custom_entity_enable`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        caps.ensure_custom_entity_config_support()

        return ("custom_entity_enable", {"entity_type": entity_type})

    def _prepare_custom_entity_configure(
        self, entity_type, display_name=None, entity_config=None, caps=None
    ):
        """
        Validate the arguments of ``custom_entity_configure`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        caps.ensure_custom_entity_config_support()

        params = {"entity_type": entity_type}
        if display_name is not None:
            params["display_name"] = display_name
        if entity_config is not None:
            params["entity_config"] = entity_config

        return ("custom_entity_configure", params)

    def _prepare_custom_entity_disable(self, entity_type, force=False, caps=None):
        """
        Validate the arguments of ``custom_entity_disable`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        caps.ensure_custom_entity_config_support()

        params = {"entity_type": entity_type}
        if force is True:
            params["force"] = True

        return ("custom_entity_disable", params)

    def _prepare_note_thread_read(self, note_id, entity_fields=None, caps=None):
        """
        Validate the arguments of ``note_thread_read`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        if caps.version and caps.version < (6, 2, 0):
            raise ShotgunError(
                "note_thread requires server version 6.2.0 or "
                "higher, server is %s" % (caps.version,)
            )

        entity_fields = entity_fields or {}

        if not isinstance(entity_fields, dict):
            raise ValueError("entity_fields parameter must be a dictionary")

        params = {"note_id": note_id, "entity_fields": entity_fields}

        return "note_thread_contents", params

    def _prepare_text_search(
        self, text, entity_types, project_ids=None, limit=None, caps=None
    ):
        """
        Validate the arguments of ``text_search`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        if caps.version and caps.version < (6, 2, 0):
            raise ShotgunError(
                "auto_complete requires server version 6.2.0 or "
                "higher, server is %s" % (caps.version,)
            )

        # convert entity_types structure into the form
        # that the API endpoint expects
        if not isinstance(entity_types, dict):
            raise ValueError("entity_types parameter must be a dictionary")

        api_entity_types = {}
        for entity_type, filter_list in entity_types.items():

            if isinstance(filter_list, (list, tuple)):
                resolved_filters = _translate_filters(filter_list, filter_operator=None)
                api_entity_types[entity_type] = resolved_filters
            else:
                raise ValueError(
                    "value of entity_types['%s'] must "
                    "be a list or tuple." % entity_type
                )

        project_ids = project_ids or []

        params = {
            "text": text,
            "entity_types": api_entity_types,
            "project_ids": project_ids,
            "max_results": limit,
        }

        return "query_display_name_cache", params

    def _prepare_activity_stream_read(
        self,
        entity_type,
        entity_id,
        entity_fields=None,
        min_id=None,
        max_id=None,
        limit=None,
        caps=None,
    ):
        """
        Validate the arguments of ``activity_stream_read`` and return its ``(rpc method, params)``.
        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        caps = self._require_caps(caps)
        if caps.version and caps.version < (6, 2, 0):
            raise ShotgunError(
                "activity_stream requires server version 6.2.0 or "
                "higher, server is %s" % (caps.version,)
            )

        # set up parameters to send to server.
        entity_fields = entity_fields or {}

        if not isinstance(entity_fields, dict):
            raise ValueError("entity_fields parameter must be a dictionary")

        params = {
            "type": entity_type,
            "id": entity_id,
            "max_id": max_id,
            "min_id": min_id,
            "limit": limit,
            "entity_fields": entity_fields,
        }

        return "activity_stream", params

    def _add_project_param(self, params, project_entity, caps=None):
        """
        Add the project to ``params`` if one was given and the server supports it.

        :raises _ServerCapsRequired: if ``caps`` is needed but was not given.
        """
        if project_entity:
            caps = self._require_caps(caps)
            if caps.ensure_per_project_customization():
                params["project"] = project_entity

        return params


# ----------------------------------------------------------------------------
# Filter translation


def _translate_filters(filters: Union[List, Tuple], filter_operator) -> Dict[str, Any]:
    """
    Translate filters params into data structure expected by rpc call.
    """
    wrapped_filters = {"filter_operator": filter_operator or "all", "filters": filters}

    return _translate_filters_dict(wrapped_filters)


def _translate_filters_dict(sg_filter: Dict[str, Any]) -> Dict[str, Any]:
    new_filters = {}
    filter_operator = sg_filter.get("filter_operator")

    if filter_operator == "all" or filter_operator == "and":
        new_filters["logical_operator"] = "and"
    elif filter_operator == "any" or filter_operator == "or":
        new_filters["logical_operator"] = "or"
    else:
        raise ShotgunError("Invalid filter_operator %s" % filter_operator)

    if not isinstance(sg_filter["filters"], (list, tuple)):
        raise ShotgunError(
            "Invalid filters, expected a list or a tuple, got %s" % sg_filter["filters"]
        )

    new_filters["conditions"] = _translate_filters_list(sg_filter["filters"])

    return new_filters


def _translate_filters_list(filters):
    conditions = []

    for sg_filter in filters:
        if isinstance(sg_filter, (list, tuple)):
            conditions.append(_translate_filters_simple(sg_filter))
        elif isinstance(sg_filter, dict):
            conditions.append(_translate_filters_dict(sg_filter))
        else:
            raise ShotgunError(
                "Invalid filters, expected a list, tuple or dict, got %s" % sg_filter
            )

    return conditions


def _translate_filters_simple(sg_filter):
    condition = {"path": sg_filter[0], "relation": sg_filter[1]}

    values = sg_filter[2:]
    if len(values) == 1 and isinstance(values[0], (list, tuple)):
        values = values[0]

    # Payload optimization: Do not send a full object
    # just send the `type` and `id` when combining related queries
    global SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION
    if (
        not SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION
        and condition["path"] != "id"
        and condition["relation"] in ["is", "is_not", "in", "not_in"]
        and isinstance(values[0], dict)
    ):
        values = [_optimize_filter_field(v) for v in values]

    condition["values"] = values

    return condition


def _optimize_filter_field(
    field_value: Union[Dict[str, Any], List], recursive: bool = True
) -> Union[Dict, List]:
    """
    For an FPT entity, returns a new dictionary with only the type,
    id, and other allowed keys.
    If case of any processing error, the original dictionary is returned.

    At least `type` and `id` keys are required to do the optimization
    """
    allowed_keys = {
        "id",
        "type",
        "url",
        "name",
        "content_type",
        "local_path",
        "storage",
        "relative_path",
    }
    if isinstance(field_value, dict) and "id" in field_value and "type" in field_value:
        return {key: field_value[key] for key in allowed_keys if key in field_value}

    elif recursive and isinstance(field_value, list):
        return [_optimize_filter_field(fv, recursive=False) for fv in field_value]

    return field_value
