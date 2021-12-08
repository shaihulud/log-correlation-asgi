# Log Correlation ASGI

ASGI middleware and a set of filters to trace requests between microservices.

Log Correlation ASGI aims to help you and your QA team in case you have a pipeline
of microservices with request transmitting from one to another.

For every incoming request Log Correlation ASGI checks request headers for correlation
header and logs your request and response with that identifier. Also, it allows you
easily to add that header to all outgoing requests you make.


## Installation

Log Correlation ASGI can be installed by running

    pip install log-correlation-asgi

It requires Python 3.6+ to run.

## Usage

For a quick dive you can see an example from `examples/example_fastapi.py`.
You can run it with

    uvicorn examples.example_fastapi:app

Before running example you should install:

    pip install fastapi uvicorn websockets httpx

The usage is simple. You should create a middleware and add it to your ASGI
application:

```python
from log_correlation_asgi import LogCorrelationMiddleware


CORRELATION_ID_HEADER_NAME = "correlation_id"  # how you name your header

asgi_application.add_middleware(  # FastAPI syntax
    LogCorrelationMiddleware,
    correlation_id_header=CORRELATION_ID_HEADER_NAME,
    get_remote_addr="remoteaddr",
    logger_name="some_logger",
)
```

add a filter and desired fields to log:

```python
import logging.config


logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            # Here we add %(correlation_id)s %(ip_address)s %(user)s %(method)s %(path)s %(query_string)s %(body)s fields
            "fmt": "%(asctime)s %(levelname)s %(correlation_id)s %(ip_address)s "
            "%(user)s %(method)s %(path)s %(message)s %(query_string)s %(body)s",
        },
    },
    "filters": {  # Add filter
        "log_correlation_filter": {
            "()": "log_correlation_asgi.ContextDataFilter",
        },
    },
    "handlers": {
        "console": {
            "filters": ["log_correlation_filter"],  # And use it
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "middleware_logger": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}
logging.config.dictConfig(logging_config)
```

That's all!

if you start the server and make a request to some view, in your console you will see
something like the following log:

```console
2021-12-08 03:14:15,926 INFO 7c7bffaa-5bba-48e3-bc42-02423818c2a4 - test_user GET /some/path/ Got request {"q": ["Life", "Universe", "Everything"]} -
2021-12-08 03:14:15,926 INFO 7c7bffaa-5bba-48e3-bc42-02423818c2a4 - test_user GET /some/path/ Sent response - 42
```

If you make an outgoing request from your code, it is easy to add correlation id further:

```python
import httpx
from log_correlation_asgi import get_logging_dict


CORRELATION_ID_HEADER_NAME = "correlation_id"  # how you name your header

@app.get("/plain/")
async def get_plain():
    # get if of current request
    headers = {CORRELATION_ID_HEADER_NAME: get_logging_dict()["correlation_id"]}

    # and send it further
    async with httpx.AsyncClient(base_url="http://example.com", headers=headers) as client:
        await client.get("/external/request/")
    ...
```

## Documentation

The module defines the following items:

#### class LogCorrelationMiddleware
```python
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
```

Creates an ASGI correlation middleware instance. Adds new attributes to your logs format:
- %(service_name)s - Name of service.
- %(correlation_id)s - ID unique between different microservices.
- %(request_id)s - UUID of current request unique only for this microservice.
- %(method)s - HTTP method of current request.
- %(path)s - Path part of URL.
- %(body)s - Body of the request or response.
- %(query_string)s - Query string part of request.
- %(ip_address)s - User IP address.
- %(user)s - User that made the request.

#### def get_logging_dict() -> dict

Returns a dictionary containing mentioned above request-specific data.

#### class ContextDataFilter

Filter class to add mentioned above request-specific data to logs.
