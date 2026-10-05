"""Bounded FRED/ALFRED observations with caller-reviewed availability policy.

FRED date-level real-time intervals do not establish intraday publication times.
The required policy supplies usable timestamps and externally assessed quality.
A preserved interval may be clipped by the request; its end is not proof of the
next actual revision time. Raw responses remain the authoritative evidence.
As a validation convention (not a FRED-supplied publication timezone), the
availability lower-bound guard uses America/New_York and rejects instants
before local midnight on the vintage start. This is only
a necessary bound: unknown release-time delays/next-session treatment remain
the responsibility of the caller-reviewed availability policy.
"""
from datetime import date, datetime
import json
import re
from typing import Callable, Iterable
from zoneinfo import ZoneInfo
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from quant_dca.types import Observation, QualityTier, Region
from .base import RawStore, bounded_interval


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _send(url, params, *, allow_redirects):
    if allow_redirects is not False:
        raise ValueError('Redirects prohibited')
    try:
        with build_opener(_NoRedirect()).open(Request(url + '?' + urlencode(params)), timeout=30) as response:
            return response.status, response.read()
    except HTTPError as error:
        # Do not expose exception URL containing the API credential.
        return error.code, b''
    except Exception:
        raise RuntimeError('FRED transport failed; request details suppressed') from None


class BoundedFREDTransport:
    def __init__(self, *, api_key: str, sender=None):
        if not api_key:
            raise ValueError('FRED API key required')
        self._api_key = api_key
        self._sender = sender or _send

    def observations(self, series_id, start, end, vintage_start, vintage_end) -> bytes:
        # All authorization checks happen before sender invocation.
        bounded_interval(start, end)
        bounded_interval(vintage_start, vintage_end)
        if not isinstance(series_id, str) or not re.fullmatch(r'[A-Za-z0-9_]+', series_id):
            raise ValueError('Invalid series ID')
        params = dict(series_id=series_id, observation_start=start, observation_end=end,
                      realtime_start=vintage_start, realtime_end=vintage_end,
                      output_type='1', file_type='json', limit='100000', offset='0', api_key=self._api_key)
        status, payload = self._sender('https://api.stlouisfed.org/fred/series/observations', params, allow_redirects=False)
        if status != 200:
            raise ValueError(f'FRED response status {status}; no redirect or retry performed')
        return payload


class FREDProvider:
    def __init__(self, *, series_id: str, vintage_start: str, vintage_end: str,
                 transport: BoundedFREDTransport, raw_store: RawStore,
                 availability_quality_policy: Callable[[dict], tuple[datetime, QualityTier]]):
        if not callable(availability_quality_policy):
            raise ValueError('Caller-reviewed availability/quality policy required')
        bounded_interval(vintage_start, vintage_end)
        self.series_id, self.vintage_start, self.vintage_end = series_id, vintage_start, vintage_end
        self.transport, self.raw_store, self.policy = transport, raw_store, availability_quality_policy

    def fetch(self, domain: str, start: str, end: str) -> Iterable[dict]:
        if domain != 'us_macro_vintages':
            raise ValueError('Unsupported FRED domain')
        bounded_interval(start, end)
        bounded_interval(self.vintage_start, self.vintage_end)
        raw = self.transport.observations(self.series_id, start, end, self.vintage_start, self.vintage_end)
        document = json.loads(raw)
        rows = document['observations']
        self.raw_store.persist(raw, provider='fred_alfred', domain=domain, row_count=len(rows))
        if document.get('count') != len(rows) or document.get('offset') != 0:
            raise ValueError('Incomplete FRED response; pagination not implemented')
        for field, expected in [('observation_start', start), ('observation_end', end), ('realtime_start', self.vintage_start), ('realtime_end', self.vintage_end)]:
            if document.get(field) != expected:
                raise ValueError('FRED response bounds differ from requested bounds')
        for row in rows:
            self._validate_row(row)
            if not start <= row['date'] <= end:
                raise ValueError('FRED observation outside request bounds')
        for row in rows:
            yield dict(row, series_id=self.series_id)

    def _validate_row(self, row):
        bounded_interval(row['date'], row['date'])
        bounded_interval(row['realtime_start'], row['realtime_end'])
        if not self.vintage_start <= row['realtime_start'] <= row['realtime_end'] <= self.vintage_end:
            raise ValueError('FRED vintage outside request bounds')

    def normalize(self, domain: str, rows: Iterable[dict]) -> Iterable[Observation]:
        if domain != 'us_macro_vintages':
            raise ValueError('Unsupported FRED domain')
        for row in rows:
            self._validate_row(row)
            if row.get('series_id', self.series_id) != self.series_id:
                raise ValueError('FRED series mismatch')
            available_at, quality = self.policy(dict(row))
            if not isinstance(available_at, datetime) or available_at.tzinfo is None or available_at.utcoffset() is None:
                raise ValueError('Policy must supply timezone-aware availability')
            if available_at.astimezone(ZoneInfo('America/New_York')).date() < date.fromisoformat(row['realtime_start']):
                raise ValueError('Availability precedes vintage start')
            if not isinstance(quality, QualityTier):
                raise ValueError('Policy must supply explicit QualityTier')
            yield Observation(series=self.series_id, entity_id=None, observation_date=row['date'],
                value=None if row['value'] == '.' else float(row['value']), source='fred_alfred',
                available_at=available_at, quality=quality, region=Region.US,
                revision_id=f"{row['realtime_start']}/{row['realtime_end']}",
                vintage_start=row['realtime_start'], vintage_end=row['realtime_end'])
