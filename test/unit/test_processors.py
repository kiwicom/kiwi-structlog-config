from decimal import Decimal
from unittest.mock import MagicMock, patch

import freezegun
import pytest
import structlog

from kw.structlog_config import processors as uut


@pytest.fixture(autouse=True)
def clear_contextvars():
    """Clear structlog contextvars before and after each test.

    datadog_tracer_injection now mutates global contextvars state,
    so tests must start from a clean slate and not leak into each other.
    """
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


@pytest.mark.parametrize(
    "value, expected",
    (
        (1.1119, "1.112"),
        (Decimal("1.1119"), "1.112"),
    ),
)
def test_numeric_rounder(value, expected):
    event_dict = {"value": value}
    result = uut.numeric_rounder(None, None, event_dict)
    assert str(result["value"]) == expected


@freezegun.freeze_time("2018-01-01")
def test_unix_timestamper():
    result = uut.unix_timestamper(None, None, {})
    assert str(result["timestamp"]) == "1514764800.0"


@pytest.mark.parametrize(
    "key, value, expected",
    (
        ("visa", "4321000088881234", "************1234"),
        ("amex", "341200008881234", "************1234"),
        ("passenger", "Hubert Bonisseur de La Bath", "H*** B*** d*** L*** B***"),
        ("noop", "James Bond", "James Bond"),
    ),
)
def test_anonymize(key, value, expected):
    CARD_NUMBER = ({"visa", "amex"}, r"\d+(\d{4})", "*" * 12 + r"\1")
    NAME = ({"passenger"}, r"(\w)\w*", r"\1***")
    anonymize = uut.Anonymize(patterns=[CARD_NUMBER, NAME])

    result = anonymize(None, None, {key: value})
    assert result[key] == expected


@pytest.fixture
def fake_ddtrace_context():
    """Inject a fake ddtrace module so tests run without ddtrace installed."""
    fake_ddtrace = MagicMock()
    with patch.object(uut, "ddtrace", fake_ddtrace):
        yield fake_ddtrace.tracer


def test_datadog_tracer_injection_with_active_span_ddtrace_3_10(fake_ddtrace_context):
    """ddtrace >= 3.10 returns keys with 'dd.' prefix."""
    fake_ddtrace_context.get_log_correlation_context.return_value = {
        "dd.trace_id": "123456789",
        "dd.span_id": "987654321",
        "dd.env": "production",
        "dd.service": "mambo",
        "dd.version": "abc123",
    }
    result = uut.datadog_tracer_injection(None, None, {})
    assert result["dd.trace_id"] == "123456789"
    assert result["dd.span_id"] == "987654321"
    assert result["dd.env"] == "production"
    assert result["dd.service"] == "mambo"
    assert result["dd.version"] == "abc123"


def test_datadog_tracer_injection_with_active_span_ddtrace_old(fake_ddtrace_context):
    """ddtrace < 3.10 returns keys without 'dd.' prefix."""
    fake_ddtrace_context.get_log_correlation_context.return_value = {
        "trace_id": "123456789",
        "span_id": "987654321",
        "env": "production",
        "service": "mambo",
        "version": "abc123",
    }
    result = uut.datadog_tracer_injection(None, None, {})
    assert result["dd.trace_id"] == "123456789"
    assert result["dd.span_id"] == "987654321"
    assert result["dd.env"] == "production"
    assert result["dd.service"] == "mambo"
    assert result["dd.version"] == "abc123"


def test_datadog_tracer_injection_no_span_does_not_overwrite(fake_ddtrace_context):
    """When no span is active, '0' values must not overwrite existing event_dict values."""
    fake_ddtrace_context.get_log_correlation_context.return_value = {
        "dd.trace_id": "0",
        "dd.span_id": "0",
        "dd.env": "",
        "dd.service": "",
        "dd.version": "",
    }
    event_dict = {"dd.trace_id": "real_trace", "dd.span_id": "real_span"}
    result = uut.datadog_tracer_injection(None, None, event_dict)
    assert result["dd.trace_id"] == "real_trace"
    assert result["dd.span_id"] == "real_span"


def test_datadog_tracer_injection_no_span_no_existing_values(fake_ddtrace_context):
    """When no span and no existing values, nothing is injected."""
    fake_ddtrace_context.get_log_correlation_context.return_value = {
        "dd.trace_id": "0",
        "dd.span_id": "0",
        "dd.env": "",
        "dd.service": "",
        "dd.version": "",
    }
    result = uut.datadog_tracer_injection(None, None, {})
    assert "dd.trace_id" not in result
    assert "dd.span_id" not in result


def test_datadog_tracer_injection_caches_ids_in_contextvars(fake_ddtrace_context):
    """With an active span, ids land in event dict and in structlog.contextvars."""
    fake_ddtrace_context.get_log_correlation_context.return_value = {
        "dd.trace_id": "111",
        "dd.span_id": "222",
        "dd.env": "production",
        "dd.service": "mambo",
        "dd.version": "abc123",
    }
    result = uut.datadog_tracer_injection(None, None, {})
    assert result["dd.trace_id"] == "111"
    assert result["dd.span_id"] == "222"
    bound = structlog.contextvars.get_contextvars()
    assert bound["dd.trace_id"] == "111"
    assert bound["dd.span_id"] == "222"


def test_datadog_tracer_injection_restores_ids_after_span_closes(fake_ddtrace_context):
    """Two sequential calls — real ids then placeholders — second call still gets real ids."""
    fake_ddtrace_context.get_log_correlation_context.return_value = {
        "dd.trace_id": "111",
        "dd.span_id": "222",
        "dd.env": "production",
        "dd.service": "mambo",
        "dd.version": "abc123",
    }
    uut.datadog_tracer_injection(None, None, {})

    fake_ddtrace_context.get_log_correlation_context.return_value = {
        "dd.trace_id": "0",
        "dd.span_id": "0",
        "dd.env": "",
        "dd.service": "",
        "dd.version": "",
    }
    result = uut.datadog_tracer_injection(None, None, {})
    assert result["dd.trace_id"] == "111"
    assert result["dd.span_id"] == "222"


def test_datadog_tracer_injection_no_leak_after_clear(fake_ddtrace_context):
    """After clear_contextvars, a placeholder-only call yields no trace id."""
    fake_ddtrace_context.get_log_correlation_context.return_value = {
        "dd.trace_id": "111",
        "dd.span_id": "222",
        "dd.env": "production",
        "dd.service": "mambo",
        "dd.version": "abc123",
    }
    uut.datadog_tracer_injection(None, None, {})

    structlog.contextvars.clear_contextvars()

    fake_ddtrace_context.get_log_correlation_context.return_value = {
        "dd.trace_id": "0",
        "dd.span_id": "0",
        "dd.env": "",
        "dd.service": "",
        "dd.version": "",
    }
    result = uut.datadog_tracer_injection(None, None, {})
    assert "dd.trace_id" not in result
    assert "dd.span_id" not in result
