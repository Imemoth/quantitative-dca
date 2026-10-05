# Bounded FRED development audit — 2026-09-13

This is provider/data-access evidence, not a model experiment or an admitted research panel. The user-authorized evaluation protocol applies.

## Request and validation contract

All six requests used the reviewed BoundedFREDTransport/FREDProvider at code commit 635b549. Endpoint: https://api.stlouisfed.org/fred/series/observations. Both observation and realtime intervals were explicitly 2010-01-01 through 2023-12-31 before transmission; output_type=1, limit=100000, offset=0. Redirects disabled. Credential supplied only in the transient process and omitted from artifacts. Normalization was not called; its supplied policy rejects admission.

The adapter verifies returned bounds, completeness and every observation/vintage date before yielding. Successful raw payloads and SHA256 manifests are retained in data/raw/fred_development_audit/<series>/. No retrospective holdout requests or evaluations occurred in this audit. The earlier documentation incident remains documented and the historical holdout is not pristine.

## Observed results

| Series | Outcome | Rows | Distinct periods | Observation range |
|---|---|---:|---:|---|
| CPIAUCSL | raw_validated_not_admitted | 830 | 167 | 2010-01-01 .. 2023-11-01 |
| CPILFESL | raw_validated_not_admitted | 822 | 167 | 2010-01-01 .. 2023-11-01 |
| UNRATE | raw_validated_not_admitted | 296 | 167 | 2010-01-01 .. 2023-11-01 |
| FEDFUNDS | raw_validated_not_admitted | 169 | 167 | 2010-01-01 .. 2023-11-01 |
| DGS10 | failed | — | — | — .. — |
| DGS2 | failed | — | — | — .. — |

The four successful series contain 2010–2023 historical observations with vintage intervals. Their last observation period is November 2023; no December value was pulled from a 2024 release. Multiple rows per period in the inflation/unemployment series establish actual revision records, not just a documented capability. This alone does not establish revision completeness or exact publication timestamps.

DGS10 and DGS2 failed with ValueError before any raw payload was persisted. The sanitized audit captured the exception class only; the precise HTTP/cause was not retained, so this is an unclassified access failure, not proof of missing historical coverage. Do not infer successful yield-curve coverage.

## Quality and coverage limits

Quality remains null / NOT ADMITTED for this audit. Date-level realtime intervals are not intraday publication evidence; the next task is to verify a conservative availability policy against historical release information before assigning B or A. US macro only; equity active/delisted coverage, corporate actions and USA/EU equity breadth are not applicable to these series and remain unresolved elsewhere. Historical coverage outside the returned ranges is unverified. Rate limits, complete series rights/redistribution permissions and free entitlement limits were not established by this probe. No paid purchase occurred.

This does not close the eleven-domain source inventory gate or create an eligible equity panel. No feature, model, hyperparameter or policy selection was conducted.

## Raw evidence hashes

- CPIAUCSL: `80d08f7e8746f551392aded2606e2dca479abb8b5b400776776301599fe9b3b4`; 830 rows.
- CPILFESL: `4694d64693f228dcab50a171d9c215a3024b4c3f4691d6b6a6b8752174b0474c`; 822 rows.
- FEDFUNDS: `d2a8a5b2debf9abacdd7d5f434603742968b16c0591d97ef48c31ffb4c78b882`; 169 rows.
- UNRATE: `5cab72748c8af9029f6a366a2865896ab3c3efe1ab715e4c67d5f24c6c9305fa`; 296 rows.
