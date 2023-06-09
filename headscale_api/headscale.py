"""Headscale API abstraction."""

__authors__ = ["Marek Pikuła <marek@serenitycode.dev>"]
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from multiprocessing import Lock
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

import aiohttp
from betterproto import Message

from .endpoints import ENDPOINTS, Endpoint
from .schema.headscale import v1 as model

Response = Tuple[str, int]
"""Response in form acceptable by Flask.

`(response: str, status: int)`
"""


@dataclass
class ResponseError(RuntimeError):
    """Error response from Headscale."""

    http_code: int
    """HTTP code of error."""

    code: Optional[int]
    """Error code from server."""

    message: str
    """Error message."""

    details: List[str]
    """Error details."""

    def __str__(self) -> str:  # noqa
        return f"Response (code {self.code}): {self.message}"

    def to_response(self) -> Response:
        """Make a Flask-compatible error response."""
        return json.dumps(asdict(self)), self.http_code

    def raise_or_respond(
        self, raise_exception: bool, source_exception: Optional[BaseException] = None
    ) -> "Response":
        """Raise exception or gracefully return response.

        Arguments:
            raise_exception -- raise exception instead of gracefully returning.
            source_exception -- exception which triggered this error.

        Raises:
            ResponseError: if `raise_exception` is set.

        Returns:
            Flask-compatible response if `raise_exception` is False.
        """
        if raise_exception:
            raise self from source_exception
        return self.to_response()


class UnauthorizedError(PermissionError):
    """The request resulted in unauthorized error response."""


MessageT = TypeVar("MessageT", bound=Message)
"""Message type for Headscale._unary_unary() function."""


class Headscale(
    model.HeadscaleServiceStub
):  # pylint: disable=too-many-instance-attributes
    """Headscale API abstraction."""

    class _SessionContext:
        """ClientSession context with session user counter."""

        def __init__(self, parent: "Headscale") -> None:
            self._session_lock = Lock()
            self._session: Optional[aiohttp.ClientSession] = None
            self._session_users = 0
            self._parent = parent

        async def __aenter__(self):
            """Enter Headscale API session context.

            If needed creates an `aiohttp.ClientSession`.
            """
            with self._session_lock:
                if self._session_users == 0 or self._session is None:
                    self._session = aiohttp.ClientSession(self._parent.base_url)
                self._session_users += 1
            return self._session

        async def __aexit__(self, *err: Any):
            """Exit Headscale API session context.

            If session is not used by any context, the session is closed and removed.
            """
            with self._session_lock:
                self._session_users -= 1
                if self._session_users == 0 and self._session is not None:
                    await self._session.close()
                    self._session = None

    def __init__(  # pylint: disable=super-init-not-called,too-many-arguments
        self,
        base_url: str,
        api_key: Optional[str] = None,
        requests_timeout: float = 10,
        raise_exception_on_error: bool = True,
        raise_unauthorized_error: bool = True,
        logger: Union[logging.Logger, int] = logging.INFO,
    ):
        """Initialize Headscale API.

        Arguments:
            base_url -- base API URL (without `/api/v1`).

        Keyword Arguments:
            api_key -- API key, which can be overridden later (default: {None})
            requests_timeout -- request timeout in seconds (default: {10})
            raise_exception_on_error -- raise exception in error (either internal or
                from the API). Otherwise, return Flask-compatible response tuple
                (default: {True})
            raise_unauthorized_error -- raise a special UnauthorizedError exception on
                unauthorized status. If False falls back to `raise_exception_on_error`
                behaviour (default: {True})
            logger -- logger to use or default logging level
                (default: {logging.INFO})
        """
        self._base_url = base_url
        self._api_key = api_key
        self.timeout = requests_timeout
        self.raise_exception_on_error = raise_exception_on_error
        self.raise_unauthorized_error = raise_unauthorized_error
        self.logger = logger
        self._session = self._SessionContext(self)

    @property
    def logger(self):
        """Get logger used by the API abstraction."""
        return self._logger

    @logger.setter
    def logger(self, logger: Union[logging.Logger, int]):
        if isinstance(logger, logging.Logger):
            self._logger = logger
        else:
            logging.basicConfig(level=logger)
            self._logger = logging.getLogger(__name__)

    @property
    def session(self):
        """Get session context (async).

        Can be used to ensure persistent HTTP session with the API for subsequent
        requests, e.g.:

        ```
        async with headscale.session:
            await headscale.health_check()
            await headscale.test_api_key()
        ```
        """
        return self._session

    @property
    def api_key(self) -> Optional[str]:
        """Get API key if saved.

        Can be overridden in child class.
        """
        return self._api_key

    @api_key.setter
    def api_key(self, new_api_key: str):
        self._api_key = new_api_key

    async def test_api_key(self, new_api_key: Optional[str] = None) -> bool:
        """Test a (new) API key.

        Keyword Arguments:
            new_api_key -- new API key, if None, test the current one (default: {None})

        Returns:
            True if the API key is authorized.
        """
        if new_api_key is None:
            new_api_key = self.api_key

        async with self.session as session, session.get(
            "/api/v1/apikey",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {new_api_key}",
            },
            timeout=self.timeout,
        ) as response:
            return response.status == 200

    async def get_api_key_info(self, api_key: str | None = None) -> model.ApiKey | None:
        """Get information about an API key.

        Keyword Arguments:
            api_key -- API key to get information about. Use current API key if None.
                Can be an API key prefix (default: {None})

        Returns:
            API key model if found. None otherwise.
        """
        if api_key is None:
            api_key = self.api_key
            if api_key is None:
                return None
        if len(api_key) < 11:
            raise ValueError("API key too short.")

        api_key = api_key[:10]
        self.logger.debug("Looking for an API Key with prefix %s...", api_key)
        for key in (await self.list_api_keys(model.ListApiKeysRequest())).api_keys:
            if api_key == key.prefix:
                self.logger.debug("Key with prefix %s found.", api_key)
                return key

        self.logger.debug("Key with prefix %s not found.", api_key)
        return None

    async def renew_api_key(
        self,
        key_to_renew: str | None = None,
        renewal_threshold: timedelta = timedelta(days=5),
        new_expiration: timedelta = timedelta(days=90),
        expire_previous_key: bool = True,
    ) -> model.ApiKey | str | None:
        """Renew an API key if needed.

        If it does, renew the key and expire the old key.

        Keyword Arguments:
            key_to_renew -- key to renew. Can be key prefix (first 11 characters). If
                None, renews the current key (default: {None})
            renewal_threshold -- how much time before expiration should the key be
                renewed (default: {timedelta(days=5)})
            new_expiration -- how long should the new key be valid
                (default: {timedelta(days=90)})
            expire_previous_key -- expire the previous key after renewal
                (default: {True})

        Returns:
            API key information about the current valid key, new key or None if the
            source key doesn't exist or new key test has failed.
        """
        key_info = await self.get_api_key_info(key_to_renew)
        if key_info is None:
            self._logger.warning("Current key has not been found.")
            return None

        delta = key_info.expiration - datetime.now(timezone.utc)

        if delta > renewal_threshold:
            return key_info

        self._logger.warning(
            "Key is about to expire. Delta is %s. Renewing...", str(delta)
        )
        new_key = await self.create_api_key(
            model.CreateApiKeyRequest(datetime.today() + new_expiration)
        )
        self._logger.info("Renewed API key prefix: %s", new_key.api_key[:10])

        if not await self.test_api_key(new_key.api_key):
            self._logger.error("API key test failed.")
            return None

        if key_to_renew is None:
            self._logger.info("The new key is valid. Saving to configuration.")
            try:
                self.api_key = new_key.api_key
            except Exception as error:  # pylint: disable=broad-exception-caught
                # We want to be extra sure that the new key has been stored. Since
                # `api_key` is a property, its behaviour might be changed in children
                # class and thus there is an option that it will raise an exception.
                self.logger.error("Failed to save the new key: %s", error)
                return None

        if expire_previous_key:
            self.logger.debug("Expiring the previous key.")
            await self.expire_api_key(model.ExpireApiKeyRequest(key_info.prefix))
            self.logger.info("Previous key expired.")

        return new_key.api_key

    @property
    def base_url(self):
        """Get base URL of the Headscale server."""
        return self._base_url

    async def health_check(self) -> bool:
        """Perform a health check.

        Returns True if check passed.
        """
        async with self.session as session, session.get(
            "/health", timeout=self.timeout
        ) as response:
            return response.status == 200

    async def _unary_unary(  # type: ignore
        self,
        route: str,
        request: Message,
        response_type: Type[MessageT],
        *,
        timeout: Optional[Any] = None,
        deadline: Optional[Any] = None,  # pylint: disable=unused-argument
        metadata: Optional[Any] = None,  # pylint: disable=unused-argument
    ) -> Union[MessageT, Response]:
        """Execute an unary operation on the API.

        Used by HeadscaleServiceStub functions.
        """
        try:
            endpoint = ENDPOINTS[route]
            assert isinstance(endpoint, Endpoint)
        except KeyError as error:
            raise NotImplementedError(
                f'Route "{error.args[0]}" not supported. Contact the module maintainer.'
            ) from error

        request_dict: Dict[str, Any] = request.to_dict(  # type: ignore
            include_default_values=True
        )
        self.logger.info(endpoint.logger_start_message.format_map(request_dict))

        api_url = endpoint.api_url.format_map(request_dict)
        async with self.session as session, session.request(
            endpoint.request_type,
            api_url,
            params=request_dict if endpoint.request_type == "GET" else None,
            json=request_dict if endpoint.request_type != "GET" else None,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=self.timeout if timeout is None else timeout,
        ) as response:

            def error_message():
                message = (
                    endpoint.logger_fail_message.format_map(request_dict)
                    if endpoint.logger_fail_message is not None
                    else f'Request to "{api_url}" failed.'
                ) + f" ({response.status})"
                self.logger.error(message)
                return message

            if response.status != 200:
                error_message()
                # Unauthorized error special handling.
                if (
                    self.raise_unauthorized_error
                    and (await response.read()).decode() == "Unauthorized"
                ):
                    raise UnauthorizedError()

                try:
                    # Try to parse the response as JSON.
                    return ResponseError(
                        http_code=response.status, **(await response.json())
                    ).raise_or_respond(self.raise_exception_on_error)
                except JSONDecodeError as error:
                    # Otherwise return as is.
                    return ResponseError(
                        response.status, None, (await response.read()).decode(), []
                    ).raise_or_respond(self.raise_exception_on_error, error)

            try:
                response_parsed: MessageT = response_type.from_dict(  # type: ignore
                    await response.json()
                )
            except (JSONDecodeError, AssertionError, ValueError) as error:
                return ResponseError(500, 0, error_message(), []).raise_or_respond(
                    self.raise_exception_on_error, error
                )

            if endpoint.logger_success_message is not None:
                self.logger.info(
                    endpoint.logger_success_message.format_map(
                        dict(request_dict, **response_parsed.to_dict())  # type: ignore
                    )
                )
            return response_parsed  # type: ignore

    async def _unary_stream(  # type: ignore
        self,
        route: str,
        request: Any,
        response_type: Any,
        *,
        timeout: Optional[float] = None,
        deadline: Optional[Any] = None,
        metadata: Optional[Any] = None,
    ) -> Any:
        raise NotImplementedError("Stream operation not implemented.")
