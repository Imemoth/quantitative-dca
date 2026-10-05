"""Literal schedule fixtures catch weekday math, DST and boundary leakage."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from quant_dca.calendars.service import (
    eligible_session_close, eligible_session_open, next_eligible_open, nth_subsequent_open,
    previous_eligible_eod,
)


def utc(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


@pytest.mark.parametrize('exchange,query,expected', [
    ('XNYS', '2023-09-01T21:00', '2023-09-05T13:30'),  # Labor Day
    ('XNAS', '2023-07-03T18:00', '2023-07-05T13:30'),  # Independence Day
    ('XETR', '2023-04-06T18:00', '2023-04-11T07:00'),  # Easter Friday/Monday
    ('XLON', '2023-05-05T17:00', '2023-05-09T07:00'),  # coronation holiday
    ('XPAR', '2023-04-06T18:00', '2023-04-11T07:00'),
    ('XNYS', '2023-07-01T00:00', '2023-07-03T13:30'),  # month starts weekend
    ('XETR', '2023-05-01T00:00', '2023-05-02T07:00'),  # month starts holiday
    ('XNYS', '2010-01-01T00:00', '2010-01-04T14:30'),
    ('XNYS', '2012-10-26T21:00', '2012-10-31T13:30'),  # Hurricane Sandy
    ('XNYS', '2023-03-10T22:00', '2023-03-13T13:30'),  # US DST starts
    ('XETR', '2023-03-10T22:00', '2023-03-13T08:00'),  # EU DST not yet
    ('XETR', '2023-03-24T22:00', '2023-03-27T07:00'),  # EU DST starts
    ('XNYS', '2023-11-03T22:00', '2023-11-06T14:30'),  # US DST ends
    ('XETR', '2023-10-27T22:00', '2023-10-30T08:00'),  # EU DST ends
    ('XNYS', '2023-09-05T13:30', '2023-09-06T13:30'),  # strictly after
    ('XNYS', '2023-09-05T13:29:59.999999', '2023-09-05T13:30'),
    ('XNYS', '2023-09-05T15:00', '2023-09-06T13:30'),  # intraday
])
def test_next_open(exchange, query, expected):
    result = next_eligible_open(exchange, utc(query))
    assert result == utc(expected)
    assert result.tzinfo == timezone.utc


@pytest.mark.parametrize('exchange,query,expected', [
    ('XNYS', '2010-01-01T00:00', '2009-12-31T21:00'),
    ('XETR', '2010-01-01T00:00', '2009-12-30T16:30'),
    ('XNYS', '2023-11-24T18:00', '2023-11-24T18:00'),  # inclusive early close
    ('XNYS', '2023-11-24T17:59:59.999999', '2023-11-22T21:00'),
    ('XNYS', '2023-09-05T15:00', '2023-09-01T20:00'),
    ('XETR', '2023-04-10T18:00', '2023-04-06T15:30'),
    ('XNYS', '2023-12-31T23:59', '2023-12-29T21:00'),
])
def test_previous_eod(exchange, query, expected):
    assert previous_eligible_eod(exchange, utc(query)) == utc(expected)


@pytest.mark.parametrize('exchange,session,n,expected', [
    ('XNYS', date(2023, 9, 1), 1, '2023-09-05T13:30'),
    ('XNYS', date(2023, 9, 1), 2, '2023-09-06T13:30'),
    ('XETR', date(2023, 4, 6), 1, '2023-04-11T07:00'),
    ('XETR', date(2023, 4, 6), 3, '2023-04-13T07:00'),
])
def test_nth_counts_sessions_strictly_after_baseline(exchange, session, n, expected):
    assert nth_subsequent_open(exchange, session, n) == utc(expected)


def test_eligible_session_open_returns_same_session_boundary():
    assert eligible_session_open('XNYS', date(2020, 1, 6)) == utc('2020-01-06T14:30')
    assert eligible_session_open('XNYS', date(2020, 1, 4)) is None


def test_aware_non_utc_input_is_the_same_instant():
    local = datetime(2023, 9, 5, 9, 30, tzinfo=ZoneInfo('America/New_York'))
    assert next_eligible_open('XNYS', local) == utc('2023-09-06T13:30')
    assert previous_eligible_eod('XNYS', local) == utc('2023-09-01T20:00')


@pytest.mark.parametrize('function', [next_eligible_open, previous_eligible_eod])
def test_rejects_naive_timestamp(function):
    with pytest.raises(ValueError, match='timezone-aware'):
        function('XNYS', datetime(2023, 1, 3))


@pytest.mark.parametrize('function', [next_eligible_open, previous_eligible_eod])
@pytest.mark.parametrize('bad', [date(2023, 1, 3), '2023-01-03', None])
def test_rejects_non_datetime_timestamp(function, bad):
    with pytest.raises(TypeError):
        function('XNYS', bad)


@pytest.mark.parametrize('mic', ['NYSE', 'xnys', 'UNKNOWN', '', None])
def test_rejects_unsupported_mic(mic):
    with pytest.raises(ValueError, match='Unsupported exchange MIC'):
        next_eligible_open(mic, utc('2023-01-03T00:00'))
    with pytest.raises(ValueError, match='Unsupported exchange MIC'):
        previous_eligible_eod(mic, utc('2023-01-03T00:00'))
    with pytest.raises(ValueError, match='Unsupported exchange MIC'):
        nth_subsequent_open(mic, date(2023, 1, 3), 1)


@pytest.mark.parametrize('n', [0, -1, 1.5, True, False, '2', None])
def test_rejects_invalid_n(n):
    with pytest.raises((TypeError, ValueError)):
        nth_subsequent_open('XNYS', date(2023, 9, 1), n)


@pytest.mark.parametrize('session', [date(2023, 9, 2), date(2023, 9, 4)])
def test_rejects_non_session_baseline(session):
    with pytest.raises(ValueError, match='not a trading session'):
        nth_subsequent_open('XNYS', session, 1)


@pytest.mark.parametrize('session', ['2023-09-01', datetime(2023, 9, 1), utc('2023-09-01T00:00'), None])
def test_baseline_is_a_date_label_not_a_timestamp(session):
    with pytest.raises(TypeError, match='date'):
        nth_subsequent_open('XNYS', session, 1)


@pytest.mark.parametrize('function', [next_eligible_open, previous_eligible_eod])
@pytest.mark.parametrize('query', ['2008-12-31T23:59', '2031-01-01T00:00'])
def test_timestamp_outside_calendar_coverage_fails(function, query):
    with pytest.raises(ValueError, match='coverage'):
        function('XNYS', utc(query))


def test_missing_result_beyond_schedule_fails():
    with pytest.raises(ValueError, match='coverage'):
        previous_eligible_eod('XNYS', utc('2009-01-01T00:00'))
    with pytest.raises(ValueError, match='coverage'):
        next_eligible_open('XNYS', utc('2030-12-31T23:59'))
    with pytest.raises(ValueError, match='coverage'):
        nth_subsequent_open('XNYS', date(2030, 12, 31), 1)


@pytest.mark.parametrize('exchange,session,expected', [
    ('XNYS', date(2022, 1, 10), '2022-01-10T21:00'),
    ('XNYS', date(2023, 11, 24), '2023-11-24T18:00'),
    ('XETR', date(2022, 1, 10), '2022-01-10T16:30'),
])
def test_eligible_session_close_returns_actual_scheduled_close(exchange, session, expected):
    assert eligible_session_close(exchange, session) == utc(expected)


def test_eligible_session_close_returns_none_for_non_session():
    assert eligible_session_close('XNYS', date(2022, 1, 8)) is None
