# Development panel admission — 2026-10-06 closure assessment

**DCA_RESEARCH_GATE = BLOCKED_BY_DATA.** No actual PIT development panel is
admitted: 0 rows, 0 securities, no admitted date range, no admitted US or EU
coverage. All tiers remain unassigned. No financial model or OOS run occurred.
This is an honest blocked checkpoint, not proof that free data cannot ever work.

The merged software base remains intact. New evidence: 430 historical US delisted
listing records (424 Stock, 6 ETF, 2 missing names), 2 splits and 34 dividends for
one US demo instrument. The active listing request returned no listing data.
Nine retained FRED captures contain 13,435 vintage rows; raw bounds, finite
numeric values, keys, inclusive interval non-overlap and API count/offset checks
PASS. Vintage rows/chunks are not distinct market sessions or a full macro basket.
New action records pass basic date/key/amount checks; publication/correction and
adjustment semantics are still unresolved. All 14 prior raw hashes reverified.
See `raw-data-quality-results.json` and `observed-source-inventory.json`.

| Required family | Current decision / exact missing evidence |
|---|---|
| Historical US/EU universe | METHODOLOGY_BLOCKED_BY_DATA: partial US listing sample only; no active cohort, EU historical master, stable identifiers, primary common-equity eligibility, ex-ante changes or terminal consideration |
| OHLCV and original volume | METHODOLOGY_BLOCKED_BY_DATA: one US survivor sample; no admitted EU/delisted coverage, correction lineage, action reconciliation or original-unit volume |
| Corporate actions | METHODOLOGY_BLOCKED_BY_DATA: RAW_ONLY split/dividend sample; no complete merger/spin-off/delisting ledger or publication/revision history |
| HUF FX | METHODOLOGY_BLOCKED_BY_DATA: one-day MNB references, no historical availability/correction evidence or admitted full conversion legs |
| Fundamentals | METHODOLOGY_BLOCKED_BY_DATA: SEC accession evidence is not a normalized PIT fact panel; EU coverage absent; dissemination, taxonomy, currencies, restatements and security mapping unresolved |
| Macro/credit/conditions | METHODOLOGY_BLOCKED_BY_DATA: partial date-vintage samples; no admitted publication rules, full regional basket, units/geography/rights or curve stitching |
| Market/sector context | METHODOLOGY_BLOCKED_BY_DATA: no dated benchmark/security/calendar/classification mapping or admitted context history |
| Ex-ante events | METHODOLOGY_BLOCKED_BY_DATA: no schedule-known-at versions; realized event dates are insufficient |

`configs/research_readiness_v1.json` covers every frozen feature raw dependency,
execution-price/action/FX prerequisites and both regions. Its preflight evaluator
lists evidence shortfalls; it **cannot** authenticate a panel or return READY.
`research-readiness-preflight.json` is the reproducible blocked result, not leakage
test evidence. No globally required family is waived as ordinary missingness.
The final positive path requires independent artifact-bound real-panel validation
that has not been implemented against actual data. It is not simulated here.

No canonical panel, PIT snapshots, feature store or target store were fabricated.
Real-panel leakage is **BLOCKED / NOT EXECUTED**, with the entire required check
list in `real-panel-leakage-report.md`. Recession Core remains diagnostic-only,
`HISTORICAL_DIAGNOSTIC_BLOCKED_BY_DATA_ADMISSION`; no real-input score generated.

Each remedy, impact, paid candidate scope and purchase decision is in the updated
`provider-decision-matrix.md`. Numeric costs remain unverified; request samples and
quotes before deciding. No purchase, subscription or external provider contact.

Four deliberate financial requests completed with pre-send historical bounds and
redirects disabled. An earlier interrupted listing attempt has unknown dispatch
count. Search/document excerpts incidentally exposed 2024+ observations; this phase
does **not** claim zero exposure. Incident documentation is preserved, those values
were not incorporated or used in decisions, and retrospective holdout remains
**NOT RUN / NOT PRISTINE**. See `source-search-access-incident-2026-10-06.md`.

The complete preceding report is preserved below as historical evidence.

# Historical development panel admission — 2026-10-05

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
