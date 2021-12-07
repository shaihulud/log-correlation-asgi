import logging

from log_correlation_asgi.middleware import get_logging_dict, LOGGED_FIELDS


class ContextDataFilter(logging.Filter):  # pylint: disable=R0903
    """Filter to add context data to logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        logging_data_dict = get_logging_dict()

        for key, val in logging_data_dict.items():
            if not hasattr(record, key):
                setattr(record, key, val or "-")

        for key in LOGGED_FIELDS:
            val = getattr(record, key, None)
            if val is None:
                setattr(record, key, "-")

        return True
