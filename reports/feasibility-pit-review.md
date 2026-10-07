# Independent feasibility PIT review

Date: 2026-10-07. Reviewer: independent `feasibility_pit_closure` agent.
Reviewed source scope: recovered `2717926..52e56a4`, plus the current closure
working tree for status consistency. The previous PIT review verdict was not
available as an artifact; this is a fresh, scoped review, not a reconstruction of
an earlier verdict. No financial observations were requested or examined and no
financial/OOS model was run during this review.

## Verdict

**PASS_FOR_BLOCKED_ASSESSMENT_ONLY.** No Critical or Important PIT/leakage finding
was identified in the reviewed feasibility changes. This verdict approves the
correctness of leaving the research gate **BLOCKED_BY_DATA**. It is not provider
admission, a real-panel leakage PASS, proof of a workable paid stack, or permission
to begin model research.

## Evidence inspected

- Feature-data coverage matrix and frozen feature dictionary/registry; provider
  matrix, evidence summaries, macro inventory and provider-feasibility contract.
- Historical-universe, terminal-economics, fundamental, macro, FX and minimum-panel
  reports; proof-panel quality/leakage reports and machine status.
- Readiness manifest, phase access receipt and final feasibility report.
- `src/quant_dca/admission/readiness.py` and feasibility/current-phase tests.
- Frozen design sections 9–13 and the frozen regime configuration.

Git comparison found no changes from `2717926` to `52e56a4` in
`configs/features_v1.yaml`, `configs/regimes_v1.yaml`, either frozen dictionary or
`src/quant_dca`. This phase does not alter feature, target, regime or execution
methodology. The 94 slots remain 81 registered outputs plus 13 alternative regime
slots; reserved slots are not represented as fitted models.

## PIT and leakage assessment

1. Historical membership and stable identity remain unresolved. The reports
   correctly reject present-day membership and the use of a last-price filter as
   a historical-universe filter. An audited historical proxy remains permitted;
   the frozen specification has not been strengthened to demand perfect coverage.
2. Delisted identification is distinguished from cash/share/recovery treatment.
   No automatic final-bar liquidation or assumed zero recovery is introduced.
   Uncertain terminal observations remain eligible for the frozen sensitivity
   treatment once a known event population exists.
3. Observation, publication, effective, provider-availability and revision clocks
   remain separate. Filing-date availability is not treated as same-day-open
   permission. A next-session lag is not claimed to repair revised history.
4. Macro date vintages are not represented as exact release timestamps. Latest-only
   data, chunk-edge vintage truncation, jurisdiction mismatch and uncertain release
   chronology remain explicitly blocked rather than tier C by default.
5. FX reference values are distinguished from executable quotes. Cross-rate
   availability uses the later leg, historical correction/publication evidence
   remains absent, and current ECB policy is not projected back onto 2010–2023.
6. Realized event dates are not admitted as ex-ante calendars. Historical sector,
   benchmark, venue and session mappings remain unresolved dependencies.
7. Request-time observation/vintage bounds remain 2023-12-31. The recovered phase
   receipt reports zero new financial observation requests and preserves incidental
   post-2023 documentation exposure; no pristine-access certification is asserted.
8. Both proof quality and leakage remain `BLOCKED_NOT_RUN` for 0 rows/0 securities.
   The preflight is explicitly declaration-based and always returns blocked; it
   cannot turn a complete set of caller-provided PASS labels into admission.
9. Feature/target isolation and train-only normalization remain real-panel checks
   awaiting data. Passing artifact/unit tests is not represented as financial
   evidence. Model/OOS counters remain 0 and retrospective holdout NOT_RUN.

## Findings

- Critical: **0**.
- Important: **0** within PIT/leakage scope.
- Minor: The coverage CSV's `structural_missingness` column stores the registry
  applicability expression (for example `all_eligible_equities`) rather than a
  standalone missing-value rule. Its companion columns and fundamental report
  explain the intended distinction, and tests enforce the exact registry mapping.
  This is a presentation limitation, not a gate or methodology defect; no change
  is required for this blocked checkpoint.

## Declined to judge / limits

- Exact current provider licensing interpretation, legal suitability and prices:
  those need the independent provider/data review. This review does not endorse
  a categorical FRED or Sharadar legal prohibition from an evidence summary.
- Actual provider response completeness, publication-time accuracy, vendor
  revision replay, corporate-action economics and historical coverage: there is
  no admitted joined real panel to validate.
- Full-suite/compile verification: delegated to the closure verification record;
  this review independently ran the two relevant artifact/status test modules,
  **18 passed in 0.11s**. These are software tests only.
- Final report links, final SHA and removal of pending-review metadata remain
  routine closure work and must describe the real verification results.

No new provider research or architecture expansion is needed to close this PIT
assessment. The data blockers remain blockers after this scoped PASS.
