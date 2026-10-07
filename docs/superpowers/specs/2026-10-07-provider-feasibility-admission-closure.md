# Quant DCA V1 — Provider Feasibility & Admission Closure

## AUTHORITATIVE REPOSITORY STATE

GitHub repository:

`https://github.com/Imemoth/quantitative-dca`

Current verified `main` merge commit:

`2717926687378696e8b02a9ed7e3f4d4a4d8e1fe`

Current working branch already created:

`research/provider-feasibility-admission-closure`

Use this branch.

Do NOT work directly on `main`.

---

# 0. CURRENT VERIFIED PROJECT STATUS

The latest reviewed checkpoint established:

- Foundation software/PIT gate: PASS
- Features / Targets / Regimes: PASS
- Recession Risk Core software: PASS
- Data Acquisition & Admission Closure checkpoint: REVIEW PASS for correct blocked conclusion
- tests: 954/954 PASS
- compileall: PASS
- git diff --check: PASS
- financial model research runs: 0
- financial OOS runs: 0
- retrospective holdout: NOT RUN
- admitted real panel: 0 rows
- admitted securities: 0
- real-panel leakage gate: BLOCKED
- DCA research gate: BLOCKED_BY_DATA

New raw evidence already exists outside public Git:

- \~430 delisted US securities
- 2 split records
- 34 dividend records

This evidence is NOT equivalent to data admission.

The private raw evidence package must remain outside public Git.

---

# 1. PRIMARY OBJECTIVE

The sole objective of this phase is:

> Determine whether a credible, economically usable, point-in-time 2010–2023 US + EU development panel can be constructed from free / low-cost sources under the frozen Quant DCA V1 methodology.

This phase is not general data collection.

It is a **provider feasibility decision phase**.

For each critical data domain, establish one of:

- ADMITTABLE_FREE
- ADMITTABLE_LOW_COST
- ADMITTABLE_ONLY_PAID
- PROXY_POSSIBLE_WITH_LIMITATION
- UNSUPPORTED_FOR_PIT
- METHODOLOGY_BLOCKED_BY_DATA

Do not leave important domains in vague “maybe usable” states.

---

# 2. STRICT RESEARCH BOUNDARIES

Development cutoff:

`2023-12-31`

The retrospective holdout:

`2024-01-01 → 2026-09-11`

remains NOT RUN and must not be used for:

- provider performance selection;
- financial model selection;
- threshold tuning;
- feature selection;
- strategy evaluation.

Do not request post-2023 financial observations for development research when the endpoint can be bounded beforehand.

If documentation/search results incidentally expose post-2023 examples, document them and exclude them from research evidence.

---

# 3. NO MODEL RESEARCH

Do NOT run:

- direction models;
- return models;
- better-entry models;
- calibration;
- NetWaitEV;
- DCA policy;
- benchmark backtests;
- 2015–2023 nested OOS;
- holdout analysis.

Financial model/OOS counters must remain:

`0 / 0`

until human approval after the data gate.

---

# 4. CRITICAL DOMAIN 1 — HISTORICAL UNIVERSE

This is the highest-priority blocker.

You must determine whether we can reconstruct, for each relevant historical date:

- security identity
- primary listing
- active_from
- active_to
- exchange
- region
- historical ticker/name
- common-equity eligibility
- delisted status
- corporate events affecting identity

for:

## USA

- active equities
- delisted equities

## Europe

- active equities
- delisted equities

The result must avoid current-universe survivorship bias.

A current ticker list plus historical prices is NOT sufficient.

---

# 5. HISTORICAL UNIVERSE PROVIDER FEASIBILITY

Research and verify candidate sources.

Candidates may include, but are not limited to:

- exchange / regulator archives
- Alpha Vantage listing-status history
- EODHD exchange + delisted endpoints
- Stooq
- official exchange archives
- regulator datasets
- other documented APIs
- low-cost commercial datasets
- Norgate
- Sharadar
- SimFin metadata where relevant

Do not prefer a source because it was previously mentioned.

For each provider, verify with documentation and/or bounded probes:

- historical membership/listing reconstruction capability
- delisted coverage
- earliest usable date
- exchange coverage
- identifier stability
- primary vs secondary listing handling
- request-time historical date filtering
- licensing/reuse terms
- cost tier
- documented limitations

---

# 6. CRITICAL DOMAIN 2 — TERMINAL ECONOMICS

Delisting presence alone is insufficient.

For delisted securities, determine whether we can obtain or reconstruct:

- final tradable price
- cash merger consideration
- stock merger terms
- acquisition exchange ratio
- bankruptcy terminal value / recovery where available
- delisting date
- final executable session

The research system must never silently treat:

`no more prices`

as:

`security disappears with no economic consequence`.

For every candidate source, assess terminal-event fidelity.

If a free source identifies delistings but not economic outcomes, explicitly classify that limitation.

---

# 7. CRITICAL DOMAIN 3 — OHLCV + CORPORATE ACTIONS

For both USA and EU, verify:

- daily open/high/low/close
- volume
- adjusted vs unadjusted semantics
- splits
- cash dividends
- spin-offs if relevant
- mergers
- symbol changes
- historical currency
- original-share-unit volume

The provider must document enough semantics that:

- return features
- executable-entry targets
- dividend handling
- volume/liquidity features
- corporate-action adjustments

can be reproduced.

An unexplained “adjusted close” alone is not sufficient.

---

# 8. CRITICAL DOMAIN 4 — FUNDAMENTALS / VALUATION PIT

For USA and EU separately, determine if we can obtain:

- reported revenue
- EPS
- cash flow
- margins
- balance sheet
- shares
- debt
- publication timestamps
- period end
- revision/restatement handling

The key question is not:

“Does the API have historical fundamentals?”

The key question is:

> Can we reproduce what the model could have known on a specific historical date?

Latest-restated-history-only datasets are not automatically acceptable.

For each provider classify:

- true historical vintage
- filing-derived reconstructable vintage
- latest-only history
- unknown revision semantics

---

# 9. CRITICAL DOMAIN 5 — MACRO / CREDIT / FINANCIAL CONDITIONS

Complete feasibility for:

## USA

- CPI
- core CPI
- unemployment
- policy rate
- 3M Treasury
- 2Y Treasury
- 10Y Treasury
- HY spread
- IG spread
- financial conditions
- central-bank liquidity
- activity proxy

## EU

- HICP
- core HICP
- unemployment
- ECB / jurisdiction-specific policy rates
- sovereign curve proxy
- HY / IG or defensible credit proxy
- financial conditions
- activity proxy

For each series establish:

- observation date
- publication date
- vintage/revision availability
- source units
- request-time bounded history
- region / jurisdiction validity

Prefer official sources where feasible.

---

# 10. CRITICAL DOMAIN 6 — FX

Determine a PIT-safe historical source for:

- USD/HUF
- EUR/HUF
- any required cross rates

Need:

- quote convention
- fixing/session timestamp
- holiday handling
- source timezone
- availability semantics
- historical completeness

The execution model must be able to reproduce HUF acquisition cost without future FX leakage.

---

# 11. CRITICAL DOMAIN 7 — MARKET CONTEXT / EVENT CALENDAR

Assess feasibility for:

- broad US market
- broad EU market
- sector benchmarks
- VIX or defensible volatility proxy
- earnings announcement dates
- CPI/HICP release schedules
- Fed/ECB decision dates

Scheduled event dates may only be used when their announcement/schedule was already known at the prediction timestamp.

Do not assume modern calendars existed historically in identical form.

---

# 12. PROVIDER EVIDENCE STANDARD

A provider receives a positive feasibility classification only with evidence.

Allowed evidence includes:

- official documentation
- API schema
- bounded sample response
- documented historical date behavior
- explicit licensing statement
- reproducible probe

Marketing copy alone is not enough.

For each important claim, record:

- source URL / reference
- date accessed
- claim
- evidence strength
- caveat

---

# 13. DATA QUALITY / ADMISSION DECISION MATRIX

Maintain one authoritative matrix with columns at least:

- domain
- provider
- region
- free/paid
- historical coverage
- delisted coverage
- PIT capable
- vintage capable
- publication timestamp
- corporate actions
- terminal economics
- request bounded
- unit semantics
- licensing
- current status
- quality confidence
- methodological risk
- recommended decision

Use explicit decisions:

- `PREFERRED`
- `ACCEPTABLE`
- `PROXY_ONLY`
- `REJECT`
- `PAID_FALLBACK`
- `UNRESOLVED`

---

# 14. COST DISCIPLINE

Do NOT purchase anything.

If paid data becomes justified, produce a decision memo.

For every paid candidate include:

- provider
- product/package
- approximate pricing if publicly available
- domains solved
- remaining gaps
- whether PIT semantics are actually solved
- whether EU is covered
- whether delisted/terminal economics are covered
- lock-in risk
- estimated research value
- cheaper alternatives

The key decision is:

> Does paying materially reduce methodology risk enough to justify the cost at prototype stage?

---

# 15. MINIMUM VIABLE RESEARCH PANEL

Define a concrete `MVRP` — Minimum Viable Research Panel.

This must state the minimum data required before the first model run is allowed.

At minimum consider:

- historical universe
- delisted securities
- terminal treatment
- OHLCV
- corporate actions
- FX
- enough fundamentals for frozen features
- enough macro for frozen features
- market context
- feature availability timestamps
- target isolation

For each required domain label:

- mandatory
- degradable
- proxy-allowed
- optional

Do not silently reclassify frozen-model dependencies as optional.

---

# 16. FEATURE COVERAGE IMPACT

Map every frozen V1 feature family to required admitted data.

Produce:

`reports/feature-data-coverage-matrix.csv`

For each feature / feature family record:

- dependency domains
- current provider candidate
- admission feasibility
- expected missingness
- structural missingness
- global unavailability risk
- whether model research remains valid

This is critical.

A feature that is missing for some securities is different from a feature that is unavailable for the entire historical universe.

---

# 17. FALLBACK DECISION TREE

Create a machine- and human-readable fallback hierarchy.

Example:

Primary provider fails
→ alternative free official source
→ alternative free commercial source
→ documented proxy
→ low-cost paid source
→ methodology-blocked escalation

Never jump directly from “free source imperfect” to paid.

Never jump from “paid source inconvenient” to weakening PIT rules.

---

# 18. SMALL-SCALE PROOF-OF-FEASIBILITY PANEL

Only after selecting candidate sources:

construct a tiny bounded proof panel.

Suggested scope:

- a small US sample
- a small EU sample
- includes at least one delisted security
- includes at least one corporate action
- includes one reporting/fundamental vintage sequence
- includes macro vintages
- includes FX

Use only pre-2024 data.

The purpose is NOT performance testing.

The purpose is to prove:

- joins work
- lineage works
- PIT semantics work
- identifiers survive changes
- delisting/terminal handling works
- units and currencies reconcile

---

# 19. PROOF PANEL DATA QUALITY TESTS

Run:

- uniqueness
- date continuity
- OHLC validity
- currency validity
- corporate-action chronology
- historical identity continuity
- publication lag
- revision replay
- FX chronology
- delisting chronology
- terminal-event treatment
- missingness by domain

Document all defects.

---

# 20. PROOF PANEL LEAKAGE TEST

Run the real PIT leakage test on the proof panel.

Hard conditions:

- no feature input available after prediction timestamp
- no later revised macro value
- no later-restated fundamental
- no future index/universe membership
- no future ticker mapping
- no future corporate action knowledge
- no target contamination
- no future FX
- no future calendar revision

Hard failure if violated.

---

# 21. NO FALSE PASS

Do not set:

`DCA_RESEARCH_GATE = PASS`

based on a tiny proof panel alone.

The proof panel can only establish:

`ARCHITECTURE_WITH_REAL_DATA = FEASIBLE`

The actual research gate requires sufficient USA + EU panel coverage for the frozen research design.

---

# 22. RECESSION RISK CORE

Use admitted macro data only as a secondary consumer to confirm its real-data compatibility.

Do NOT expand its scope.

No:

- probability model
- historical threshold optimization
- Macro Risk Gate
- policy integration

in this phase.

---

# 23. PUBLIC GITHUB RULES

The repository is public.

Never commit:

- raw provider data
- private evidence ZIPs
- proprietary data
- credentials
- API keys
- secrets
- raw full responses if redistribution is restricted
- Parquet/DuckDB panel files

Commit only:

- code
- tests
- configs
- provider metadata
- non-sensitive manifests
- reports
- schemas
- evidence summaries
- decision matrices

Raw research evidence remains external/private.

---

# 24. REQUIRED DELIVERABLES

Produce:

1. `reports/provider-feasibility-final.md`
2. `reports/provider-decision-matrix.md`
3. `reports/feature-data-coverage-matrix.csv`
4. `reports/minimum-viable-research-panel.md`
5. `reports/terminal-economics-feasibility.md`
6. `reports/historical-universe-feasibility.md`
7. `reports/fundamental-pit-feasibility.md`
8. `reports/macro-pit-feasibility.md`
9. `reports/fx-feasibility.md`
10. `reports/proof-panel-quality.md`
11. `reports/proof-panel-leakage.md`
12. `reports/paid-provider-escalation.md`
13. updated `reports/readiness-manifest.json`
14. updated research ledger
15. test/review evidence

---

# 25. INDEPENDENT REVIEWS

Before closing this phase obtain:

1. independent provider/data-methodology review
2. independent PIT/leakage review
3. independent code-quality review

A review PASS must state exactly what passed.

Do not describe:

“provider feasibility review PASS”

as:

“data panel admitted”

unless actual admission occurred.

---

# 26. SOFTWARE VERIFICATION

Run:

```bash
python -m pytest -q
python -m compileall -q src tests
git diff --check

```

Starting baseline:

`954 tests PASS`

Do not reduce coverage.

---

# 27. SUCCESS STATES

At the end choose exactly one primary state.

## STATE A — RESEARCH_READY

Only if:

- credible USA and EU provider stack selected
- required historical universe feasible
- delistings feasible
- terminal treatment feasible
- core OHLCV / actions / FX feasible
- fundamental PIT feasible enough for frozen design
- macro PIT feasible
- proof panel passes PIT/leakage
- no unresolved methodology-critical blocker remains

Then:

`DCA_RESEARCH_GATE = READY_FOR_HUMAN_APPROVAL`

Do NOT start models yet.

---

## STATE B — CONDITIONAL_READY

Use only if:

- architecture/proof panel works
- most required domains solved
- one or more limited gaps remain
- gaps have explicit, bounded methodological impact
- a specific paid or proxy decision could resolve them

Do not start model research without human decision.

---

## STATE C — BLOCKED_BY_DATA

Use if a methodology-critical domain remains unresolved.

Return exact blockers and cheapest credible remediation.

This is a scientifically valid outcome.

---

# 28. CHECKPOINT

At completion, create a checkpoint ZIP containing:

- code
- tests
- configs
- reports
- Git history
- verification evidence

Do NOT include private raw datasets.

Provide a separate private evidence bundle only if needed.

Report:

- final commit SHA
- test count
- provider stack recommendation
- US feasibility
- EU feasibility
- historical universe feasibility
- terminal economics feasibility
- fundamental PIT feasibility
- macro PIT feasibility
- FX feasibility
- proof-panel row/security/date coverage
- proof leakage result
- paid escalation recommendation
- DCA research gate status
- model research runs
- OOS runs
- holdout status
- any 2024+ exposure incident

---

# 29. MANDATORY STOP

After this checkpoint:

**STOP.**

Do not start:

- Models / Policy / Validation
- nested OOS
- DCA benchmark testing
- full recession research
- retrospective holdout
- production/Codex work

Wait for human review.

---

# SCIENTIFIC PRIORITY

The objective is not to maximize the number of available datasets.

The objective is to determine whether the frozen Quant DCA V1 hypothesis can be tested without unacceptable:

- survivorship bias
- look-ahead bias
- revision leakage
- corporate-action distortion
- FX leakage
- terminal-value bias

using a financially reasonable prototype data stack.

If it cannot, say so explicitly.

Do not trade methodological validity for progress percentage.