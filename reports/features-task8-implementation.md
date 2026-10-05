# Task 8 — interpretable regime implementation

Implemented 2026-10-03 on `research/development-v1`, base `49ef5f6`.
Authority: Task 8 brief and design-spec sections 5, 8, 9, 22; controller-approved
bounded contract. This is a synthetic software gate, not financial validation.
Task 9 remains blocked until the independent review returns PASS.

## Controlled formula and rationale

`configs/regimes_v1.yaml` defines `interpretable-v1-heuristic-1`: five fixed
prototypes, equal positive dimension weights, temperature 1, coordinate clip 4.
For each state, score is the sum of negative weighted squared coordinate
distances. Stable softmax subtracts the largest eligible score before
exponentiation. Recovery is excluded (probability zero) when its evidence gate
fails. The five output memberships sum to one; hard state is the largest
membership, with ties resolved in the specification's state order.

| State | Trend | Volatility | Credit |
|---|---:|---:|---:|
| EXPANSION_RISK_ON | 1 | -1 | -1 |
| CORRECTION | -1 | 0 | 0 |
| HIGH_VOL_STRESS | 0 | 2 | 1 |
| CRISIS | -2 | 3 | 3 |
| RECOVERY | 1 | 0 | 0 |

These are a-priori qualitative anchors: positive/calm, negative/moderate,
elevated risk, severe joint risk with negative trend, and positive trend after
risk easing. Equal weights avoid asserting a learned hierarchy. Unit temperature
leaves distance scaling unchanged; clipping bounds outlier influence. None of
these parameters was estimated, selected against returns, or financially
validated. They are uncalibrated heuristic membership scores, not calibrated
economic-state probabilities or frozen research selections.

| Existing input | Required declared unit | Fixed reference coordinate |
|---|---|---|
| broad_market_momentum_20d_raw | fractional_return | value / 0.05 |
| vix_level_raw | index_points | (value - 20) / 10 |
| high_yield_spread_raw | percentage_points | (value - 4) / 2 |

Round reference levels/scales make the distances readable; they are not
sample means, standard deviations, rolling estimates, or full-history
normalization. The scalar aliases `vol_z` and `credit_z` exist only for the
plan's API compatibility. No registry definitions/base signals were added;
the five reserved regime output slots remain available for Task 10 wiring.

## Input and explanation contracts

- `predict_proba` and `explain` take exactly `market_trend`, `vol_z`, `credit_z`
  as already dimensionless coordinates. These pure helpers claim no PIT
  provenance. Without optional historical scalars, recovery is zero.
- Evidenced `predict` requires current and historical canonical `FeatureValue`
  triples, explicit prediction timestamp, US/EU region, benchmark MIC, current
  EOD, prior EOD, `PartitionRole`, and all three declared units. It performs no
  fitting, feature production, imputation, or revision selection. Producers
  must supply their already selected PIT snapshots.
- Current EOD is checked against Foundation `previous_eligible_eod(prediction)`;
  prior EOD must be exactly the immediately preceding eligible benchmark close.
  The configured recovery lookback is exactly one benchmark session. US MICs
  are XNYS/XNAS; EU MICs are XETR/XLON/XPAR. Snapshot `as_of` must equal its EOD.
- Recovery requires prior volatility or credit at least one reference unit
  above its center, current trend strictly above zero, neither risk dimension
  rising, and at least one strictly falling. The gate compares original values
  before clipping. Missing historical evidence fails explicitly at `predict`.
- Both complete snapshots' schema, identity, regional provenance, quality,
  observation dates and economic clocks are checked before any numeric value.
  Canonical `assert_pit_safe` enforces availability, publication/revision and
  maximum-input cutoffs at each snapshot's own EOD. Economic dates/clocks must
  be within 2010–2023; offline `computed_at` is audit metadata. Request-level
  outer-OOS/holdout and out-of-range bounds fail before input iteration.
- Exact feature allowlists reject target, ticker/identity and unknown inputs;
  aggregate records require `entity_id=None`. Trend/credit must match requested
  region. VIX may be GLOBAL or the requested region, but must already have been
  available at that region's EOD. A forthcoming US close cannot enter an EU
  snapshot. HY requires quality A/B; other inputs accept canonical A/B/C.
- `feature_units` is mandatory because `FeatureValue`/registry do not encode
  numeric units. No basis-point inference/conversion occurs. The declaration
  is a producer contract, not independent evidence of provider correctness.
- Missing, nonfinite, boolean and nonnumeric required values fail closed.
  Finite extremes are safely clipped before scaling arithmetic. The immutable
  result retains raw and clipped coordinates, prior inputs, each state/dimension
  contribution, scores, all five recovery checks, hard state, membership vector,
  full configuration and SHA-256 hash. Evidenced results also retain all six
  canonical rows and request clocks/region/partition/MIC for replay.

## Changes and verification

Added `src/quant_dca/regimes/__init__.py`, `interpretable.py`, configuration,
`tests/regimes/test_interpretable.py`, and this report. Features/targets remain
isolated; no provider, market/network call, research selection, real-data fit,
outer-OOS observation or 2024+ observation was used. Negative boundary tests
construct only rejected metadata and unreadable sentinels.

Interpreter for commands below:
`/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python`.
The initially restored runtime lacked pytest; controller restored declared
dependencies before a genuine RED run. No package requirement changes were made.

| Gate | Actual result |
|---|---|
| Initial `python -m pytest tests/regimes/test_interpretable.py -q` | **66 failed in 0.97s**, expected missing model/package/config |
| First focused GREEN | **66 passed in 0.98s** |
| Initial full `python -m pytest -q` | **622 passed in 8.63s** |
| Explanation regression RED | **1 failed in 0.42s**, missing `raw_inputs` |
| Final focused `python -m pytest tests/regimes/test_interpretable.py -q` | **67 passed in 0.92s** |
| Final full `python -m pytest -q` | **623 passed in 8.28s** |
| `python -m compileall -q src/quant_dca tests` | **exit 0**, no output |
| `git diff --check` | **exit 0**, no output |

Self-review added the raw-input/recovery-check regression because clipped
coordinates alone cannot explain a failed original-value gate. Tests cover all
five states, literal distances, ties, probability sums, US/EU timing, holiday
prior-session selection, missing/invalid values, extreme finite arithmetic,
configuration effects and invalid configurations, immutable explanations,
identity/target/schema rejection, forbidden partitions and metadata-before-value
checks. Existing 556 tests remain green. Parent status/ledger files and unrelated
untracked raw/fixture files are excluded from this implementation commit.
