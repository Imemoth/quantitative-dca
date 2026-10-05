# Data & PIT Foundation — Task 1 implementation

Status: implemented and verified with synthetic fixtures only. No provider
network request or historical research evaluation was performed by this task.
The approved 2026-09-11 evaluation amendment was read before implementation.

## Scope and design

Created a Python 3.12+ package using a `src` layout, setuptools metadata and
pytest configuration. Canonical contracts use the standard library only;
pytest is an optional test dependency. Later tasks can introduce dependencies
when their consuming functionality is implemented.

All seven records are frozen, slotted dataclasses with scalar fields, sharing
required `available_at`, `quality`, `source`, and `revision_id`. Optional
`published_at` and `revised_at` remain unknown (`None`) when unavailable.
Availability describes the specific vintage; dates never substitute for
availability. No tier is assigned by default and no source capability is
inferred from the presence of these contracts.

| Contract | Domain fields and semantics |
| --- | --- |
| Observation | Series/entity, observation date, nullable value, optional currency/region/exchange/unit; compatible with the exact task-brief constructor. |
| Security | Stable security ID, ticker/name/ISIN, currency, US/EU/global region, MIC exchange, active interval, listing and security type, monetary jurisdiction/currency area. |
| UniverseMembership | Universe/security/index identity, historical active interval, region, exchange and currency; interval is start-inclusive/end-exclusive. |
| CorporateAction | Action/security identity, type, ex-date, cash per share, new/old share split ratio, currency/region/exchange, announcement and payment timestamps. |
| FXQuote | Base/quote currency, rate in quote units per base unit, fixing timestamp and quote type. |
| FeatureValue | Feature/entity, observation date and value, decision cutoff, maximum input availability, calculation timestamp, optional currency/region/exchange. |
| OHLCV | Security/session, nullable OHLCV, currency/region/exchange, exchange session open/close timestamps, explicit price basis defaulting to unadjusted. |

`QualityTier` provides A/B/C serialization values. `Region` provides US/EU/GLOBAL.
Global is available for shared macro and risk series; it does not expand the
approved equity universe.

All timestamp fields reject datetimes without a usable UTC offset, including
objects with non-null tzinfo but `utcoffset() is None`. Non-datetime timestamp
inputs raise TypeError. Aware non-UTC timestamps retain their offset and compare
as the same instant; no local time or UTC timestamp is silently invented.
Optional timestamp fields accept None; required timestamps do not.

Immutability means normal attribute assignment and deletion are prohibited;
new vintages are represented by new records, preserving prior values. These
objects are structural contracts, not a tamper-proof persistence layer.

## TDD and verification

1. Wrote tests against the absent package before writing production contracts.
2. Ran `python -m pytest tests/types/test_contracts.py -v`; collection failed
   with `ModuleNotFoundError: No module named 'quant_dca'`, the expected RED.
3. Implemented contracts and packaging; the same command passed **98 tests**.
4. Simplified optional-timestamp handling to inspect the dataclass field's
   explicit None default rather than its rendered type; reran the full suite.

The log `reports/task-1-tests.txt` preserves the actual initial RED output and
subsequent GREEN outputs. Tests exercise real constructors and actual assignment
and deletion. For each of the seven records, each declared timestamp is tested
against a naive datetime, an unusable tzinfo, and an aware non-UTC datetime.
They additionally check compatibility with the brief, missing observation
values, distinct revisions without overwriting the original, enum serialization
and the raw-price default. No mocks, provider downloads, or research data were
used. `git diff --check` found no whitespace errors.

## Limits and next tasks

- Fixtures establish structural software behavior only, not historical
  research validity, genuine PIT availability or provider quality.
- Ingestion validation (Task 4) must validate ISO dates, numeric domains,
  exchange/currency mappings, missing fields and chronological consistency,
  and explicitly quarantine failures. OHLCV construction deliberately retains
  questionable numeric values for those diagnostics.
- Calendar and as-of services must enforce decision cutoffs and feature input
  availability. Constructors do not enforce those cross-domain economic rules.
- Historical membership eligibility, corporate-action economics and FX quote
  selection remain separate planned services; recording their inputs does not
  implement their policy.
- The evaluation amendment remains binding: request observation, vintage and
  publication upper bounds before any development download; only 2015–2023
  development OOS is authorized. No retrospective holdout or production handoff
  is authorized by this task.
