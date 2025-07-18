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
    """Propagate trace ids for Datadog."""
    if not ddtrace:
        return event_dict

    try:
        context = ddtrace.tracer.get_log_correlation_context()

        # Safely get values with defaults
        if trace_id := context.get("trace_id"):
            event_dict["dd.trace_id"] = trace_id
        if span_id := context.get("span_id"):
            event_dict["dd.span_id"] = span_id
        if env := context.get("env"):
            event_dict["dd.env"] = env
        if service := context.get("service"):
            event_dict["dd.service"] = service
        if version := context.get("version"):
            event_dict["dd.version"] = version

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
