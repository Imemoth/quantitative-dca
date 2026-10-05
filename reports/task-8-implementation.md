# Task 8 implementation — point-in-time FX conversion

## Interfaces

- `FXService.from_rows(rows, *, max_age)` snapshots canonical `FXQuote` rows.
  `max_age` is deliberately required: a `timedelta` enforces staleness and
  `None` explicitly chooses an unbounded age policy.
- `FXService.resolve(base, quote, at_or_before) -> FXQuote` returns the exact
  canonical quote and provenance selected for a direct pair.
- `FXService.rate(base, quote, at_or_before) -> float` is the scalar
  convenience API over `resolve`.
- `FXService.to_huf(amount, currency, execution_ts) -> float` converts a
  finite amount with the same point-in-time selector. Native HUF amounts do
  not fabricate an FX quote.
- `FXQuoteUnavailable` and `StaleFXQuote` distinguish absent PIT evidence from
  a quote rejected by the caller's age policy.

## Decisions

- Input is limited to fully evidenced canonical `FXQuote` objects. The brief's
  tuple shorthand is rejected because it would invent availability, quality,
  source and revision evidence.
- Resolution supports direct pairs only. It first requires both `fixing_at`
  and `available_at` to be no later than execution, chooses the latest fixing,
  then orders actual revisions for that fixing by their explicit `revised_at`.
  Arrival time does not let an older revision replace a newer revision already
  known. Rows without revision timestamps retain the shared `latest_known` PIT
  behavior; conflicting revisions with tied timestamps fail closed. This FX-
  specific rule does not change the shared Task 5 helper.
- The selected `FXQuote` object is returned unchanged, preserving its quality,
  source, publication timestamp, revision timestamp and revision identifier.
  Scalar conversion is intentionally downstream of that evidenced selection.
- Currency legs must be distinct uppercase three-letter ASCII codes. Rates
  must be finite and positive; amounts must be finite; all timestamps must be
  timezone-aware. Availability cannot predate fixing, and publication/revision
  chronology is checked before selection.
- Daily fallback rows must explicitly identify `quote_type="daily_open"` and
  are usable only on the opening timestamp's calendar day (evaluated in that
  timestamp's timezone). The complete allowlist is `spot` and `daily_open`;
  values such as `close`, `eod`, `open`, differently cased or padded spellings,
  and other daily types cannot be promoted to spot/open evidence. No midnight
  or close timestamp is synthesized.
- No inverse lookup or cross-rate graph was added. The service does not make
  network requests, inspect market observations, or use credentials.

## TDD and test evidence

The initial focused test collection failed with
`ModuleNotFoundError: No module named 'quant_dca.fx'` before production files
existed. The first GREEN attempt passed 19 tests and failed two currency-row
cases, exposing that malformed rows could hide behind pair filtering. After
collection-first validation, the focused suite passed 21 tests. A subsequent
RED test proved tuple shorthand was still accepted at construction; it failed
with `DID NOT RAISE TypeError`, and passed after canonical input enforcement.

Final focused and full regression commands and outcomes are recorded in
`reports/task-8-tests.txt`.

Review fix round 1 added failing regressions for delayed arrival of an older
revision, tied revision timestamps with conflicting values, and five unknown
quote-type spellings that previously bypassed the daily-evidence rule. The
fixes are local to `quant_dca.fx`: explicit revision timestamp ordering and a
two-value quote-type allowlist.

## Limitations

- Upstream ingestion must establish that a `daily_open` row is a genuine
  observed open and supply its real fixing/availability/provenance. This layer
  can reject missing or inconsistent evidence but cannot prove vendor meaning.
- Age limits are policy inputs, not research conclusions. The service provides
  no default threshold and this task does not tune one.
- Only exact direct pairs are resolved. Inversion and triangulation require
  separately specified evidence/rounding/availability policy and are deferred.
