# Data Admission and Recession Risk Core Implementation Plan

> Use superpowers:executing-plans with TDD, focused checks after each task, logical commits and independent spec/code-quality review at the end.

**Goal:** Audit real development admission and build a separate read-only regional diagnostic scaffold.
**Architecture:** Canonical Observation and existing as-of, calendar and immutable snapshot services remain authoritative. Separate diagnostic registry, evidence admission records, deterministic rule interfaces and immutable output; no investment policy or model dependency.
**Tech Stack:** Existing Python 3.12 / pytest / YAML / Parquet stack only.
**Spec:** `docs/superpowers/specs/2026-10-05-data-admission-recession-core.md` (user-supplied execution mandate).

## Global constraints

- Financial dates 2010–2023 only, checked before reading inputs; diagnostic role only.
- No 2024+ data requests, model research, DCA backtests, tuning or main merge.
- Preserve frozen features, regimes and target contracts byte-for-byte.
- Admission requires evidence, never software success or hash existence.
- No paid source acquisition. Stop after this checkpoint for human review.

## Task 1: Real evidence and admission inventory

Files: reports/development-panel-admission.md, data-source-quality-map.csv,
recession-risk-input-admission.md, data-admission-evidence.json.
Consume retained bounded raw captures and historical reports. Rehash only explicitly
documented development captures, validate date envelopes, compare manifest counts.
Report each required domain, exact gaps and evidence provenance. No new data call
unless its observation AND revision boundaries are demonstrably bounded before send.
Complete the audit report even when the panel remains blocked. No fabricated tier.
Commit the reports independently.

## Task 2: Diagnostic registry and admission contracts

Files: configs/recession_risk_v1.yaml; src/quant_dca/recession_risk/{registry,evidence}.py;
tests/recession_risk/test_diagnostic_contracts.py.
Interfaces: frozen DiagnosticConfig/InputDefinition, Admission, InputEvidence.
Write RED tests for eight pillars, explicit US/FED and EU/ECB mapping, no non-euro
fallback, wrong units/unknown identity/schema/duplicate definitions and insufficient
admission evidence. Implement strict typed immutable contracts, deterministic config
hash and dictionary. Default economic rules are empty: vocabulary is supported, no
empirically selected threshold or healthy-default inference. Focused GREEN; commit.

## Task 3: PIT snapshot and evidence confidence

Files: src/quant_dca/recession_risk/{engine,contracts}.py;
tests/recession_risk/test_engine.py.
Interface: build_snapshot(*, as_of, region, monetary_jurisdiction, evidence,
config, role='diagnostic') -> MacroRiskSnapshot.
RED tests: canonical vintage selection, future observation/revision exclusion,
same-day EOD publication, stale/missing/low-quality/mixed admission, wrong units,
source-content mismatch, future extension replay, permutation invariance,
immutability, unsupported jurisdiction, role and boundary fail before input reads.
Reuse latest_known/assert_pit_safe/previous_eligible_eod/verify_evidence/evidence_frame
and snapshot_hash. Verify each selected observation against its own immutable
canonical snapshot; hash only evidence used as-of, not future archive extensions.
Confidence is explicitly evidence completeness, A/B/C weight, freshness and known
publication share, with critical-input cap; not recession probability. Focused GREEN;
commit.

## Task 4: Deterministic state and driver interfaces, architecture

Files: src/quant_dca/recession_risk/rules.py; tests/recession_risk/test_rules.py,
test_architecture.py; reports/recession-risk-input-dictionary.csv.
Interfaces: versioned band Rule and conjunction ScenarioRule; immutable PillarState,
Driver, dominant/secondary scenario. RED tests: exact band boundaries, ordered rules,
partial evidence stays UNKNOWN, all-missing has no positive driver, structured drivers
identify selected inputs, aggregation requires complete critical evidence, config
changes identity. Add import-boundary and frozen-file SHA checks. Implement skeleton,
empty default scenario rules, generated dictionary and serialized snapshot support.
Focused GREEN; commit.

## Task 5: Documentation, verification and independent checkpoint review

Write full-dashboard, probability-V2 and macro-gate experiment design notes, readiness
manifest and checkpoint. Actual historical diagnostic remains explicitly BLOCKED
unless a genuine admitted macro panel exists. Tests are software evidence only.
Run full pytest, compileall and git diff --check. Request independent spec and code
quality reviews of branch against supplied spec; fix important findings with RED/GREEN.
Do not close without both PASS. Package committed branch for human review, no merge.

## Review focus

1. Forged/mismatched admission evidence must not promote a row (Task 2/3 tests).
2. Wrong regional series or monetary jurisdiction must not silently fall back (2/3).
3. Late revisions and source snapshot identity must not rewrite earlier outputs (3).
4. Stale critical evidence must not yield a benign state or high confidence (3/4).
5. Mutable nested config or imported DCA/target code must not breach isolation (2/4).
