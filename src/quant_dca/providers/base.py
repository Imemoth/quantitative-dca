"""Provider contract and content-addressed raw evidence storage."""
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable, Protocol, runtime_checkable

DEVELOPMENT_END = date(2023, 12, 31)


def bounded_interval(start: str, end: str) -> None:
    if not isinstance(start, str) or not isinstance(end, str):
        raise ValueError('Explicit ISO start and end dates required')
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first.isoformat() != start or last.isoformat() != end:
        raise ValueError('Canonical ISO dates required')
    if first > last or last > DEVELOPMENT_END:
        raise ValueError('Invalid interval or development cutoff exceeded')


@runtime_checkable
class ProviderAdapter(Protocol):
    def fetch(self, domain: str, start: str, end: str) -> Iterable[dict]: ...
    def normalize(self, domain: str, rows: Iterable[dict]) -> Iterable[object]: ...


class RawStore:
    """Write-once blobs and manifests; existing content is verified, never replaced.

    Store only allowlisted provenance, never URLs, request parameters or secrets.
    A separate directory per provider/domain avoids ambiguous identical payloads.
    """
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def persist(self, raw: bytes, *, provider: str, domain: str, row_count: int) -> Path:
        if not all(re.fullmatch(r'[a-z][a-z0-9_]*', x) for x in (provider, domain)):
            raise ValueError('Invalid provider or domain identifier')
        if type(row_count) is not int or row_count < 0:
            raise ValueError('Invalid row count')
        self.root.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(raw).hexdigest()
        blob = self.root / f'{digest}.raw'
        try:
            with blob.open('xb') as stream:
                stream.write(raw)
        except FileExistsError:
            if blob.read_bytes() != raw:
                raise ValueError('Immutable raw integrity violation')
        manifest = self.root / f'{digest}.manifest.json'
        metadata = dict(provider=provider, domain=domain, fetched_at=datetime.now(timezone.utc).isoformat(), source_hash=digest, row_count=row_count)
        try:
            with manifest.open('x') as stream:
                json.dump(metadata, stream, indent=2)
        except FileExistsError:
            previous = json.loads(manifest.read_text())
            if any(previous.get(key) != value for key, value in metadata.items() if key != 'fetched_at'):
                raise ValueError('Immutable manifest conflict')
        return manifest
