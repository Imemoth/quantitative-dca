# Quant DCA Data & PIT Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic point-in-time data foundation that can reconstruct exactly what was knowable for an eligible US/EU security at any EOD prediction timestamp.

**Architecture:** Raw provider data is preserved unchanged, normalized through provider adapters into typed canonical tables, assigned availability timestamps and quality tiers, then exposed only through as-of-safe query functions. Corporate actions, exchange calendars, historical universe membership and FX are first-class data domains rather than backtest afterthoughts.

**Tech Stack:** Python 3.12+, DuckDB, Parquet/PyArrow, Pandas, Pydantic/dataclasses, exchange-calendars, pytest.

**Spec:** `docs/quant-dca-engine-v1-design-spec.md`

## Global Constraints

- Daily/EOD only; same-close execution from an EOD signal is prohibited.
- `available_at <= as_of` is mandatory for every feature source observation.
- No backward fill.
- Revised macro/fundamental observations cannot overwrite what was historically known.
- Cross-sectional calculations use the historical eligible universe, never the 2026 universe projected backward.
- Invalid raw observations are quarantined, not silently fixed.
- Data quality tiers are A/B/C; dependence on Tier C must remain visible downstream.
- Feature and target stores must remain physically/logically separate.
- Default base currency is HUF.

---

## File map

- Create: `pyproject.toml` — package/test/tool dependencies.
- Create: `src/quant_dca/types.py` — canonical enums and immutable records.
- Create: `src/quant_dca/calendars/service.py` — eligible-session and next-open logic.
- Create: `src/quant_dca/providers/base.py` — provider adapter protocol.
- Create: `src/quant_dca/providers/csv_provider.py` — local fixture/reference provider.
- Create: `src/quant_dca/canonical/validate.py` — validation and quarantine rules.
- Create: `src/quant_dca/point_in_time/asof.py` — PIT selection primitives.
- Create: `src/quant_dca/universe/membership.py` — historical eligibility lookup.
- Create: `src/quant_dca/corporate_actions/economics.py` — split/dividend economic adjustment.
- Create: `src/quant_dca/fx/conversion.py` — timestamp-safe FX conversion.
- Create: `src/quant_dca/storage/snapshots.py` — immutable Parquet snapshot writer/hash.
- Create: `src/quant_dca/lineage.py` — source/transform lineage metadata.
- Create: `src/quant_dca/tools/build_fixture_snapshot.py` — deterministic fixture build CLI used by the audit.
- Create: `reports/provider-decision-matrix.md` — researched provider choice, cost/access constraints and fallback per domain.
- Test counterparts under `tests/` with the same domain names.


### Task 0: Research and freeze the prototype provider matrix

**Files:**
- Create: `reports/provider-decision-matrix.md`
- Create: `configs/providers_v1.yaml`

**Interfaces:**
- Produces: one primary and one fallback source per required domain, with explicit quality tier, historical coverage, PIT/revision capability, access method and cost status.

- [ ] **Step 1: Evaluate the required domains independently**

Cover exactly these domains: US macro vintages, EU macro vintages, US OHLCV, EU OHLCV, FX, US fundamentals, EU fundamentals, corporate actions, historical universe/delistings, sector/index context and scheduled event calendars.

- [ ] **Step 2: Apply the V1 procurement rule**

Prefer authoritative free sources where practical. No paid institutional dataset may be purchased or assumed available without explicit user approval. A source that lacks historical PIT semantics must be labeled Tier B/C and its limitation must remain visible to downstream sensitivity analysis.

- [ ] **Step 3: Record selection criteria and fallbacks**

For each domain record: provider, endpoint/dataset, coverage start, fields needed, publication timestamp support, revision support, corporate-action behavior, rate/access limit, license constraint, quality tier, primary/fallback status and rejection reason for alternatives.

- [ ] **Step 4: Encode only the selected adapters in configuration**

`configs/providers_v1.yaml` contains provider IDs and domain mappings only; credentials are environment variables and are never committed.

- [ ] **Step 5: Commit**

```bash
git add reports/provider-decision-matrix.md configs/providers_v1.yaml
git commit -m "research: freeze low-cost V1 provider matrix"
```

### Task 1: Scaffold package and canonical data contracts

**Interfaces:**
- Produces: `QualityTier`, `Region`, `Observation`, `Security`, `UniverseMembership`, `CorporateAction`, `FXQuote`, `FeatureValue`.

- [ ] **Step 1: Write failing contract tests**

```python
from datetime import datetime, timezone
from quant_dca.types import Observation, QualityTier


def test_observation_is_immutable_and_timestamped():
    row = Observation(
        series="US_CPI",
        entity_id=None,
        observation_date="2020-02-29",
        value=2.3,
        available_at=datetime(2020, 3, 11, 12, 30, tzinfo=timezone.utc),
        quality=QualityTier.A,
        source="fixture",
        revision_id="v1",
    )
    assert row.quality is QualityTier.A
    assert row.available_at.tzinfo is not None
```

- [ ] **Step 2: Run the test and verify import failure**

Run: `pytest tests/types/test_contracts.py -v`

Expected: FAIL because `quant_dca.types` does not exist.

- [ ] **Step 3: Implement immutable canonical records**

```python
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

class QualityTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"

@dataclass(frozen=True)
class Observation:
    series: str
    entity_id: str | None
    observation_date: str
    value: float | None
    available_at: datetime
    quality: QualityTier
    source: str
    revision_id: str
```

Add the remaining records with explicit currency, region, exchange and timestamp fields; reject naive datetimes in `__post_init__`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/types/test_contracts.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/quant_dca/types.py tests/types/test_contracts.py
git commit -m "feat: define canonical point-in-time data contracts"
```

### Task 2: Implement exchange-calendar and execution-session rules

**Interfaces:**
- Consumes: `Security.exchange`.
- Produces: `previous_eligible_eod(exchange, ts)`, `next_eligible_open(exchange, ts)`, `nth_subsequent_open(exchange, session, n)`.

- [ ] **Step 1: Write failing US/EU holiday tests**

```python
from datetime import datetime, timezone
from quant_dca.calendars.service import next_eligible_open


def test_next_open_skips_weekend():
    friday_after_close = datetime(2026, 9, 11, 21, 0, tzinfo=timezone.utc)
    nxt = next_eligible_open("XNYS", friday_after_close)
    assert nxt.weekday() == 0
    assert nxt > friday_after_close
```

Add one XETR holiday fixture and one monthly first-eligible-session case.

- [ ] **Step 2: Verify failure**

Run: `pytest tests/calendars/test_service.py -v`

Expected: FAIL because calendar service is absent.

- [ ] **Step 3: Implement calendar service**

Use `exchange_calendars` schedules; map supported exchange MICs explicitly. Never infer an execution timestamp by adding 24 hours.

- [ ] **Step 4: Run tests**

Run: `pytest tests/calendars/test_service.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/quant_dca/calendars tests/calendars
git commit -m "feat: add point-in-time exchange session service"
```

### Task 3: Define provider adapter boundary and raw-to-canonical ingestion

**Interfaces:**
- Produces: `ProviderAdapter.fetch(domain, start, end) -> Iterable[dict]`, `ProviderAdapter.normalize(raw) -> Iterable[canonical records]`.

- [ ] **Step 1: Write a failing adapter contract test**

```python
from quant_dca.providers.csv_provider import CSVProvider


def test_csv_provider_preserves_raw_and_emits_source_metadata(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("ticker,date,open,close\nABC,2020-01-02,10,11\n")
    rows = list(CSVProvider(path).normalize_prices())
    assert rows[0].source == "csv"
    assert rows[0].available_at is not None
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/providers/test_csv_provider.py -v`

Expected: FAIL.

- [ ] **Step 3: Implement the protocol and fixture provider**

```python
from typing import Protocol, Iterable

class ProviderAdapter(Protocol):
    def fetch(self, domain: str, start: str, end: str) -> Iterable[dict]: ...
    def normalize(self, domain: str, rows: Iterable[dict]) -> Iterable[object]: ...
```

The CSV provider is the executable contract for future FRED/ALFRED, OHLCV, fundamentals and EU adapters.

- [ ] **Step 4: Add raw manifest persistence**

Every ingest writes `{provider, domain, fetched_at, source_hash, row_count}` beside the raw file. Implement provider-specific adapters only for the sources frozen in `configs/providers_v1.yaml`; keep their output behind the shared protocol.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/providers -v`

```bash
git add src/quant_dca/providers tests/providers
git commit -m "feat: add provider abstraction and canonical ingestion"
```

### Task 4: Implement canonical validation and quarantine

**Interfaces:**
- Consumes: canonical OHLCV/observation records.
- Produces: `ValidationResult(valid_rows, quarantined_rows, reasons)`.

- [ ] **Step 1: Write failing bad-data tests**

```python
from quant_dca.canonical.validate import validate_ohlcv


def test_high_below_low_is_quarantined():
    result = validate_ohlcv([{"high": 9.0, "low": 10.0, "volume": 100.0}])
    assert len(result.valid_rows) == 0
    assert result.quarantined_rows[0].reason == "HIGH_BELOW_LOW"
```

Add negative-volume, duplicate-session and unexplained extreme-jump tests.

- [ ] **Step 2: Verify failure**

Run: `pytest tests/canonical/test_validate.py -v`

- [ ] **Step 3: Implement explicit validation reasons**

Do not winsorize valid market extremes. Permit an extreme discontinuity only if a verified corporate action explains it.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/canonical/test_validate.py -v`

```bash
git add src/quant_dca/canonical tests/canonical
git commit -m "feat: quarantine invalid canonical observations"
```

### Task 5: Implement point-in-time as-of selection with hard leakage failure

**Interfaces:**
- Produces: `latest_known(rows, as_of)`, `assert_pit_safe(feature_values, prediction_timestamp)`.

- [ ] **Step 1: Write vintage and leakage tests**

```python
from datetime import datetime, timezone
import pytest
from quant_dca.point_in_time.asof import latest_known, assert_pit_safe


def test_latest_known_uses_historical_vintage():
    as_of = datetime(2020, 3, 15, tzinfo=timezone.utc)
    rows = [
        {"value": 4.0, "available_at": datetime(2020, 3, 6, tzinfo=timezone.utc)},
        {"value": 3.9, "available_at": datetime(2020, 4, 3, tzinfo=timezone.utc)},
    ]
    assert latest_known(rows, as_of)["value"] == 4.0


def test_future_feature_is_hard_failure():
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        assert_pit_safe([datetime(2020, 3, 16, tzinfo=timezone.utc)],
                        datetime(2020, 3, 15, tzinfo=timezone.utc))
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/point_in_time/test_asof.py -v`

- [ ] **Step 3: Implement as-of selection and guard**

`latest_known` filters `available_at <= as_of`, sorts by availability/revision order and returns only the latest historically knowable record.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/point_in_time/test_asof.py -v`

```bash
git add src/quant_dca/point_in_time tests/point_in_time
git commit -m "feat: enforce point-in-time as-of semantics"
```

### Task 6: Implement historical universe eligibility

**Interfaces:**
- Produces: `eligible_universe(as_of, region) -> list[Security]` and `is_eligible(security_id, as_of)`.

- [ ] **Step 1: Write survivorship tests**

```python
from quant_dca.universe.membership import UniverseIndex


def test_delisted_security_remains_eligible_before_delisting():
    idx = UniverseIndex.from_rows([
        {"security_id": "OLD", "active_from": "2012-01-01", "active_to": "2018-06-01", "region": "US"}
    ])
    assert idx.is_eligible("OLD", "2017-01-03")
    assert not idx.is_eligible("OLD", "2019-01-03")
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/universe/test_membership.py -v`

- [ ] **Step 3: Implement eligibility filters**

Require common equity, primary listing, minimum 120 eligible sessions, liquidity threshold from configuration and at least one historically available fundamental report. Preserve delisted names while historically eligible.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/universe/test_membership.py -v`

```bash
git add src/quant_dca/universe tests/universe
git commit -m "feat: reconstruct historical eligible universe"
```

### Task 7: Implement corporate-action economics and ex-dividend protection

**Interfaces:**
- Produces: `economic_acquisition_cost(fill, delayed_from, actions, fx_service)` and split-adjusted feature price series.

- [ ] **Step 1: Write ex-dividend false-dip test**

```python
from quant_dca.corporate_actions.economics import economic_price_improvement


def test_dividend_drop_is_not_free_timing_edge():
    improvement = economic_price_improvement(
        baseline_cost=100.0,
        delayed_fill=98.0,
        foregone_distribution=2.0,
    )
    assert improvement == 0.0
```

Add a 2-for-1 split invariance test.

- [ ] **Step 2: Verify failure**

Run: `pytest tests/corporate_actions/test_economics.py -v`

- [ ] **Step 3: Implement economic equivalence**

```python
def economic_price_improvement(baseline_cost: float, delayed_fill: float,
                               foregone_distribution: float) -> float:
    delayed_economic_cost = delayed_fill + foregone_distribution
    return (baseline_cost - delayed_economic_cost) / baseline_cost
```

Apply FX conversion at the relevant cash-flow timestamp for HUF evaluation.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/corporate_actions/test_economics.py -v`

```bash
git add src/quant_dca/corporate_actions tests/corporate_actions
git commit -m "feat: preserve economic returns across corporate actions"
```

### Task 8: Implement point-in-time FX conversion

**Interfaces:**
- Produces: `FXService.rate(base, quote, at_or_before)` and `to_huf(amount, currency, execution_ts)`.

- [ ] **Step 1: Write no-later-fixing test**

```python
from datetime import datetime, timezone
from quant_dca.fx.conversion import FXService


def test_fx_never_uses_quote_after_stock_execution():
    svc = FXService.from_rows([
        ("USDHUF", datetime(2020, 1, 2, 14, 30, tzinfo=timezone.utc), 300.0),
        ("USDHUF", datetime(2020, 1, 2, 21, 0, tzinfo=timezone.utc), 305.0),
    ])
    assert svc.rate("USD", "HUF", datetime(2020, 1, 2, 15, 0, tzinfo=timezone.utc)) == 300.0
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/fx/test_conversion.py -v`

- [ ] **Step 3: Implement timestamp-safe quote selection**

Fallback for daily-only data is the same calendar day's FX open; never use a later same-day close for an earlier stock execution.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/fx/test_conversion.py -v`

```bash
git add src/quant_dca/fx tests/fx
git commit -m "feat: add point-in-time base-currency conversion"
```

### Task 9: Persist immutable snapshots and lineage

**Interfaces:**
- Produces: `write_snapshot(df, layer, as_of) -> SnapshotRef`, `SnapshotRef.sha256`, lineage JSON sidecars.

- [ ] **Step 1: Write deterministic hash test**

```python
import pandas as pd
from quant_dca.storage.snapshots import snapshot_hash


def test_snapshot_hash_is_deterministic():
    df = pd.DataFrame({"b": [2, 1], "a": ["x", "y"]})
    assert snapshot_hash(df) == snapshot_hash(df.copy())
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/storage/test_snapshots.py -v`

- [ ] **Step 3: Implement canonical ordering, Parquet write and sidecar metadata**

Metadata includes layer, as-of cutoff, source hashes, row count, schema version and SHA-256.

- [ ] **Step 4: Add lineage lookup test and implementation**

A feature source lineage record must identify provider, source snapshot, transform name and availability rule.

- [ ] **Step 5: Run full foundation test suite**

Run: `pytest tests/types tests/calendars tests/providers tests/canonical tests/point_in_time tests/universe tests/corporate_actions tests/fx tests/storage -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/quant_dca/storage src/quant_dca/lineage.py tests/storage
git commit -m "feat: add immutable data snapshots and lineage"
```

### Task 10: Produce PIT foundation audit artifact

**Files:**
- Create: `reports/data-foundation-audit.md`
- Create: `reports/data-source-quality-map.csv`

- [ ] **Step 1: Run deterministic fixture build twice**

Implement `src/quant_dca/tools/build_fixture_snapshot.py` as a thin CLI over the canonical/PIT/snapshot services, then run:

Run: `python -m quant_dca.tools.build_fixture_snapshot --as-of 2020-03-12`

Expected: both runs emit the same snapshot hash.

- [ ] **Step 2: Run the complete automated suite**

Run: `pytest -q`

Expected: PASS.

- [ ] **Step 3: Write audit report from machine outputs**

The report must enumerate provider/domain, quality tier, PIT limitations, quarantined rows, survivorship limitations and snapshot hashes. Do not mark a missing PIT source as solved; classify it B/C and state its downstream restriction.

- [ ] **Step 4: Commit**

```bash
git add reports/data-foundation-audit.md reports/data-source-quality-map.csv
git commit -m "docs: record point-in-time data foundation audit"
```
