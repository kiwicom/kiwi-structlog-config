"""Contains ``structlog`` event processors."""
from __future__ import absolute_import, print_function

import re
from decimal import Decimal
from time import time

import structlog

try:
    import ddtrace
except ImportError:
    ddtrace = None

_PLACEHOLDER = "0"
_TRACE_KEYS = ("dd.trace_id", "dd.span_id")


def numeric_rounder(_, __, event_dict):
    """Round any floats in ``event_dict`` to 3 decimal places."""
    for key, value in event_dict.items():
        if isinstance(value, (float, Decimal)):
            event_dict[key] = round(value, 3)
    return event_dict


def drop_debug_logs(_, __, event_dict):
    """Drop event with ``debug`` log level."""
    if event_dict["level"] == "debug":
        raise structlog.DropEvent
    return event_dict


def unix_timestamper(_, __, event_dict):
    """Add curent timestamp to event."""
    event_dict["timestamp"] = time()
    return event_dict


def process_stdlib_logging(_, __, event_dict):
    """Move standard logging message to ``message`` field and change ``event`` to desired event name."""
    event_dict["message"] = event_dict["event"]
    event_dict["event"] = "stdlib_log"
    return event_dict


def add_structlog_context(_, __, event_dict):
    """Update ``event_dict`` with context of the ``structlog`` logger."""
    if isinstance(structlog.get_logger()._context, dict):
        event_dict.update(structlog.get_logger()._context)
    else:
        event_dict.update(structlog.get_logger()._context._dict)
    return event_dict


def datadog_tracer_injection(_, __, event_dict):
    """Propagate trace ids for Datadog.

    ddtrace ships its own structlog integration that prepends a
    ``_tracer_injection`` processor at index 0.  That processor
    unconditionally writes ``dd.trace_id``/``dd.span_id`` from
    ``get_log_correlation_context()`` into the event dict — including
    the placeholder string ``"0"`` when no span is active.  Because it
    runs before us, simply *skipping* ``"0"`` is not enough: the zero is
    already in the event dict and nothing else put the real value back.

    To fix this, we **remember** real trace ids in
    ``structlog.contextvars`` while the span is alive, and **restore**
    them from contextvars when only placeholders are available (the span
    has already closed, e.g. the WSGI response log emitted in the
    outermost middleware's ``finally`` block).

    Handles both ddtrace < 3.10 (keys without ``dd.`` prefix) and
    ddtrace >= 3.10 (keys with ``dd.`` prefix).
    """
    if not ddtrace:
        return event_dict

    try:
        context = ddtrace.tracer.get_log_correlation_context()

        # ddtrace >= 3.10 uses "dd."-prefixed keys; older versions use bare keys.
        # Support both by checking each key with and without the prefix.
        mapping = {
            "dd.trace_id": "dd.trace_id",
            "trace_id": "dd.trace_id",
            "dd.span_id": "dd.span_id",
            "span_id": "dd.span_id",
            "dd.env": "dd.env",
            "env": "dd.env",
            "dd.service": "dd.service",
            "service": "dd.service",
            "dd.version": "dd.version",
            "version": "dd.version",
        }

        remembered = {}
        for source_key, dest_key in mapping.items():
            value = context.get(source_key)
            if value and value != _PLACEHOLDER:
                event_dict[dest_key] = value
                if dest_key in _TRACE_KEYS:
                    remembered[dest_key] = value

        if remembered:
            structlog.contextvars.bind_contextvars(**remembered)
        else:
            bound = structlog.contextvars.get_contextvars()
            for key in _TRACE_KEYS:
                value = bound.get(key)
                if value and value != _PLACEHOLDER:
                    event_dict[key] = value

    except Exception:
        # If anything goes wrong, just return the original event_dict
        # This prevents the logging system from breaking
        pass

    return event_dict


class Anonymize:
    r"""Anonymize personal data.

    anonymize = Anonymize(patterns=[
        ({"visa", "amex"}, r"\d+(\d{4})", "*"*12 + r"\1"),
        ({"passenger_name"}, r"(\w)\w*", r"\1***"),
    ])
    """

    def __init__(self, patterns):
        self.patterns = self.build_mapping(patterns)

    @classmethod
    def build_mapping(cls, patterns):
        """Flatten input in a dict and compile regex patterns."""
        mapping = {}
        for keys, pattern, replacement in patterns:
            regex = re.compile(pattern)
            mapping.update({key: (regex, replacement) for key in keys})
        return mapping

    def __call__(self, logger, method_name, event_dict):
        for key in set(event_dict) & set(self.patterns):
            pattern, replacement = self.patterns[key]
            event_dict[key] = re.sub(pattern, replacement, event_dict[key])
        return event_dict
