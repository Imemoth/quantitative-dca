# Bounded euro-area macro access audit — 2026-09-13

FRED series `CP0000EZ19M086NEST` was a candidate identified by a historical-range metadata query. The present audit used only the reviewed BoundedFREDTransport against `/fred/series/observations`, with both observation and realtime bounds explicitly 2010-01-01 through 2023-12-31 before send, output_type=1, limit=100000, offset=0, redirects disabled.

Actual result: 362 rows, 167 distinct observation periods, 2010-01-01 through 2023-11-01. Echoed bounds, completeness, every observation date and every vintage interval were validated before persistence. The transport was used directly because the existing FREDProvider normalizer supports US macro only; no EU record was incorrectly normalized as US.

Raw evidence SHA256: `142b57055bc254e856f04d3dd927759eabc6e56cc33ac4f5035a4bd1520d0b98`. Raw bytes and manifest live under `data/raw/fred_eu_development_audit/`. No quality tier assigned and no feature/model admission. Multiple interval records establish actual date-level vintage data, not complete publication-time truth. Exact revision completeness, historical series definition, seasonal adjustment/unit interpretation and geographic membership comparability remain unverified. An euro-area aggregate is not full EU monetary-jurisdiction coverage.

No new capability is inferred for equities, delisted companies, fundamentals or corporate actions. Rate limits and per-series rights/usage terms remain unverified. No paid purchase. This remains partial provider audit evidence, not a model experiment; no 2024+ observations were requested or evaluated. The retrospective holdout remains unexecuted, with the prior incident retained in its report.
