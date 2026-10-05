"""Offline exchange schedules, never weekday approximations.

Supported MICs: XNYS, XNAS, XETR, XLON, XPAR. XNAS explicitly uses the
XNYS regular-session schedule, as exchange_calendars does for its XNAS
alias. These are scheduled regular opens/closes, not guarantees of liquidity,
auction participation or security-specific halt handling.

Timestamp queries require aware datetimes and return UTC datetimes. EOD
means a scheduled close at or before the query; it does NOT assert that a
vendor's daily bar was published at that instant. Bar publication/PIT checks
remain necessary downstream. The next open is strictly after the query.

Schedules are built locally for 2009-01-01 through 2030-12-31 (inclusive),
providing a preceding-year buffer for the 2010 research boundary. This is
calendar metadata, not permission to fetch/evaluate post-2023 market data.
Out-of-range queries or absent results fail closed with ValueError.
"""
from datetime import date, datetime, timezone
from functools import lru_cache
from types import MappingProxyType

import exchange_calendars

MIC_CALENDARS = MappingProxyType({
    'XNYS': 'XNYS',
    'XNAS': 'XNYS',
    'XETR': 'XETR',
    'XLON': 'XLON',
    'XPAR': 'XPAR',
})
_START = datetime(2009, 1, 1, tzinfo=timezone.utc)
_END_EXCLUSIVE = datetime(2031, 1, 1, tzinfo=timezone.utc)


def _calendar_name(exchange: str) -> str:
    if not isinstance(exchange, str) or exchange not in MIC_CALENDARS:
        raise ValueError(f'Unsupported exchange MIC: {exchange!r}')
    return MIC_CALENDARS[exchange]


@lru_cache(maxsize=len(MIC_CALENDARS))
def _schedule(name: str):
    return exchange_calendars.get_calendar(
        name, start='2009-01-01', end='2030-12-31'
    ).schedule


def _query(exchange: str, ts: datetime):
    name = _calendar_name(exchange)
    if not isinstance(ts, datetime):
        raise TypeError('ts must be a timezone-aware datetime')
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError('ts must be a timezone-aware datetime')
    ts = ts.astimezone(timezone.utc)
    if not _START <= ts < _END_EXCLUSIVE:
        raise ValueError('Timestamp outside calendar coverage [2009, 2031)')
    return _schedule(name), ts


def previous_eligible_eod(exchange: str, ts: datetime) -> datetime:
    """Return the latest regular-session close <= ts, including early closes."""
    schedule, ts = _query(exchange, ts)
    index = schedule['close'].searchsorted(ts, side='right') - 1
    if index < 0:
        raise ValueError('Previous close unavailable within calendar coverage')
    return schedule['close'].iloc[index].to_pydatetime().astimezone(timezone.utc)


def next_eligible_open(exchange: str, ts: datetime) -> datetime:
    """Return the first regular-session open strictly > ts, even at an open."""
    schedule, ts = _query(exchange, ts)
    index = schedule['open'].searchsorted(ts, side='right')
    if index >= len(schedule):
        raise ValueError('Next open unavailable within calendar coverage')
    return schedule['open'].iloc[index].to_pydatetime().astimezone(timezone.utc)


def nth_subsequent_open(exchange: str, session: date, n: int) -> datetime:
    """Return the nth session open after an exchange-local date label.

    The baseline must be an actual session date (not a datetime or a string).
    n is a positive integer, excluding bool; n=1 excludes the baseline and
    selects the immediately following trading session. Holidays never count.
    """
    name = _calendar_name(exchange)
    if not isinstance(session, date) or isinstance(session, datetime):
        raise TypeError('session must be a date label, not a datetime')
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError('n must be a positive integer')
    if n < 1:
        raise ValueError('n must be a positive integer')
    if not _START.date() <= session < _END_EXCLUSIVE.date():
        raise ValueError('Session outside calendar coverage [2009, 2031)')
    schedule = _schedule(name)
    label = session.isoformat()
    if label not in schedule.index:
        raise ValueError(f'{session} is not a trading session for {exchange}')
    index = schedule.index.get_loc(label) + n
    if index >= len(schedule):
        raise ValueError('Subsequent open unavailable within calendar coverage')
    return schedule['open'].iloc[index].to_pydatetime().astimezone(timezone.utc)


def is_eligible_session(exchange: str, session: date) -> bool:
    """Return whether a date label is an actual scheduled exchange session."""
    name = _calendar_name(exchange)
    if not isinstance(session, date) or isinstance(session, datetime):
        raise TypeError('session must be a date label, not a datetime')
    if not _START.date() <= session < _END_EXCLUSIVE.date():
        raise ValueError('Session outside calendar coverage [2009, 2031)')
    return session.isoformat() in _schedule(name).index


def eligible_session_close(exchange: str, session: date) -> datetime | None:
    """Return an actual session close, or None when the date is not a session."""
    name = _calendar_name(exchange)
    if not isinstance(session, date) or isinstance(session, datetime):
        raise TypeError('session must be a date label, not a datetime')
    if not _START.date() <= session < _END_EXCLUSIVE.date():
        raise ValueError('Session outside calendar coverage [2009, 2031)')
    schedule = _schedule(name)
    label = session.isoformat()
    if label not in schedule.index:
        return None
    index = schedule.index.get_loc(label)
    return schedule['close'].iloc[index].to_pydatetime().astimezone(timezone.utc)


def eligible_session_open(exchange: str, session: date) -> datetime | None:
    """Return an actual session's opening instant, or None for a non-session."""
    name = _calendar_name(exchange)
    if not isinstance(session, date) or isinstance(session, datetime):
        raise TypeError('session must be a date label, not a datetime')
    if not _START.date() <= session < _END_EXCLUSIVE.date():
        raise ValueError('Session outside calendar coverage [2009, 2031)')
    schedule = _schedule(name)
    label = session.isoformat()
    if label not in schedule.index:
        return None
    index = schedule.index.get_loc(label)
    return schedule['open'].iloc[index].to_pydatetime().astimezone(timezone.utc)


def assert_session_clock(exchange: str, session_date: str,
                         opened: datetime, closed: datetime) -> None:
    """Reject missing/non-session evidence and clocks differing from schedule."""
    try:
        session = date.fromisoformat(session_date)
        actual_open = eligible_session_open(exchange, session)
        actual_close = eligible_session_close(exchange, session)
        if actual_open is None or actual_close is None:
            raise ValueError("NONEXISTENT_SESSION")
        if opened != actual_open or closed != actual_close:
            raise ValueError("SESSION_CLOCK_MISMATCH")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_SESSION_EVIDENCE:{exc}") from exc
