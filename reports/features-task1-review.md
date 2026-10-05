# Features / Targets / Regimes — Task 1 independent review

Date: 2026-09-16. Reviewed commit `5d8d3fc` against base `b8135c8`, using the supplied `features-task1-review.diff`, Task 1 brief, execution preflight, implementation report, controlling amendment, frozen design §§6–9, and the downstream Task 2–3 interfaces.

## Verdict

- **Spec compliance: FAIL.** The registry satisfies the versioning, required-field, PIT metadata, base-signal count, panel-budget, regime-reserve, and current-list identity requirements, but it omits a Task 3 required universe-percentile output and leaves the Task 2 dollar-volume contract economically under-specified for split handling and the joint US/EU universe.
- **Code quality: FAIL.** Strict root/feature/dependency schemas and immutable definitions are good, but the claimed direct-identity rejection can be bypassed by ordinary identifier variants such as `ticker_code`.
- **Task 1 gate: NOT PASSED.** Correct the findings below before Task 2 depends on this frozen V1 contract.

## Evidence and scope

The checked registry loads as 80 registered features from 69 controlled base signals. Five interpretable-regime and eight maximum unsupervised-regime probability slots yield a maximum final panel of 93, inside the required 80–95 range while accommodating both branches if validated. Every current feature has the required name, domain, raw dependencies, lookback, availability rule, quality floor, and transform; dependency objects enforce the literal `available_at <= prediction_timestamp` rule and `as_of_vintage`. The current list contains no direct security identity and does not mechanically expand every indicator or macro transform.

The reported **6 focused / 400 full** tests are accepted as supplied evidence. Per review instruction, the suites were not rerun; the report already discloses that the full run preceded the final allocation change and that the focused registry suite passed afterward. I used one narrow, offline in-process probe of `_reject_identity` after code inspection exposed a specific boundary doubt: `ticker` and `security.ticker` reject, while `ticker_code`, `issuer_ticker_code`, `symbol`, and `cusip` accept. No network, raw data, holdout access, financial experiment, model fit, implementation edit, or subagent was used. This report is the only intentional write.

## Findings

### F1 — HIGH — `configs/features_v1.yaml:394–406`; `reports/features-task1-implementation.md:82–87`

The controlled list ends its relative-strength block with `momentum_sector_percentile` and then begins fundamentals; it contains no eligible-universe percentile. The implementation report explicitly lists `universe momentum percentile` as deferred. That conflicts with the approved Task 3 producer interface, which requires historical **sector/universe percentiles** (`docs/superpowers/plans/2026-09-11-quant-dca-features-targets-regimes.md:112–137`), and with frozen design §7.4/§8 (`docs/quant-dca-engine-v1-design-spec.md:337–348,433–452`). Task 3 therefore cannot produce all of its assigned final outputs without changing the supposedly frozen V1 registry.

**Required fix:** register at least the task-assigned historical momentum universe percentile with membership/PIT dependencies, eligible-universe normalization, and a literal test. Rebalance the bounded panel by removing only an optional, economically redundant representation if necessary; do not defer an explicit downstream interface.

### F2 — HIGH — `configs/features_v1.yaml:11–56,298–320`

The liquidity definitions are not a complete economic contract. `median_dollar_volume_20d_log` says `adjusted_close_times_volume`, but does not specify whether volume is raw or reciprocally split-adjusted. Multiplying backward-adjusted price by original-unit volume creates artificial turnover jumps around splits; the existing provider policy specifically records that price feeds may return split-adjusted volume and prohibits treating ambiguous returned volume as raw liquidity (`reports/provider-decision-matrix.md:35`). The same feature and Amihud denominator are labeled dollar volume across a joint US/EU model, yet the registry has no currency/FX dependency and states neither native-currency turnover nor a common-currency conversion convention. Values in USD, EUR, HUF, and other EU currencies would consequently be incomparable under the current `log1p` representation.

**Required fix:** freeze an explicit split-consistent turnover basis (for example, unadjusted close × original-unit volume, or a verified reciprocally adjusted price/volume pair) and test split invariance. Also either add the PIT-safe FX/currency dependencies and common reporting currency required for cross-region comparability, or rename and define the feature as native-currency turnover with a downstream normalization that makes currency units irrelevant. Apply the same denominator contract to Amihud.

### F3 — MEDIUM — `src/quant_dca/features/registry.py:24–26,369–372`; `tests/features/test_registry.py:17–36,144–179`

Identity validation tokenizes an underscore-delimited identifier as one token and compares only exact members of a short denylist. As reproduced, `ticker_code`, `issuer_ticker_code`, `symbol`, and `cusip` pass. The first test checks only exact forbidden strings in the current registry, and the negative fixture covers only `security.ticker`/`ticker`. The present V1 list is clean, but the machine validator does not uphold the stated “no direct security identity” contract for later controlled edits.

**Required fix:** validate identifier components and a controlled set of direct security-ID synonyms (including ticker/symbol, ISIN, CUSIP, SEDOL, FIGI, and internal security/entity IDs) across names, formulas, applicability metadata, and dependency names. Add parameterized bypass regressions; avoid substring rules that would reject unrelated economic words.

No other material Task 1 finding was identified. The quality-floor field is correctly treated as an acceptance threshold rather than a provider assignment, unknown schema fields fail closed, and actual feature computation, joins, normalization, and regime fitting remain properly outside this task.
