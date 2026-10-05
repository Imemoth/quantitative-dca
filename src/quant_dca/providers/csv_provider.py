"""CSV fixture adapter. Every price must carry explicit canonical metadata."""
import csv
from datetime import datetime
import io
from pathlib import Path
from typing import Iterable

from quant_dca.types import OHLCV, QualityTier, Region
from .base import RawStore, bounded_interval


class CSVProvider:
    def __init__(self, path: str | Path, *, raw_store: RawStore):
        self.path, self.raw_store = Path(path), raw_store

    def _read(self) -> list[dict]:
        raw = self.path.read_bytes()
        rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        self.raw_store.persist(raw, provider='csv', domain='prices', row_count=len(rows))
        return rows

    def fetch(self, domain: str, start: str, end: str) -> Iterable[dict]:
        if domain != 'prices':
            raise ValueError('Unsupported CSV domain')
        bounded_interval(start, end)
        for row in self._read():
            if not row.get('session_date'):
                raise ValueError('CSV requires explicit metadata: session_date')
            if start <= row['session_date'] <= end:
                yield row

    def normalize_prices(self) -> Iterable[OHLCV]:
        return self.normalize('prices', self._read())

    def normalize(self, domain: str, rows: Iterable[dict]) -> Iterable[OHLCV]:
        if domain != 'prices':
            raise ValueError('Unsupported CSV domain')
        required = ('security_id', 'session_date', 'currency', 'region', 'exchange', 'session_open_at', 'session_close_at', 'available_at', 'quality', 'revision_id')
        for row in rows:
            if row.get('price_basis') != 'unadjusted':
                raise ValueError('CSV requires explicit metadata: supported price_basis unadjusted')
            missing = [key for key in required if not row.get(key)]
            if missing:
                raise ValueError(f'CSV requires explicit metadata: {missing}')
            metadata = {key: row[key] for key in required}
            for key in ('session_open_at', 'session_close_at', 'available_at'):
                metadata[key] = datetime.fromisoformat(row[key])
            metadata['quality'] = QualityTier(row['quality'])
            metadata['region'] = Region(row['region'])
            metadata['source'] = 'csv'
            for key in ('published_at', 'revised_at'):
                metadata[key] = datetime.fromisoformat(row[key]) if row.get(key) else None
            yield OHLCV(**metadata, **{key: float(row[key]) if row.get(key) else None for key in ('open', 'high', 'low', 'close', 'volume')}, price_basis=row['price_basis'])
