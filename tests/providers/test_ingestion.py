from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from quant_dca.providers.base import ProviderAdapter, RawStore
from quant_dca.providers.csv_provider import CSVProvider
from quant_dca.providers.fred import FREDProvider, BoundedFREDTransport
from quant_dca.providers.sec import SECProvider, IntegrationUnavailable
from quant_dca.types import QualityTier

NOW = datetime(2023, 4, 13, tzinfo=timezone.utc)

def policy(row):
    return NOW, QualityTier.B


def test_csv_explicit_metadata_and_immutable_raw(tmp_path):
    path = tmp_path / 'prices.csv'
    path.write_text('security_id,session_date,open,high,low,close,volume,currency,region,exchange,session_open_at,session_close_at,available_at,quality,revision_id,price_basis\nABC,2023-01-03,10,12,9,11,100,USD,US,XNYS,2023-01-03T14:30:00+00:00,2023-01-03T21:00:00+00:00,2023-01-03T21:01:00+00:00,B,r1,unadjusted\n')
    provider = CSVProvider(path, raw_store=RawStore(tmp_path / 'raw'))
    assert isinstance(provider, ProviderAdapter)
    rows = list(provider.fetch('prices', '2023-01-01', '2023-01-31'))
    bar, = provider.normalize('prices', rows)
    assert bar.source == 'csv' and bar.exchange == 'XNYS'
    assert bar.available_at.isoformat() == '2023-01-03T21:01:00+00:00'
    manifest, = (tmp_path / 'raw').glob('*.manifest.json')
    data = json.loads(manifest.read_text())
    assert data['row_count'] == 1
    assert manifest.with_name(data['source_hash'] + '.raw').read_bytes() == path.read_bytes()
    list(provider.fetch('prices', '2023-01-01', '2023-01-31'))
    assert len(list((tmp_path / 'raw').glob('*.manifest.json'))) == 1


def test_csv_refuses_guessed_metadata(tmp_path):
    path = tmp_path / 'prices.csv'
    path.write_text('ticker,date,open,close\nABC,2020-01-02,10,11\n')
    provider = CSVProvider(path, raw_store=RawStore(tmp_path / 'raw'))
    with pytest.raises(ValueError, match='explicit metadata'):
        list(provider.normalize_prices())


@pytest.mark.parametrize('bounds', [
    ('2023-01-01', '2024-01-01', '2023-01-01', '2023-12-31'),
    ('2023-01-01', '2023-12-31', '2023-01-01', '2024-01-01'),
    ('2023-02-01', '2023-01-01', '2023-01-01', '2023-12-31'),
    ('2023-01-01', '2023-12-31', '2023-02-01', '2023-01-01'),
    ('2023-01-01', '2023-12-31', None, '2023-12-31'),
])
def test_denied_bounds_never_call_transport(bounds):
    calls = []
    transport = BoundedFREDTransport(api_key='test-secret', sender=lambda *a, **k: calls.append((a, k)))
    with pytest.raises((ValueError, TypeError)):
        transport.observations('CPIAUCSL', *bounds)
    assert calls == []


def test_transport_redirects_fail_closed():
    calls = []
    def sender(url, params, *, allow_redirects):
        calls.append((url, params, allow_redirects))
        return 302, b'{}'
    transport = BoundedFREDTransport(api_key='test-secret', sender=sender)
    with pytest.raises(ValueError, match='status'):
        transport.observations('CPIAUCSL', '2023-01-01', '2023-03-31', '2023-01-01', '2023-12-31')
    assert calls[0][2] is False


def test_actual_bounded_fred_sample_replay(tmp_path):
    raw = Path('data/raw/provider_probes/FRED_CPIAUCSL_2023_sample.raw').read_bytes()
    transport = BoundedFREDTransport(api_key='test-secret', sender=lambda *a, **k: (200, raw))
    provider = FREDProvider(series_id='CPIAUCSL', vintage_start='2023-01-01', vintage_end='2023-12-31', transport=transport, raw_store=RawStore(tmp_path), availability_quality_policy=policy)
    rows = list(provider.fetch('us_macro_vintages', '2023-01-01', '2023-03-31'))
    records = list(provider.normalize('us_macro_vintages', rows))
    assert len(records) == 3 and records[0].value == 300.536
    assert records[0].vintage_start == '2023-02-14'
    assert records[0].vintage_end == '2023-12-31'
    assert records[0].published_at is None and records[0].quality == QualityTier.B
    assert 'test-secret' not in next(tmp_path.glob('*.manifest.json')).read_text()


def test_fred_policy_is_required(tmp_path):
    with pytest.raises(ValueError, match='policy'):
        FREDProvider(series_id='CPIAUCSL', vintage_start='2023-01-01', vintage_end='2023-12-31', transport=None, raw_store=RawStore(tmp_path), availability_quality_policy=None)


def test_sec_is_explicitly_unavailable():
    with pytest.raises(IntegrationUnavailable):
        list(SECProvider().fetch('us_fundamentals', '2023-01-01', '2023-12-31'))


@pytest.mark.parametrize('mutation', ['partial', 'observation', 'vintage', 'bounds'])
def test_fred_rejects_incomplete_or_out_of_bounds_responses(tmp_path, mutation):
    document = json.loads(Path('data/raw/provider_probes/FRED_CPIAUCSL_2023_sample.raw').read_bytes())
    if mutation == 'partial':
        document['count'] = 999
    elif mutation == 'observation':
        document['observations'][-1]['date'] = '2024-01-01'
    elif mutation == 'vintage':
        document['observations'][-1]['realtime_end'] = '2024-01-01'
    else:
        document['realtime_end'] = '2024-01-01'
    transport = BoundedFREDTransport(api_key='test-secret', sender=lambda *a, **k: (200, json.dumps(document).encode()))
    provider = FREDProvider(series_id='CPIAUCSL', vintage_start='2023-01-01', vintage_end='2023-12-31', transport=transport, raw_store=RawStore(tmp_path), availability_quality_policy=policy)
    with pytest.raises(ValueError):
        next(iter(provider.fetch('us_macro_vintages', '2023-01-01', '2023-03-31')))


def test_raw_integrity_violation_never_overwrites(tmp_path):
    store = RawStore(tmp_path)
    manifest = store.persist(b'evidence', provider='csv', domain='prices', row_count=1)
    metadata = json.loads(manifest.read_text())
    blob = tmp_path / (metadata['source_hash'] + '.raw')
    blob.write_bytes(b'tampered')
    with pytest.raises(ValueError, match='integrity'):
        store.persist(b'evidence', provider='csv', domain='prices', row_count=1)
    assert blob.read_bytes() == b'tampered'


def test_fred_policy_cannot_backdate_vintage(tmp_path):
    provider = FREDProvider(series_id='CPIAUCSL', vintage_start='2023-01-01', vintage_end='2023-12-31', transport=None, raw_store=RawStore(tmp_path), availability_quality_policy=lambda row: (datetime(2023, 1, 1, tzinfo=timezone.utc), QualityTier.A))
    with pytest.raises(ValueError, match='precedes'):
        list(provider.normalize('us_macro_vintages', [dict(date='2023-01-01', realtime_start='2023-02-14', realtime_end='2023-12-31', value='300')]))


def test_csv_preserves_unknown_publication(tmp_path):
    provider = CSVProvider(tmp_path / 'unused.csv', raw_store=RawStore(tmp_path / 'raw'))
    row = dict(security_id='ABC', session_date='2023-01-03', currency='USD', region='US', exchange='XNYS', session_open_at='2023-01-03T14:30:00+00:00', session_close_at='2023-01-03T21:00:00+00:00', available_at='2023-01-03T21:01:00+00:00', quality='B', revision_id='r1', price_basis='unadjusted')
    bar, = provider.normalize('prices', [row])
    assert bar.published_at is None and bar.revised_at is None


@pytest.mark.parametrize('basis', [None, '', 'vendor_adjusted'])
def test_csv_requires_supported_explicit_price_basis(tmp_path, basis):
    provider = CSVProvider(tmp_path / 'unused.csv', raw_store=RawStore(tmp_path / 'raw'))
    row = dict(security_id='ABC', session_date='2023-01-03', currency='USD', region='US', exchange='XNYS', session_open_at='2023-01-03T14:30:00+00:00', session_close_at='2023-01-03T21:00:00+00:00', available_at='2023-01-03T21:01:00+00:00', quality='B', revision_id='r1')
    if basis is not None:
        row['price_basis'] = basis
    with pytest.raises(ValueError, match='price_basis'):
        list(provider.normalize('prices', [row]))


@pytest.mark.parametrize('timestamp', ['2023-02-13T12:00:00+00:00', '2023-02-14T02:00:00+14:00', '2023-02-14T03:00:00+00:00'])
def test_fred_availability_guard_uses_new_york_date(tmp_path, timestamp):
    provider = FREDProvider(series_id='CPIAUCSL', vintage_start='2023-01-01', vintage_end='2023-12-31', transport=None, raw_store=RawStore(tmp_path), availability_quality_policy=lambda row: (datetime.fromisoformat(timestamp), QualityTier.B))
    with pytest.raises(ValueError, match='precedes'):
        list(provider.normalize('us_macro_vintages', [dict(date='2023-01-01', realtime_start='2023-02-14', realtime_end='2023-12-31', value='300')]))


@pytest.mark.parametrize('timestamp', ['2023-02-14T05:00:00+00:00', '2023-02-14T00:00:00-05:00', '2023-02-14T19:00:00+14:00'])
def test_fred_guard_accepts_equivalent_new_york_midnight_instants(tmp_path, timestamp):
    # This lower-bound guard does not certify midnight as the actual release time.
    provider = FREDProvider(series_id='CPIAUCSL', vintage_start='2023-01-01', vintage_end='2023-12-31', transport=None, raw_store=RawStore(tmp_path), availability_quality_policy=lambda row: (datetime.fromisoformat(timestamp), QualityTier.B))
    record, = provider.normalize('us_macro_vintages', [dict(date='2023-01-01', realtime_start='2023-02-14', realtime_end='2023-12-31', value='300')])
    assert record.available_at == datetime(2023, 2, 14, 5, tzinfo=timezone.utc)
