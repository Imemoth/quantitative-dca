# Quant DCA V1 — Case C Reconstruction of Lost Provider-Feasibility State

## PURPOSE

The previous Work environment created a local provider-feasibility commit:

`52e56a4`

but that local state was never pushed to GitHub and is no longer recoverable.

This has now been classified as:

**CASE C — LOCAL STATE UNRECOVERABLE**

Do NOT search indefinitely for `52e56a4`.

Do NOT attempt to invent its exact original bytes or commit hash.

Reconstruct ONLY the lost provider-feasibility phase from the latest durable repository state and the known verified outputs of the lost work.

The reconstructed work will naturally receive new commit SHA(s).

---

# 0. AUTHORITATIVE DURABLE START STATE

Repository:

`https://github.com/Imemoth/quantitative-dca`

Expected branch:

`research/provider-feasibility-admission-closure`

Expected durable GitHub HEAD at reconstruction start:

`2717926687378696e8b02a9ed7e3f4d4a4d8e1fe`

Before doing anything:

```bash
git fetch origin
git status
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -10
```

Verify the actual remote branch state.

If GitHub has advanced beyond `2717926`:

**STOP and inspect the divergence before reconstructing anything.**

Do not overwrite newer durable work.

---

# 1. DURABILITY PROTOCOL — NEW MANDATORY PROJECT RULE

The loss of `52e56a4` must not happen again.

From this phase onward:

> No more than one logical checkpoint may exist only inside a transient Work environment.

Every major milestone must be durably preserved.

Preferred order:

1. commit locally;
2. push branch to GitHub;
3. verify remote SHA.

If GitHub push is unavailable:

1. commit locally;
2. create Git bundle;
3. create checkpoint ZIP;
4. preserve both as downloadable artifacts;
5. verify that the bundle contains the expected branch/ref;
6. only then continue.

If neither GitHub push nor artifact export is possible:

**STOP.**

Do not continue accumulating unrecoverable local work.

---

# 2. REQUIRED CHECKPOINT CADENCE

Use the following mandatory checkpoints.

## CHECKPOINT C0 — Reconstruction baseline

Immediately after verifying the durable start state.

Record:

- source branch;
- base SHA;
- current test baseline;
- reconstruction scope;
- explicit declaration that `52e56a4` is unrecoverable.

Commit this documentation.

Durably preserve it before proceeding.

---

## CHECKPOINT C1 — Provider feasibility artifacts reconstructed

Must contain at least:

- provider decision matrix;
- 94-feature data-dependency map;
- blocker/cost report;
- 23-topic US/EU macro gap inventory.

Run targeted structural tests.

Commit.

Then either:

- push to GitHub and verify remote SHA;

or:

- export `checkpoint-C1.bundle`
- export `checkpoint-C1.zip`.

Do not proceed until C1 is durably preserved.

---

## CHECKPOINT C2 — Critical feasibility findings reverified

Must contain reverified conclusions for:

- historical US universe;
- historical EU universe;
- delistings;
- terminal economics;
- US fundamentals PIT;
- EU fundamentals PIT;
- macro PIT / licensing;
- FX;
- market context;
- event calendars;
- paid/free provider tradeoffs.

Commit and durably preserve.

---

## CHECKPOINT C3 — Targeted implementation/tests complete

Expected reconstructed targeted test suite should include at least the functionality represented by the previously reported:

`63/63 targeted tests PASS`

Do not mechanically force the count to exactly 63 if the reconstructed design legitimately differs.

Report the actual targeted test count.

Commit and durably preserve.

---

## CHECKPOINT C4 — Full verification + independent reviews

Run:

```bash
python -m pytest -q
python -m compileall -q src tests
git diff --check
```

Then obtain:

1. independent provider/data-methodology review;
2. independent PIT/leakage review;
3. independent code-quality review.

Resolve Critical/Important findings.

Commit and durably preserve.

---

## CHECKPOINT C5 — Final reconstruction checkpoint

Only after everything above is complete:

- final reports;
- final readiness state;
- final provider decision;
- complete Git history;
- checkpoint ZIP;
- Git bundle if useful;
- branch push.

Then STOP for human review.

---

# 3. RECONSTRUCTION PRINCIPLE

The following lost-work outcomes are historical guidance, NOT automatically trusted facts.

Reconstruct them and independently reverify the underlying evidence.

Known previously reported outputs:

- provider decision matrix completed;
- all 94 frozen V1 feature slots mapped to data dependencies;
- blocker/cost report completed;
- gap inventory covering 23 US/EU macro topics completed;
- 63/63 targeted tests reportedly passed.

Do NOT simply recreate documents containing those claims.

Rebuild the underlying logic and evidence.

---

# 4. KNOWN PRIOR FINDINGS TO REVERIFY

The lost Work session reported the following findings.

Treat them as hypotheses requiring evidence-based reconstruction.

---

## 4.1 Historical universe remained a blocker

The previous work did not establish a sufficiently trustworthy historical US + EU universe for research admission.

Need to re-evaluate:

- historically active names;
- delisted names;
- listing intervals;
- identifier continuity;
- symbol/name changes;
- exchange/region mapping;
- primary listing;
- common-equity eligibility.

Current-universe reconstruction is NOT acceptable.

---

## 4.2 Terminal economics remained unresolved

Delisting detection alone was insufficient.

Need to assess whether we can correctly represent:

- final tradable price;
- cash acquisition;
- share exchange merger;
- bankruptcy recovery;
- liquidation;
- terminal delisting outcome;
- final executable session.

Missing prices after delisting must never silently become:

`return = 0`

or:

`security disappeared`.

---

## 4.3 EU end-to-end data chain remained unresolved

Previous work reported no sufficiently evidenced:

`historical identity → price → PIT fundamentals`

chain for the required EU universe.

Reverify.

Do not weaken the frozen USA + EU scope without explicit human authorization.

---

## 4.4 Sharadar looked technically useful for US data

Previous research suggested Sharadar may address several US data gaps.

However, potential issues were identified around:

- licensing;
- redistribution;
- publication of derived evaluations;
- retention after subscription termination;
- suitability for the intended research workflow.

Reverify exact current terms from authoritative sources.

Separate:

- technical suitability;
- PIT suitability;
- licensing suitability;
- economic suitability.

Do not automatically reject or approve Sharadar.

---

## 4.5 FRED / ALFRED licensing and source ownership require care

Previous research identified that technical vintage capability alone may not prove permissible machine-learning/research usage for every underlying series.

Reverify:

- FRED/ALFRED terms;
- original source-owner restrictions;
- whether individual series have separate rights;
- whether our local research use is permitted;
- whether derived model use introduces restrictions.

Do NOT state a legal prohibition unless the evidence actually supports it.

When uncertain:

`LICENSING_REQUIRES_HUMAN_REVIEW`

is preferable to an invented conclusion.

---

# 5. PROVIDER FEASIBILITY MATRIX

Reconstruct one authoritative provider matrix.

Minimum columns:

- domain
- provider
- product/dataset
- region
- free/paid
- historical coverage
- historical universe capability
- delisted coverage
- terminal economics
- OHLCV
- corporate actions
- fundamentals
- PIT capable
- historical vintage capable
- publication timestamps
- revision/restatement semantics
- request-time date bounding
- stable identifier
- unit semantics
- currency semantics
- licence/reuse status
- post-subscription retention
- approximate cost
- current feasibility status
- evidence confidence
- methodology risk
- recommended role

Decision vocabulary:

- `PREFERRED`
- `ACCEPTABLE`
- `PROXY_ONLY`
- `PAID_FALLBACK`
- `REJECT`
- `UNRESOLVED`

No provider may be `PREFERRED` based only on marketing material.

---

# 6. 94-FEATURE DATA DEPENDENCY MAP

Reconstruct:

`reports/feature-data-coverage-matrix.csv`

for all 94 frozen V1 feature slots.

For each feature record:

- feature name;
- feature family;
- raw dependencies;
- provider candidate(s);
- region;
- PIT requirement;
- current feasibility;
- expected structural missingness;
- expected incidental missingness;
- entire-feature-family availability risk;
- proxy possibility;
- methodology consequence if unavailable.

Distinguish strictly:

### Acceptable

A feature is legitimately missing for some securities/dates.

### Not acceptable

A required feature family has no historical source for the entire research universe.

Do not confuse the two.

---

# 7. 23-TOPIC US/EU MACRO GAP INVENTORY

Reconstruct the previously developed macro gap analysis.

The final count may differ if evidence shows the prior grouping was wrong, but explicitly reconcile any difference from the previously reported **23 topics**.

At minimum cover relevant:

### USA

- headline inflation
- core inflation
- PCE
- core PCE
- unemployment
- employment/payrolls
- policy rate
- 3M yield
- 2Y yield
- 10Y yield
- HY spread
- IG spread
- financial conditions
- liquidity
- growth/activity

### Europe

- HICP
- core HICP
- unemployment/employment
- policy jurisdiction
- sovereign curve
- credit proxy
- financial conditions
- growth/activity

For every topic record:

- source candidate;
- observation date;
- publication date;
- vintage availability;
- revision behavior;
- licensing status;
- PIT feasibility.

---

# 8. COST / BLOCKER REPORT

Reconstruct the blocker and cost report.

For each unresolved methodology-critical domain state:

- blocker;
- impact on research validity;
- free candidate;
- low-cost candidate;
- paid candidate;
- approximate public pricing if available;
- what the paid source actually solves;
- what remains unsolved;
- licensing issue;
- recommended decision.

No paid purchase is authorized.

---

# 9. PROVIDER DISCOVERY SCOPE

Do not restart unlimited broad provider research.

Prioritize only unresolved methodology-critical domains:

1. historical universe;
2. terminal economics;
3. EU price/fundamental identity chain;
4. PIT fundamentals;
5. macro vintages/publication evidence;
6. FX;
7. market/event context.

Investigate additional providers only when they could materially close one of these blockers.

---

# 10. DEVELOPMENT DATA BOUNDARY

All development financial observations remain bounded to:

`<= 2023-12-31`

Do not intentionally retrieve 2024+ financial observations for development research.

If documentation/search results expose later examples:

- document exposure;
- do not use those values;
- do not tune provider/methodology decisions using them.

---

# 11. NO MODEL RESEARCH

Still prohibited:

- direction models;
- expected-return models;
- better-entry models;
- calibration;
- NetWaitEV;
- DCA policy;
- nested OOS;
- DCA benchmarks;
- retrospective holdout.

Required counters:

- financial model runs = 0
- financial OOS runs = 0
- retrospective holdout = NOT RUN

---

# 12. DO NOT BUILD A FAKE PROOF PANEL

If critical provider chains remain unresolved:

do not manufacture a proof panel merely to satisfy the earlier plan.

A proof panel is allowed only when its source semantics are credible.

Otherwise report:

`PROOF_PANEL_BLOCKED_BY_PROVIDER_FEASIBILITY`

This is acceptable.

---

# 13. TARGETED TEST RECONSTRUCTION

Rebuild the lost targeted tests based on the actual reconstructed implementation.

Cover at minimum:

- provider decision enums;
- feature dependency completeness;
- all 94 feature slots accounted for;
- no duplicate feature slot;
- blocker classification;
- macro inventory integrity;
- readiness fail-closed behavior;
- missing critical domain prevents research readiness;
- licensing uncertainty prevents unjustified admission;
- absent terminal economics blocks survivorship-safe readiness;
- EU chain absence blocks full USA+EU research readiness;
- paid candidate presence alone does not create PASS.

Run and record targeted result.

Previous lost state reported:

`63/63 PASS`

The new count may differ.

---

# 14. FULL SOFTWARE VERIFICATION

After reconstruction:

```bash
python -m pytest -q
python -m compileall -q src tests
git diff --check
```

The latest durable pre-reconstruction baseline was:

`954 tests PASS`

The reconstructed final full test count should therefore normally be >=954 unless a documented legitimate test reorganization explains otherwise.

Do not delete tests to obtain green status.

---

# 15. THREE INDEPENDENT REVIEWS

Perform all three fresh after reconstruction.

## Review A — Provider/Data Methodology

Focus:

- survivorship bias;
- universe reconstruction;
- terminal economics;
- provider claims;
- costs;
- licensing;
- USA/EU scope.

## Review B — PIT / Leakage

Focus:

- historical availability;
- publication timestamp;
- revisions;
- latest-history leakage;
- request bounds;
- identifier leakage;
- universe leakage.

## Review C — Code Quality

Focus:

- contracts;
- fail-closed readiness;
- maintainability;
- evidence/provenance;
- deterministic outputs;
- test quality.

For each review preserve:

- verdict;
- Critical;
- Important;
- Minor;
- declined-to-judge.

A PASS must state exactly what passed.

---

# 16. FINDING RESOLUTION

Any Critical or Important finding must be:

- fixed;
- retested;
- committed;

or explicitly left as a data blocker where code cannot fix it.

Do not “solve” a missing dataset by weakening methodology.

---

# 17. FINAL FEASIBILITY STATE

Choose exactly one.

## RESEARCH_READY

Only if all methodology-critical provider requirements are credibly solved.

## CONDITIONAL_READY

Only if remaining blocker(s) are narrowly bounded and there is a concrete human decision that would close them.

Example:

> one specific paid provider/package closes the last required data domain with acceptable PIT/licensing semantics.

## BLOCKED_BY_DATA

Use when one or more methodology-critical dependencies remain unresolved.

Do not force CONDITIONAL_READY merely because much work was completed.

---

# 18. PAID PROVIDER ESCALATION

If paid data appears justified, produce a final comparison.

At least:

- provider;
- package;
- approximate cost;
- historical universe;
- delisted;
- terminal economics;
- USA;
- EU;
- fundamentals;
- PIT/vintage;
- corporate actions;
- licensing;
- retention rights;
- remaining gaps;
- recommendation.

Explicitly answer:

> If we spend money now, what exact scientific risk disappears?

and:

> What scientific risk remains after paying?

---

# 19. PUBLIC GITHUB RULES

GitHub is public.

Never commit:

- raw private provider data;
- raw evidence bundles;
- proprietary source files;
- API keys;
- `.env`;
- credentials;
- redistribution-restricted responses;
- research Parquet/DuckDB data.

Public Git may contain only:

- code;
- tests;
- configs;
- schemas;
- decision matrices;
- reports;
- evidence summaries;
- safe manifests.

---

# 20. CHECKPOINT IMPLEMENTATION

Durability is now a first-class requirement.

At every C0–C5 checkpoint:

### Preferred

```bash
git add ...
git commit ...
git push origin research/provider-feasibility-admission-closure
git fetch origin
git rev-parse HEAD
git rev-parse origin/research/provider-feasibility-admission-closure
```

Confirm local and remote SHA match.

### If push unavailable

Create:

```bash
git bundle create <checkpoint-name>.bundle research/provider-feasibility-admission-closure
```

Then verify:

```bash
git bundle verify <checkpoint-name>.bundle
```

Also create a checkpoint ZIP.

Do not continue until an external downloadable copy exists.

---

# 21. CHECKPOINT ZIP CONTENT

Each checkpoint ZIP should contain:

- source;
- tests;
- configs;
- docs;
- reports;
- verification evidence;
- `CHECKPOINT.json`;
- `RESTORE.md`;
- Git bundle if practical.

`CHECKPOINT.json` must include:

- branch;
- commit SHA;
- base SHA;
- timestamp;
- stage;
- tests run;
- test results;
- research counters;
- holdout state;
- known blockers.

`RESTORE.md` must explain exact recovery commands.

---

# 22. PRIVATE EVIDENCE

If new raw/provider evidence is gathered:

store it in a separate private evidence bundle.

Never place private evidence inside the public checkpoint ZIP unless redistribution is explicitly safe.

The public checkpoint should refer to evidence by:

- hash;
- provenance identifier;
- safe summary;

not by embedding restricted raw content.

---

# 23. FINAL REQUIRED OUTPUTS

At reconstruction completion deliver:

1. provider feasibility final report;
2. provider decision matrix;
3. 94-feature coverage matrix;
4. 23-topic macro gap inventory;
5. blocker/cost report;
6. paid-provider escalation report;
7. historical universe feasibility;
8. terminal economics feasibility;
9. US fundamental PIT feasibility;
10. EU fundamental PIT feasibility;
11. macro PIT/licensing feasibility;
12. FX feasibility;
13. proof-panel feasibility status;
14. readiness manifest;
15. research ledger;
16. targeted test evidence;
17. full-suite evidence;
18. all three review reports;
19. final checkpoint ZIP;
20. recoverable Git bundle where needed.

---

# 24. FINAL REPORT

Explicitly report:

- Case C reconstruction performed: YES
- original `52e56a4` recovered: NO
- reconstructed final SHA
- checkpoint C0 SHA/artifact
- checkpoint C1 SHA/artifact
- checkpoint C2 SHA/artifact
- checkpoint C3 SHA/artifact
- checkpoint C4 SHA/artifact
- checkpoint C5 SHA/artifact
- GitHub branch HEAD
- targeted tests
- full tests
- review verdicts
- US universe feasibility
- EU universe feasibility
- terminal economics feasibility
- US fundamentals PIT
- EU fundamentals PIT
- macro PIT/licensing
- FX
- proof panel status
- paid-provider recommendation
- admitted panel rows
- admitted securities
- final DCA research gate
- financial model runs
- OOS runs
- holdout state
- any 2024+ exposure.

---

# 25. MANDATORY STOP

After C5:

**STOP FOR HUMAN REVIEW.**

Do not start Models / Policy / Validation.

Do not run nested OOS.

Do not run DCA backtesting.

Do not run the retrospective holdout.

Do not continue into production work.

---

# CORE PRINCIPLE

The reconstruction is successful if it restores a scientifically defensible decision state.

It is NOT necessary for the final result to be `RESEARCH_READY`.

A rigorously evidenced:

`BLOCKED_BY_DATA`

is preferable to a falsely optimistic research pipeline.

And from now on:

> Work that is not durably checkpointed does not count as completed project state.