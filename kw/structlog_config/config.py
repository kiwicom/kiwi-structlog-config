"""Configures both ``structlog`` and stdlib ``logging``."""
from __future__ import absolute_import, print_function

import logging
import logging.config

import simplejson
import structlog

from .processors import (
    add_structlog_context, drop_debug_logs, numeric_rounder, process_stdlib_logging, unix_timestamper
)

# structlog configuration
PRODUCTION_PROCESSORS = [
    structlog.stdlib.add_log_level,
    drop_debug_logs,
    structlog.stdlib.PositionalArgumentsFormatter(),
    unix_timestamper,
    numeric_rounder,
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeEncoder(),
]

DEBUG_PROCESSORS = [
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    numeric_rounder,
    structlog.processors.TimeStamper('iso'),
    structlog.processors.ExceptionPrettyPrinter(),
    structlog.processors.UnicodeDecoder(),
    structlog.dev.ConsoleRenderer(pad_event=25),
]


def get_structlog_processors(debug=False, json_kwargs=None):
    """Helper method to get debug/production processors list."""
    json_kwargs = {} if json_kwargs is None else json_kwargs

    if debug:
        processors = DEBUG_PROCESSORS
    else:
        processors = PRODUCTION_PROCESSORS + [
            structlog.processors.JSONRenderer(
                serializer=simplejson.dumps, **json_kwargs
            )
        ]
    return processors


def configure_structlog(debug=False, json_kwargs=None):
    """Configure proper log processors and settings for structlog with regards to debug setting."""
    processors = get_structlog_processors(debug, json_kwargs)
    structlog.configure_once(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=structlog.threadlocal.wrap_dict(dict),
    )


def configure_stdlib_logging(debug=False, json_kwargs=None):
    """Configure standard logging to log using the same processors as structlog."""

    # Specific processors for stdlib logging
    stdlib_processors = [
        add_structlog_context,  # fill structlog logger attributes (e.g. provided to bind())
        structlog.stdlib.add_logger_name,  # fill `logger` attribute
        process_stdlib_logging  # fill `message` attribute, set `event`
    ]

    # Append structlog processors to chain
    processors = get_structlog_processors(debug, json_kwargs)
    stdlib_processors.extend(processors)

    # The last processor needs to be passed separately
    stdlib_renderer = stdlib_processors.pop(-1)

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": stdlib_renderer,
                "foreign_pre_chain": stdlib_processors,
            },
        },
        "handlers": {
            "default": {
                "level": "DEBUG" if debug else "INFO",
                "class": "logging.StreamHandler",
                "formatter": "plain",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": "DEBUG" if debug else "INFO",
                "propagate": True,
            },
        }
    })
