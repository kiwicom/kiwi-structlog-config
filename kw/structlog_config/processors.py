"""Contains ``structlog`` event processors."""
from __future__ import absolute_import, print_function

from decimal import Decimal
from time import time

import structlog

try:
    from ddtrace.helpers import get_correlation_ids
except ImportError:
    get_correlation_ids = None


def numeric_rounder(_, __, event_dict):
    """Round any floats in ``event_dict`` to 3 decimal places."""
    for key, value in event_dict.items():
        if isinstance(value, (float, Decimal)):
            event_dict[key] = round(value, 3)
    return event_dict


def drop_debug_logs(_, __, event_dict):
    """Drop event with ``debug`` log level."""
    if event_dict['level'] == 'debug':
        raise structlog.DropEvent
    return event_dict


def unix_timestamper(_, __, event_dict):
    """Add curent timestamp to event."""
    event_dict['timestamp'] = time()
    return event_dict


def process_stdlib_logging(_, __, event_dict):
    """Move standard logging message to ``message`` field and change ``event`` to desired event name."""
    event_dict['message'] = event_dict['event']
    event_dict['event'] = 'stdlib_log'
    return event_dict


def add_structlog_context(_, __, event_dict):
    """Update ``event_dict`` with context of the ``structlog`` logger."""
    event_dict.update(structlog.get_logger()._context._dict)
    return event_dict


def datadog_tracer_injection(_, __, event_dict):
    """Propagate trace ids for Datadog."""
    if get_correlation_ids is None:
        # Do nothing if ddtrace module is not available.
        return event_dict

    # Hack to prevent infinite loop in asyncio event loop creation in debug log-level
    # https://github.com/DataDog/dd-trace-py/issues/1003
    if event_dict["level"] == "debug" and event_dict.get('logger') == 'asyncio':
        return event_dict

    trace_id, span_id = get_correlation_ids()
    if trace_id and span_id:
        event_dict['dd.trace_id'] = trace_id
        event_dict['dd.span_id'] = span_id
    return event_dict
