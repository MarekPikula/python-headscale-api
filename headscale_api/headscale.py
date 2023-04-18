"""Headscale API abstraction."""

__authors__ = ["Marek Pikuła <marek@serenitycode.dev>"]

import json
import logging
from dataclasses import asdict, dataclass
from json import JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

import requests
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

    def to_reponse(self) -> Response:
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
        return self.to_reponse()


MessageT = TypeVar("MessageT", bound=Message)
"""Message type for Headscale._unary_unary() function."""


class Headscale(model.HeadscaleServiceStub):
    """Headscale API abstraction."""

    def __init__(  # pylint: disable=super-init-not-called,too-many-arguments
        self,
        base_url: str,
        api_key: Optional[str] = None,
        requests_timeout: float = 10,
        raise_exception_on_error: bool = True,
        logger: Union[logging.Logger, int] = logging.INFO,
    ):
        """Initialize Headscale API.

        Arguments:
            base_url -- base API URL (without `/api/v1`).

        Keyword Arguments:
            api_key -- API key, which can be overriden later (default: {None})
            requests_timeout -- request timeout in seconds (default: {10})
            raise_exception_on_error -- raise exception in error (eiher internal or from
                the API). Otherwise, return Flask-compatible response tuple
                (default: {True})
            logger -- logger to use or default logging level
                (default: {logging.INFO})
        """
        self._base_url = base_url
        self._api_key = api_key
        self.timeout = requests_timeout
        self.raise_exception_on_error = raise_exception_on_error
        if isinstance(logger, logging.Logger):
            self._logger = logger
        else:
            logging.basicConfig(level=logger)
            self._logger = logging.getLogger(__name__)

    @property
    def api_key(self) -> Optional[str]:
        """Get API key if saved.

        Can be overriden in child class.
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
        response = requests.get(
            f"{self._base_url}/api/v1/apikey",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {new_api_key}",
            },
            timeout=self.timeout,
        )
        return response.status_code == 200

    @property
    def base_url(self):
        """Get base URL of the Headscale server."""
        return self._base_url

    @property
    def health_url(self) -> str:
        """Get health check URL of the Headscale server."""
        return f"{self.base_url}/health"

    async def health_check(self) -> bool:
        """Perform a health check.

        Returns True if check passed.
        """
        return requests.get(self.health_url, timeout=self.timeout).status_code == 200

    async def _unary_unary(  # type: ignore
        self,
        route: str,
        request: Message,
        response_type: Type[MessageT],
        *,
        timeout: Optional[Any] = None,
        deadline: Optional[Any] = None,
        metadata: Optional[Any] = None,
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

        request_dict: Dict[str, Any] = request.to_dict()  # type: ignore
        self._logger.info(endpoint.logger_start_message.format_map(request_dict))

        api_url = endpoint.api_url.format_map(request_dict)
        response = requests.request(
            endpoint.request_type,
            f"{self._base_url}{api_url}",
            params=request_dict,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=self.timeout if timeout is None else timeout,
        )

        def error_message():
            message = (
                endpoint.logger_fail_message.format_map(request_dict)
                if endpoint.logger_fail_message is not None
                else f'Request to "{api_url}" failed.'
            ) + f" ({response.status_code})"  # type: ignore
            self._logger.error(message)
            return message

        if response.status_code != 200:
            error_message()
            try:
                return ResponseError(
                    http_code=response.status_code, **response.json()
                ).raise_or_respond(self.raise_exception_on_error)
            except JSONDecodeError as error:
                return ResponseError(
                    response.status_code, None, response.content.decode(), []
                ).raise_or_respond(self.raise_exception_on_error, error)

        try:
            response_parsed: MessageT = response_type.from_dict(  # type: ignore
                response.json()
            )
        except (JSONDecodeError, AssertionError, ValueError) as error:
            return ResponseError(500, 0, error_message(), []).raise_or_respond(
                self.raise_exception_on_error, error
            )

        if endpoint.logger_success_message is not None:
            self._logger.info(
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
