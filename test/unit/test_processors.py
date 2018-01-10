import pytest

from kw.structlog_config import processors as uut


def test_float_rounder():
    event_dict = {'float': float(1.1119), }
    result = uut.float_rounder(None, None, event_dict)
    assert str(result['float']) == '1.112'


@pytest.mark.freeze_time('2018-01-01')
def test_unix_timestamper():
    result = uut.unix_timestamper(None, None, {})
    assert str(result['timestamp']) == '1514764800.0'
