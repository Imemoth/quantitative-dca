# Development panel admission — 2026-10-05

**Decision: NOT ADMITTED.** Audit inventory completed; actual panel and admission
evidence remain incomplete. All source tiers remain unassigned (empty CSV / JSON
null), not Tier C. `REAL_PANEL_LEAKAGE_GATE_BLOCKED_BY_DATA_ADMISSION`.

## Evidence actually checked in this phase

Rehashed 14 previously bounded captures retained alongside the old local checkpoint.
All 14 match their content-addressed filenames. FRED row counts match manifests and
API counts; every observation and real-time interval is within 2010–2023. EODHD bar
dates, SEC index filing dates and the sampled accession acceptance date, and MNB quote
dates passed the development-envelope checks. Exact paths, hashes, byte/row counts and
results are in `data-admission-evidence.json`. The SEC filing sample lacks a standalone
manifest in the retained workspace: hash and acceptance field are verified, not
complete acquisition provenance. No omission is silently reconstructed.

These raw files are **not in the GitHub snapshot** and are not redistributed by this
branch. The machine report is a receipt of the local audit, not enough by itself to
reconstruct or admit the provider data. Reproduction requires those exact raw bytes.
No financial data network request, new credential use, paid purchase, model fit or
OOS run occurred in this phase. More rows would not resolve the present semantic gaps;
no unbounded interface or contemporary market page was opened.

## Domain decisions

The companion CSV records source, observed span, geography, active/delisted coverage,
actions, PIT/revisions, publication, request bounds, units/currency, rate/rights/cost,
quality evidence, decision, limitation and remaining blocker for each domain.

| Required capability | Decision | Actual evidence / unresolved blocker |
|---|---|---|
| Historical active US equities | MISSING | One active demo price series is not dated listing/eligibility evidence |
| Historical delisted US equities | MISSING | No delisted security master or terminal ledger |
| Historical active EU equities | MISSING | No usable historical security master |
| Historical delisted EU equities | MISSING | No delisted listings or terminal consideration |
| Historical membership | MISSING | No ex-ante membership versions |
| Ticker/name changes | MISSING | No identifier-effective/known-at mapping |
| Mergers/acquisitions | MISSING | No announcement, effective, cash/share consideration history |
| Terminal economics | MISSING | No verified delisting/recovery/merger values |
| US OHLCV | RAW_ONLY | One EODHD AAPL demo, 2010-01-04–2023-12-29; correction state unverified |
| EU OHLCV | UNAVAILABLE | Prior SAP test paths failed; not proof all providers unavailable |
| Corporate actions | MISSING | Split, distribution, cancellation and correction ledger absent |
| Adjusted/unadjusted prices | RAW_ONLY | Raw demo fields exist; economic/action reconciliation absent |
| Original-unit volume | REQUIRES_MANUAL_REVIEW | Provider historical adjustment conventions unresolved |
| Delisting/terminal prices | MISSING | No observations |
| USD/HUF | RAW_ONLY | MNB 2023-12-29 sample; date-only reference rate |
| EUR/HUF | RAW_ONLY | Same one-day reference sample |
| FX cross-rates | MISSING | No admitted continuous legs; cannot establish execution availability |
| US fundamentals | RAW_ONLY | Two SEC quarter indexes and one original 2010 filing; no canonical fact panel |
| EU fundamentals | MISSING | No verified dated IFRS issuer/OAM panel |
| Filing publication/vintages | REQUIRES_MANUAL_REVIEW | SEC acceptance field alone does not establish dissemination or restatement handling |
| US inflation/labor/policy | RAW_ONLY | CPIAUCSL, CPILFESL, UNRATE, FEDFUNDS; 2010-01–2023-11 periods |
| US yield curves | RAW_ONLY | DGS10/DGS2 bounded chunks; vintage-boundary stitching and publication unresolved; 3M leg missing |
| EU inflation | RAW_ONLY | One euro-area HICP index; geography/base units not admitted |
| EU unemployment/policy/curves | MISSING | No usable observed panel; no non-euro jurisdiction fallback |
| US/EU credit spreads | MISSING | No captures, third-party rights unverified |
| US/EU financial conditions/liquidity | MISSING | No captures or admitted definitions |
| US/EU broad market | MISSING | No admitted regional index history |
| Sector benchmarks | MISSING | No historical sector classification/components |
| VIX / volatility proxy | MISSING | No admitted series |
| Scheduled events | MISSING | Realized dates and current schedules cannot establish ex-ante knowledge |

## Narrow possible remedies, not admitted substitutions

- Macro: stitch real-time chunks, verify exact series units/geography and original
  release-time evidence. A conservative later-EOD availability policy can be evaluated
  if supported by dated publication evidence; date labels alone do not certify it.
- Equities/universe/actions: dated exchange/issuer filings may form an audited narrow
  proxy panel. Current survivors alone cannot support the intended general USA/EU claim.
  A bounded low-cost historical vendor is a candidate after entitlement, adjustments,
  delistings and rights are demonstrated; no purchase is justified yet.
- FX: prior-known official MNB reference rates remain a proxy candidate, not executable
  quotes. Publication/correction policy must be resolved before admission. A timestamped
  FX vendor could address the limitation, but availability/price is unverified.
- Fundamentals: original dated SEC/issuer filings can preserve vintages; extraction,
  acceptance/publication semantics, taxonomy/unit handling and issuer mapping remain.
  A professional PIT provider is optional, not a prerequisite to software proof.

Bias risks: survivorship/composition bias, revision hindsight, false economic dips,
same-day fixing look-ahead, stale-price substitution and backcast euro-area membership.
The source map records which missing capability is required for the prototype and which
can remain structurally missing. None may be silently dropped from research criteria.

## Gates

| Gate | Status |
|---|---|
| Foundation and Features/Targets/Regimes software | PASS (prior checkpoint) |
| Actual admitted PIT development panel | FALSE |
| Panel quality/admission report accepted as complete panel evidence | FALSE |
| Current audit inventory/report written | TRUE |
| Real-panel leakage gate | REAL_PANEL_LEAKAGE_GATE_BLOCKED_BY_DATA_ADMISSION |
| Models/Policy/Validation start | NOT AUTHORIZED; data gates fail and separate human approval required |
| Financial model / OOS runs | 0 / 0 |
| Retrospective holdout | NOT RUN; NOT PRISTINE |

The blocked real-panel check includes availability, revisions, publication lag,
historical universe, regional calendars, FX, corporate actions, target isolation and
future observations. Synthetic checks cannot substitute for any of these real-panel
claims. No 2024+ financial observations accessed in this phase; earlier documented
incidents remain and no whole-project pristine assertion is made.
