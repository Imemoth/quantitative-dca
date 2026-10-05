# Features Task 2 implementation

## Scope and status

Implements all 22 frozen V1 price/trend, volatility/drawdown, and volume/liquidity outputs. Files: `src/quant_dca/features/price.py`, `src/quant_dca/features/history.py`, and `tests/features/test_price_vol_liquidity.py`. Registry and Foundation contracts were not changed. Independent review is required before Task 3.

This resumes the interrupted untracked implementation, preserving its draft and tests rather than replacing them. Parent handoff records an original missing-module RED; its exact terminal output is not available in this resumed session and is not reconstructed here. No market network calls, real-data research, holdout evaluation, OOS fitting, or subagents were used. Unrelated pre-existing untracked data files were untouched and excluded from the commit.

## Interfaces and economic conventions

- `trailing_return(prices, sessions)` requires all `sessions + 1` trailing prices. `compute_trailing_features(close, high, low, usd_turnover)` accepts aligned sequences, returns exactly the 22 registry names, and performs no PIT selection itself.
- `build_price_features` is the evidenced per-security/as-of ingress. The effective cutoff is the latest eligible exchange EOD at or before prediction. Later evening publications wait for another EOD. Canonical raw revisions and action revisions use Foundation `latest_known`.
- Exchange-calendar sessions are expanded explicitly. Missing actual sessions remain `None`; they are never filled or compressed. An economic chain restarts after a gap, so no complete feature window can cross that gap. Short histories retain available short-lookback features, not imputed long histories.
- Total-return close chains use previous economic close times `(current raw close * split ratio + dividend) / previous raw close`. Cash dividends are reinvested at ex-date close. High and low receive the same day's multiplicative economic-close scale. This is a feature-only OHLC convention, not an executable quote or a cashflow label.
- Complete corporate-action coverage is an explicit external audit assertion (including verified absence of events), with availability, source, and reference. Empty action lists alone establish no completeness. Same-day split/dividend ordering, unsupported actions, currency changes and ambiguous vintages fail closed.
- Volatility is sample standard deviation (`ddof=1`) of log returns, annualized by `sqrt(252)`. Downside volatility is standard deviation of `min(log return, 0)` over all 60 returns. Slopes are log-price OLS slope divided by residual RMSE with denominator n. Residual scale <= 1e-14 is numerically degenerate and missing.
- ATR uses mean true range over 20 economic bars divided by current economic close. Drawdowns are negative ratios. Duration counts sessions since the most recent equal maximum in 252 closes. Current drawdown honors the registry's 253-observation availability requirement while comparing to the peak of the last 252 closes. Maximum drawdown uses in-window running peaks.
- USD turnover is raw unadjusted close times verified original-share-unit volume times direct local/USD spot FX. USD requires no FX quote. Volume evidence binds to the raw revision; it may explicitly supply audited original units independently of the canonical volume field. Historical Security currency must be available by each bar's EOD and match that bar. FX fixing and availability must both be <= that historical EOD; caller supplies maximum age. No inversion, cross-pair synthesis, or currency fallback occurs.
- Verified zero turnover is valid for median-dollar-volume (`log1p(0) = 0`), but makes Amihud unavailable. Amihud uses arithmetic absolute economic returns divided by positive USD turnover, then `log1p` of the 20-session mean.
- Raw bars remain immutable and are returned separately. Snapshot records retain selected actions, coverage, volume evidence, listings, FX quotes, and verified discontinuity evidence. Feature clocks conservatively include all selected history dependencies, and canonical quality is the worst selected bar/action/FX/listing tier. Coverage and volume attestations are audit assertions, not automatically assigned provider quality tiers.

## Verification evidence

Runtime recovery: `python -m pip install -e '.[test]'` succeeded using declared dependencies. Bare `pytest` was unavailable on PATH; all actual verification uses `python -m pytest`.

Baseline preserved draft:

```text
$ python -m pytest tests/features/test_price_vol_liquidity.py -q
............                                                             [100%]
12 passed in 1.93s
```

New regression RED caught validating future volume provenance before filtering the prediction cutoff:

```text
$ python -m pytest tests/features/test_price_vol_liquidity.py -q
FAILED tests/features/test_price_vol_liquidity.py::test_future_volume_evidence_cannot_change_historical_snapshot
ValueError: MISSING_VERIFICATION_PROVENANCE
1 failed, 15 passed in 2.16s
```

The minimal fix moved volume provenance validation inside the security/availability filter. Additional tests cover absent/mismatched historical currency, propagated listing quality, local-price/FX rescaling invariance, and zero-volume ingress.

```text
$ python -m pytest tests/features/test_price_vol_liquidity.py -v
collected 16 items
============================== 16 passed in 2.06s ==============================

$ python -m pytest -q
431 passed in 5.96s
```

Full suite was run once after the focused GREEN. It exited 0 without warnings. Focused tests include literal split/dividend neutral-return and split-neutral turnover assertions, exact formula/lookback checks for every registry output, crisis preservation, actual-ingress future price/action/volume mutations, late revisions/publications, timely historical FX, missing inputs, genuine session gaps, and degenerate scales. `git diff --check` exited 0.

## Self-review and limits

Reviewed the brief, preflight, frozen registry, Foundation canonical types, corporate-action economics, PIT vintage/clock logic, exchange calendar and FX implementation. Preserved separation from raw execution prices and from target generation. Fixed future-volume validation leakage through a failing regression before editing production code.

Audit completeness and original volume units must be established outside this module; these APIs do not discover provider capabilities or manufacture evidence. The ingress deliberately rejects historical currency switches rather than attempting redenomination economics. Listing availability at each historical EOD is conservative. A non-spot quote selected by Foundation is not accepted for turnover. Missing/unusable liquidity inputs do not suppress otherwise valid price features. Provenance clocks and quality are snapshot-wide, not minimal per-feature dependency sets, and can therefore be conservative. No real-data eligibility or financial-performance gate is claimed. Independent review remains outstanding.

## Independent review correction round 1

Read `reports/features-task2-review.md` fully and reproduced both reported ingress defects. The earlier statement that Foundation contracts were unchanged describes the initial commit; this correction adds one explicitly opted-in validation mode while retaining default canonical admission unchanged.

P1: selected, available corporate-action vintages now reject `available_at < announced_at` when an announcement timestamp is supplied. Since accepted availability is <= prediction EOD, accepted explicit announcements are also <= that EOD and covered by the conservative max-input clock. Absent announcement clocks stay absent; no clock is invented. Genuinely future-unavailable action records are still filtered before payload validation, including contradictory future payloads.

P2: `validate_ohlcv(..., allow_missing_volume=True)` validates a price-feature view only. This explicitly allows absent/None canonical volume without modifying or replacing the original row. It is not strict raw-canonical admission. The default remains `False`; present invalid volume, OHLC errors, chronology/provenance, calendars and discontinuity screening remain unchanged. The feature ingress opts in. Independently audited original-share-unit evidence can provide liquidity; without that evidence only liquidity outputs remain missing. A regression explicitly confirms default canonical validation still quarantines all 22 missing-volume bars. Additional actual-ingress regressions exercise missing volume combined with a bad price, an unexplained discontinuity, negative present volume, and an invalid session clock. Thus the correction does not merely discard a quarantine reason after discontinuity screening has already been skipped.

Test-first RED, before either production change:

```text
$ python -m pytest tests/features/test_price_vol_liquidity.py -q
FAILED tests/features/test_price_vol_liquidity.py::test_action_availability_cannot_precede_explicit_announcement
Failed: DID NOT RAISE ValueError
FAILED tests/features/test_price_vol_liquidity.py::test_missing_canonical_volume_preserves_price_only_and_independent_turnover
ValueError: INVALID_FEATURE_HISTORY:MISSING_VOLUME
FAILED tests/features/test_price_vol_liquidity.py::test_price_only_view_does_not_bypass_invalid_bars[change1-UNEXPLAINED_DISCONTINUITY]
Expected regex: 'UNEXPLAINED_DISCONTINUITY'
Actual message: 'INVALID_FEATURE_HISTORY:MISSING_VOLUME'
3 failed, 19 passed in 2.28s
```

Focused GREEN, covering regression suite, and one full-suite run after the correction:

```text
$ python -m pytest tests/features/test_price_vol_liquidity.py -q
22 passed in 2.58s
$ python -m pytest tests/canonical/test_validate.py tests/corporate_actions/test_economics.py tests/point_in_time/test_asof.py tests/features/test_price_vol_liquidity.py -q
118 passed in 2.39s
$ python -m pytest -q
437 passed in 6.43s
$ git diff --check
[exit 0, no output]
```

All GREEN commands exited 0 without test warnings. Self-review checked that the opt-in only changes the missing-volume branch before coherent-panel discontinuity screening, that raw row identity/value is preserved, and that unavailable action filtering still precedes the new announcement check. Only Task 2-relevant code, tests and this report were changed. No market access, holdout work, subagents or Task 3 work occurred. Independent re-review remains required.
