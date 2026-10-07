# Data Acquisition & Admission Closure Implementation Plan

> Use superpowers:executing-plans with TDD and independent final reviews.

**Goal:** Determine whether actual research data can meet the frozen V1 gate.
**Architecture:** Reuse provider/raw/PIT infrastructure; add only inspection and
machine-readable admission contracts needed to distinguish evidence from claims.
**Tech Stack:** Existing Python/pytest/JSON/YAML stack.
**Spec:** ../specs/2026-10-06-data-acquisition-admission-closure.md

## Global constraints

2010–2023 financial data only; pre-request cutoff; zero financial/OOS research;
no paid purchase; no frozen methodology changes; no raw data in Git; final STOP.

## Task 1: Source acquisition and constraints in priority order

- [ ] Verify merged tree and new branch, record previous 911-test baseline.
- [ ] Investigate historical universe/terminal economics first, then prices/actions,
  FX, fundamentals, macro, market context and schedules.
- [ ] Only bounded data endpoints may be probed; save raw externally with hash and
  request-bound receipt. Record unavailable access and unsafe endpoints explicitly.
- [ ] Distinguish official documentation, actual response and unverified capability.
- [ ] Create provider-decision-matrix and source inventory; commit evidence summaries.

## Task 2: Inspect retained/new evidence and define readiness contract

Files: src/quant_dca/admission/{profile,readiness}.py; tests/admission/;
configs/research_readiness_v1.json; reports/observed-source-inventory.json.
Interface: profile_fred(document) -> aggregate checks (no financial values),
assess_readiness(contract, evidence) -> BLOCKED_BY_DATA or READY_FOR_HUMAN_APPROVAL.

- [ ] RED tests reject duplicate composite keys, conflicting revisions, unbounded
  clocks, false row-count completeness and invalid numeric values.
- [ ] GREEN minimal aggregate profiler; profile only known bounded captures.
- [ ] RED readiness tests: globally absent family blocks even if other inputs allow
  missingness; wrong region, incomplete coverage, missing evidence/review/leakage
  cannot pass; synthetic evidence cannot count as an actual panel.
- [ ] GREEN strict machine contract and deterministic blocker evaluation; actual
  evidence remains unadmitted unless independent factual evidence establishes it.
- [ ] Focused checks and commit. No generic model infrastructure expansion.

## Task 3: Admission decisions and real-panel gate

- [ ] Update all required reports with observed counts, statuses and blocker/remedy
  matrix. Admit only if source semantics, quality/rights and data checks are proven.
- [ ] If no genuine admitted panel, mark real leakage and diagnostic smoke BLOCKED,
  not PASS and not an attempted OOS run. Record actual admitted coverage as zero.
- [ ] Run full pytest, compileall and diff-check; commit.

## Task 4: Independent reviews and final checkpoint

- [ ] Independent spec, code-quality and data-admission reviews; fix Important issues
  with RED/GREEN and fresh suite; obtain PASS before software closure.
- [ ] Create history/source/report checkpoint without raw/provider data; record SHA,
  tests, admission/coverage, exposure and zero research counters. STOP human review.

## Review focus

1. A hash/documentation claim must not become source admission.
2. One supported region or macro family must not hide missing US/EU universe.
3. Date-range min/max must not imply complete session or vintage coverage.
4. Repeated vintage chunks must not fabricate economic revision timestamps.
5. Readiness cannot depend on arbitrary caller strings claiming real leakage PASS.
