from decimal import Decimal

import freezegun
import pytest

from kw.structlog_config import processors as uut


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
