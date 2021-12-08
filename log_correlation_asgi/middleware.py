import json
import logging
import re
from contextvars import ContextVar
from typing import Callable, List, Optional, Pattern, Union, Any, Dict
from uuid import uuid4
from urllib.parse import parse_qs


_logging_dict_ctx_var: ContextVar[dict] = ContextVar("logging_dict", default=dict())
LOGGED_FIELDS = (
    "service_name",
    "correlation_id",
    "request_id",
    "method",
    "path",
    "body",
    "query_string",
    "ip_address",
    "user",
)


def get_logging_dict() -> dict:
    """Returns a dictionary containing request-specific data."""
    return _logging_dict_ctx_var.get()


class LogCorrelationMiddleware:  # pylint: disable=R0902, R0903
    """
    Log correlation middleware for logging requests between microservices.
    """

    def __init__(  # pylint: disable=R0913
        self,
        app,
        service_name: Optional[str] = None,
        correlation_id_header: str = "Correlation-Id",
        get_remote_addr: Union[str, Callable, None] = None,
        get_username: Optional[Callable] = None,
        logger_name: Optional[str] = None,
        excluded_paths: Optional[List[str]] = None,
        no_args_paths: Optional[List[str]] = None,
        get_request_message: Optional[str] = "Got request",
        send_response_message: Optional[str] = "Sent response",
    ) -> None:
        """
        :param app: ASGI application instance.
        :param service_name: Name of service to show in logs.
        :param correlation_id_header: Name of header whose id will be the same between microservices.
        :param get_remote_addr: Callable to get remote address from headers dict or header name (str). TODO: multi dict
        :param get_username: Callable to get remote address from headers dict or scope["user"] (if filled previously).
        :param logger_name: Name of logger used to log http/ws requests.
        :param excluded_paths: Paths that won't be logged.
        :param no_args_paths: Paths that will be logged without query string and body.
        :param get_request_message: A string to distinguish a request from a response in log.
        :param send_response_message: A string to distinguish a request from a response in log.
        """
        self.app = app
        self.service_name = service_name
        self.correlation_id_header = correlation_id_header.lower()
        self.get_remote_addr = get_remote_addr
        self.get_username = get_username
        self.logger = logging.getLogger(logger_name or __name__)

        self._excluded_paths: List[Pattern[str]]
        if excluded_paths:
            self._excluded_paths = [re.compile(path) for path in excluded_paths]
        else:
            self._excluded_paths = []

        self._no_args_paths: List[Pattern[str]]
        if no_args_paths:
            self._no_args_paths = [re.compile(path) for path in no_args_paths]
        else:
            self._no_args_paths = []

        self._get_request_message = get_request_message if get_request_message is not None else ""
        self._send_response_message = send_response_message if send_response_message is not None else ""

    async def __call__(self, scope, receive, send) -> None:
        async def proxy_receive():
            """Replaces receive to intercept messages."""
            message = await receive()

            if message["type"] == "http.request":
                body.append(message.get("body", b""))

                if not message.get("more_body", False):
                    extra = {}
                    if not is_no_args_path:
                        extra["query_string"] = query_string_to_json(scope["query_string"])
                        extra["body"] = _decode(b"".join(body))

                    self.logger.info(self._get_request_message, extra=extra)
                    body.clear()

            return message

        async def proxy_send(message) -> None:
            """Replaces send to intercept messages."""
            if message["type"] == "http.response.start":
                # Set correlation id header
                key = self.correlation_id_header.encode("latin-1")
                value = get_logging_dict()["correlation_id"].encode("latin-1")
                headers = message["headers"]
                headers.append([key, value])
            elif message["type"] == "http.response.body":
                body.append(message.get("body", b""))

                if not message.get("more_body", False):
                    extra = {}
                    if not is_no_args_path:
                        extra["body"] = _decode(b"".join(body))

                    self.logger.info(self._send_response_message, extra=extra)
                    body.clear()

            await send(message)

        # And now the async def __call__ goes.
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        logging_data_dict = {
            "service_name": self.service_name,
            "correlation_id": None,
            "request_id": str(uuid4()),
            "method": scope.get("method"),
            "path": scope.get("path"),
            "body": None,
            "query_string": None,
            "ip_address": None,
            "user": None,
        }

        _logging_data = _logging_dict_ctx_var.set(logging_data_dict)

        if any(pattern.search(scope["path"]) for pattern in self._excluded_paths):
            try:
                await self.app(scope, receive, send)
            finally:
                _logging_dict_ctx_var.reset(_logging_data)
            return

        is_no_args_path = any(pattern.search(scope["path"]) for pattern in self._no_args_paths)

        body: List[bytes] = []
        headers = headers_to_dict(scope["headers"])
        logging_data_dict["correlation_id"] = headers.get(self.correlation_id_header, str(uuid4()))

        if isinstance(self.get_remote_addr, str):
            logging_data_dict["ip_address"] = headers.get(self.get_remote_addr)
        elif callable(self.get_remote_addr):
            logging_data_dict["ip_address"] = self.get_remote_addr(headers)

        if self.get_username:
            logging_data_dict["user"] = self.get_username(headers=headers, user=scope.get("user"))

        _logging_dict_ctx_var.set(logging_data_dict)

        if not headers.get("content-length", 0):
            extra = {}
            if not is_no_args_path:
                extra["query_string"] = query_string_to_json(scope["query_string"])

            self.logger.info(self._get_request_message, extra=extra)

        try:
            await self.app(scope, proxy_receive, proxy_send)
        finally:
            _logging_dict_ctx_var.reset(_logging_data)


def headers_to_dict(scope_headers: list) -> Dict[str, Any]:
    """Converts list of tuples of headers to dict."""
    headers: Dict[str, Any] = {}
    for raw_key, raw_value in scope_headers:
        key = raw_key.decode("latin-1").lower()
        value = raw_value.decode("latin-1")
        if key in headers:
            headers[key] = headers[key] + ", " + value
        else:
            headers[key] = value
    return headers


def query_string_to_json(query_string: bytes) -> Optional[str]:
    """Converts query string to json."""
    qs_dict = parse_qs(query_string.decode("latin-1"))
    return json.dumps(qs_dict)


def _decode(data: bytes) -> str:
    """Returns string representation of data."""
    try:
        return data.decode(json.detect_encoding(data), "surrogatepass")
    except (TypeError, UnicodeDecodeError):
        return "Can not decode"
