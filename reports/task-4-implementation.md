# Task 4 — canonical validation and quarantine

## Scope and interfaces

Implemented `quant_dca.canonical.validate` for lossless validation of canonical
OHLCV bars and generic observations. The public interfaces are:

- `validate_ohlcv(rows, *, securities=None, max_price_ratio=5.0,
  discontinuity_evidence=()) -> ValidationResult`
- `validate_observations(rows) -> ValidationResult`
- `ValidationResult(valid_rows, quarantined_rows, reasons,
  discontinuity_evidence)`
- `QuarantinedRow(row, reasons)`, with `reason` exposing the first explicit
  reason for compatibility with the planned interface example.
- `DiscontinuityEvidence(security_id, prior_session, session_date, kind,
  source, reference, verified_at)`

The result retains the original input objects and input order. Validation does
not replace, clip, winsorize, sort, forward-fill, or otherwise alter a row.
Every quarantined record contains all reasons detected for it, and the result
also contains aggregate reason counts.

## Validation behavior

OHLCV numeric checks cover missing, non-finite and non-positive prices;
missing, non-finite and negative volume; `high < low`; and open/close outside
the reported daily range. Identical and conflicting duplicates use the
`(security_id, session_date)` key and quarantine every member of the duplicate
group.

Canonical metadata checks cover ISO session dates, uppercase ISO-style
three-letter currencies, explicit `Region` and four-character MIC-like
exchange codes, raw/unadjusted price basis, source, revision, quality,
timezone-aware timestamps, session open/close order, availability after close,
and availability no earlier than publication or revision.

When `securities` is supplied, a bar must resolve to exactly one historical
security version by ID, session date in `[active_from, active_to)`, and mapping
availability no later than the bar availability. The resolved currency,
exchange and region must agree. Passing `None` means mapping validation was not
requested; passing an empty iterable explicitly requests it and therefore
produces `MISSING_SECURITY_MAPPING`.

The discontinuity screen compares positive finite closes in the supplied order
for each security. It rejects thresholds that are non-finite or no greater
than one, flags non-monotonic sessions instead of silently sorting, and marks a
ratio above the configured threshold as `UNEXPLAINED_DISCONTINUITY`. A matching
evidence record for the exact security and session transition permits either a
verified `corporate_action` or an evidenced `market_move`. Evidence requires a
non-empty source and reference plus an aware verification timestamp. Accepted
evidence is returned in `ValidationResult.discontinuity_evidence`, preserving
the provenance used to retain the extreme.

Review round 1 tightened this point-in-time rule: matching evidence resolves a
screened transition only when `evidence.verified_at <= bar.available_at` by
absolute instant. Future verification cannot retroactively validate an old
canonical bar while leaving its earlier availability timestamp intact. A caller
that needs to incorporate later verification must supply a revised canonical
row with appropriately later availability; this validator never mutates the
original. Equivalent instants expressed with different timezone offsets are
accepted.

Only a row with no validation reason becomes the next per-security
discontinuity anchor. A quarantined intermediate row therefore cannot create a
false discontinuity on a later valid row. Security identity is independently
required even when security-master mapping validation is not requested:
missing/empty IDs receive `MISSING_SECURITY_ID`, while non-string or malformed
IDs receive `INVALID_SECURITY_ID`.

Generic observations quarantine missing and non-finite values while leaving
valid negative values intact. They also validate the series name, ISO
observation date and common provenance/chronology. A missing value remains
missing in the original row and its existing quality tier is not rewritten to
Tier C.

## TDD and verification

The pre-existing interrupted RED draft was completed before production code.
`python -m pytest tests/canonical/test_validate.py -v` then failed during
collection with the expected `ModuleNotFoundError` for
`quant_dca.canonical.validate`. After implementation, the same command passed
39 tests. A second RED cycle exposed omitted required timestamps and an invalid
security activity date; four tests failed before the focused fix. The final
targeted command passed 43 tests, and the fresh full regression command
`python -m pytest -v` passed all 228 tests. `reports/task-4-tests.txt` preserves
both RED states and the GREEN runs.

Tests exercise the required bad-data cases, original-object preservation,
complete duplicate quarantine, configurable screening, both permitted evidence
kinds and evidence provenance, non-monotonic input, canonical timestamp and
publication chronology, historical mapping availability/activity and
currency/exchange/region agreement, observation missing-value semantics, and
threshold validation. They use fixtures only and no mocks or network calls.

## Decisions and concerns

- Evidence records are auditable assertions supplied by a caller. This module
  validates their structure and exact transition match; it does not independently
  establish that the cited corporate action or market move is genuine. Provider
  evidence verification remains an upstream research responsibility.
- The default close-ratio threshold of 5.0 is an operational screen, not a
  calibrated market model. Callers can set it explicitly, and a screened row
  remains quarantined until supported evidence is supplied.
- Fixture tests establish software behavior only. They do not establish actual
  2015–2023 coverage, point-in-time quality, provider truth, security-master
  completeness, or research validity.
- This task made no network request and did not access or evaluate the
  retrospective holdout.

## Review round 1 verification

Five new tests cover negative-volume and bad-provenance intermediate rows,
future evidence, timezone-equivalent evidence, and missing/empty/malformed
security identity without optional mapping. Before the fixes, the focused run
failed four tests (the timezone-equivalent behavior already passed). After the
fixes, the focused suite passed 48 tests. The full repository regression suite
passed 233 tests, as recorded in `reports/task-4-tests.txt`.
