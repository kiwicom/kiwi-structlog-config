from decimal import Decimal

import freezegun
import pytest
import structlog

from kw.structlog_config import processors as uut


@pytest.fixture(autouse=True)
def clear_structlog_contextvars():
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


def test_datadog_tracer_injection_binds_active_trace(mocker):
    mocker.patch.object(
        uut,
        "ddtrace",
        mocker.Mock(
            tracer=mocker.Mock(
                get_log_correlation_context=mocker.Mock(
                    return_value={
                        "dd.trace_id": "abc123",
                        "dd.span_id": "def456",
                        "dd.env": "staging",
                        "dd.service": "mambo",
                        "dd.version": "1",
                    }
                )
            )
        ),
    )

    result = uut.datadog_tracer_injection(None, "info", {"event": "in_request"})

    assert result["dd.trace_id"] == "abc123"
    assert result["dd.span_id"] == "def456"
    assert structlog.contextvars.get_contextvars() == {"dd.trace_id": "abc123", "dd.span_id": "def456"}


def test_datadog_tracer_injection_restores_bound_trace_after_span_closes(mocker):
    structlog.contextvars.bind_contextvars(**{"dd.trace_id": "abc123", "dd.span_id": "def456"})
    mocker.patch.object(
        uut,
        "ddtrace",
        mocker.Mock(
            tracer=mocker.Mock(
                get_log_correlation_context=mocker.Mock(
                    return_value={"dd.trace_id": "0", "dd.span_id": "0"},
                )
            )
        ),
    )

    result = uut.datadog_tracer_injection(None, "info", {"event": "response"})

    assert result["dd.trace_id"] == "abc123"
    assert result["dd.span_id"] == "def456"


def test_datadog_tracer_injection_ignores_zero_active_trace(mocker):
    mocker.patch.object(
        uut,
        "ddtrace",
        mocker.Mock(
            tracer=mocker.Mock(
                get_log_correlation_context=mocker.Mock(
                    return_value={"dd.trace_id": "0", "dd.span_id": "0"},
                )
            )
        ),
    )

    result = uut.datadog_tracer_injection(None, "info", {"event": "response"})

    assert "dd.trace_id" not in result
    assert "dd.span_id" not in result
