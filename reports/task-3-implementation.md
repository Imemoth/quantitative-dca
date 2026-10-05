# Task 3 implementation — provider boundary and ingestion

Status: implemented and fixture-tested; FRED actual bounded sample replay passes. Live adapter connectivity is not verified in this task. SEC remains explicitly unavailable; source selection does not imply working integration or usable quality.

## Interfaces

- `ProviderAdapter.fetch(domain, start, end) -> Iterable[dict]` and `normalize(domain, rows) -> Iterable[object]` are a runtime-checkable protocol.
- `CSVProvider(path, raw_store=RawStore(...))` supports `prices`, persists the entire original input, and normalizes canonical OHLCV records. Identity, exchange, currency, region, session times, availability, quality and revision metadata must be explicit. No guessed exchange or publication time. `normalize_prices()` is a fixture convenience.
- `RawStore.persist(raw, provider=..., domain=..., row_count=...)` creates SHA-256 addressed raw bytes and an adjacent manifest containing provider, domain, fetched_at, source_hash and row_count. Exclusive file creation prevents replacement. Repeat ingestion verifies existing bytes and manifest identity. Separate provider/domain stores are recommended. Only fixed allowlisted metadata is persisted; credentials and URLs are excluded from manifests.
- `BoundedFREDTransport(api_key=..., sender=None).observations(series_id, start, end, vintage_start, vintage_end)` validates both observation and vintage intervals before any request. Every end must be <= 2023-12-31. The only network endpoint is FRED series observations, with explicit bounded parameters. Production urllib sender denies redirects; injected senders must honor `allow_redirects=False`. No retry, unbounded endpoint, pagination or silent response truncation.
- `FREDProvider(series_id=..., vintage_start=..., vintage_end=..., transport=..., raw_store=..., availability_quality_policy=...)` supports `us_macro_vintages`. A caller-reviewed policy must return `(timezone-aware datetime, QualityTier)`. No default tier or inferred publication timestamp. Backdating availability before the vintage start fails. Canonical `Observation` gains optional provider-independent `vintage_start` / `vintage_end`, preserving inclusive date intervals returned by FRED. A request-clipped end is not the true next revision date. Missing values remain None.
- `SECProvider` explicitly raises `IntegrationUnavailable` for fetch and normalize. It is a failure boundary for the selected but unverified source, not a filing parser or working integration. Unsupported domains fail closed in implemented adapters.

## Evidence

TDD began with the provider contract tests failing collection because `quant_dca.providers` did not exist. Implementation then passed 18 provider tests; full suite passed 176 tests. Tests replay `data/raw/provider_probes/FRED_CPIAUCSL_2023_sample.raw`, an existing authenticated 2023-bounded sample (three rows). No network calls or real credentials were used during this implementation. Test logs are in `reports/task-3-tests.txt`.

Adversarial cases prove sender is not called for denied observation/vintage intervals, missing vintage bounds, or reversed bounds. Tests also cover redirect failure, incomplete and out-of-bounds responses failing before first yielded row, original raw retention, manifest credential exclusion, immutable-content conflict, explicit CSV metadata, policy requirement, vintage preservation and backdating rejection.

## Limitations

Fixture behavior and historical sample replay establish software behavior only, not historical research validity. Intraday FRED release timestamps remain unavailable; policy selection and evidence assessment are caller responsibilities. A sample does not establish full series coverage, revisions completeness, or research validity. API key must be supplied by caller from environment; never stored in source/config. This adapter rejects responses requiring pagination. Raw persistence uses write-once files but is not a transactional multi-file store or protection against privileged external modification. CSV is an explicit local fixture contract, not a selected production OHLCV source. SEC bounded discovery, filing/publication filtering, retrieval and parser integration remain missing and unvalidated. No holdout retrieval/evaluation, downstream models or provider config promotion was performed.

## Reviewer P2 corrections

CSV now requires explicit `price_basis='unadjusted'`, the only supported basis in this executable raw-price adapter. Missing, blank and unsupported adjusted-basis values raise an error instead of silently labeling values unadjusted. Positive fixtures explicitly declare their basis.

FRED availability lower-bound validation converts every supplied availability instant to `America/New_York` before comparing its date with the vintage start. This is a documented validation convention, **not a FRED-supplied publication timezone or evidence of actual release time**. Equivalent instants represented with different offsets now receive identical decisions. The midnight guard is only a necessary structural bound; caller-reviewed policy still must establish actual or conservative availability, including unknown publication timing and eligible-session treatment. No quality default or policy waiver was added.

Regression-first evidence: five newly exposed failures (three basis cases and two timezone cases), with 19 tests passing before fixes. After fixes and positive equivalent-instant midnight boundary coverage, all **27 provider tests pass**. Verification was limited to `tests/providers`; no canonical contract changes or network calls were needed for these corrections.
