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

    Handles both ddtrace < 3.10 (keys without ``dd.`` prefix) and
    ddtrace >= 3.10 (keys with ``dd.`` prefix).  When no span is active,
    ``get_log_correlation_context()`` returns the string ``"0"`` for
    trace_id/span_id — which is truthy — so we explicitly skip those to
    avoid overwriting values already present in ``event_dict`` (e.g. bound
    via structlog contextvars while the span was still active).
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

        for source_key, dest_key in mapping.items():
            value = context.get(source_key)
            # Skip "0" (no active span) and empty strings so we don't
            # overwrite values already in event_dict from contextvars.
            if value and value != "0":
                event_dict[dest_key] = value

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
