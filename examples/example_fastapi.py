import logging.config

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse, PlainTextResponse

from log_correlation_asgi import LogCorrelationMiddleware


def _get_username(headers, user):
    if user:
        return user
    auth = headers.get("authentication")
    return auth


app = FastAPI()
app.add_middleware(
    LogCorrelationMiddleware,
    service_name="MyService",
    correlation_id_header="span_id",
    get_remote_addr="remoteaddr",
    get_username=_get_username,
    logger_name="middleware_logger",
)


@app.get("/json/")
async def get_json():
    return JSONResponse(content={"test": 1})


@app.get("/plain/")
async def get_plain():
    return PlainTextResponse(content="yep text plain")


@app.websocket("/ws/")
async def get_ws(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"test": 1})
    await websocket.close()


logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(asctime)s %(levelname)s %(service_name)s %(request_id)s %(correlation_id)s %(ip_address)s "
            "%(user)s %(method)s %(path)s %(message)s %(query_string)s %(body)s",
        },
    },
    "filters": {
        "log_correlation_filter": {
            "()": "log_correlation_asgi.ContextDataFilter",
        },
    },
    "handlers": {
        "console": {
            "filters": ["log_correlation_filter"],
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "": {"level": "INFO"},
        "middleware_logger": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "app": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}
logging.config.dictConfig(logging_config)
