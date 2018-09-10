from decimal import Decimal

import pytest

from kw.structlog_config import processors as uut


@pytest.mark.parametrize("value, expected", (
    (1.1119, "1.112"),
    (Decimal("1.1119"), "1.112"),
))
def test_numeric_rounder(value, expected):
    event_dict = {"value": value}
    result = uut.numeric_rounder(None, None, event_dict)
    assert str(result["value"]) == expected


@pytest.mark.freeze_time('2018-01-01')
def test_unix_timestamper():
    result = uut.unix_timestamper(None, None, {})
    assert str(result['timestamp']) == '1514764800.0'
