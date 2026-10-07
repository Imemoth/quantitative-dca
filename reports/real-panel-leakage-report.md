# Real-panel leakage — 2026-10-06

**BLOCKED_NOT_EXECUTED** — no actual admitted panel exists. This is not PASS and
not a failed model experiment. Financial model/OOS runs: 0/0. No holdout run.

| Required check | Status / reason |
|---|---|
| Feature availability <= prediction timestamp | BLOCKED: no admitted feature rows |
| No future revisions; publication lag | BLOCKED: raw macro/filing dates not approved availability rules |
| Historical universe and cross-sectional membership | BLOCKED: US/EU survivorship/eligibility ledger absent |
| Exchange sessions / next eligible open | BLOCKED on real panel; software calendar tests are separate evidence |
| Corporate-action chronology / terminal costs | BLOCKED: partial action sample only, no economic reconciliation |
| FX fixing, availability and currencies | BLOCKED: date-only reference sample, no admitted conversion history |
| Event schedule-known-at chronology | BLOCKED: no versioned ex-ante calendar |
| Feature/target isolation | BLOCKED on real panel; no stores materialized |
| No future normalization | BLOCKED on real panel; no fitted transforms |
| Source lineage, IDs, units, coverage, corrections | BLOCKED: no admitted canonical snapshot |

Unit/fixture PASS and `raw-data-quality-results.json` describe narrower checks.
They do not execute this gate. Once an actual admitted panel exists, every listed
check must execute against immutable snapshot/config/schema IDs; a violation is a
hard FAIL, never a warning. Independent data-admission review and separate human
authorization must follow before model research.
