# EODHD bounded-history access audit — 2026-09-14

One demo symbol, AAPL.US, was requested from the EOD endpoint with explicit `from=2010-01-01` and `to=2023-12-31` before transmission. The existing bounded_interval guard ran before send and redirects were disabled. The response array's dates were all checked against those bounds before raw persistence.

Actual outcome: HTTP 200, 3522 daily rows, 2010-01-04 through 2023-12-29. Observed field names: adjusted_close, close, date, high, low, open, volume. SHA256: `ac37c9c3a7b1a5255ad92ae247c16f07db29b4a5c8abdc8e54687cc0bc270c07`. The payload is retained in `data/raw/eodhd_development_audit/` with its hashed manifest.

This establishes that the sampled demo symbol can return a long development-period daily history. It does not establish complete eligible-session coverage, broad US or EU access, delisted coverage, or corporate-action integrity. No pricing statistics, model, feature selection, policy experiment or investment recommendation was produced from this sample.

Admission remains RAW_ONLY with no assigned tier. The earlier documented concerns about original-unit volume, adjustment conventions, corporate actions, historical corrections and publication latency remain unresolved. Current corrected/adjusted provider histories must not be silently described as historical PIT snapshots. Exact per-symbol license/usage and rate-limit conditions were not established by a successful response. No subscription, trial or purchase was initiated.

The symbol was selected because it is the already-tested provider demo, not because it performs well or resembles the user's holdings. It cannot establish a survivorship-controlled research universe; any later economic demonstration using it would require explicit limited-data labeling and cannot substitute for the required broad OOS evidence.

No 2024+ observations were requested or evaluated. The prior documentation incident remains preserved, and the retrospective holdout remains unexecuted.
