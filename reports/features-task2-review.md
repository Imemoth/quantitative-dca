# Features Task 2 independent review

Reviewed base `7c8af05` through implementation `3e619c7`, including the complete supplied 600-line diff, Task 2 brief, execution preflight, implementation report, all 22 relevant frozen registry records, and only the Foundation interfaces needed to evaluate the new integration.

**Spec compliance: FAIL. Code quality: FAIL.** Two ingress issues require correction before Task 3. The numeric feature formulas and literal lookback lengths otherwise agree with the frozen contract.

## Findings

### P1 — Reject contradictory future action-announcement evidence before applying an action

Location: `src/quant_dca/features/history.py:90–109` (and dependency clock aggregation at lines 190–191).

The new action ingress gates `available_at`, and `latest_known` validates publication/revision chronology, but neither validates `CorporateAction.announced_at`. Consequently an action whose explicit announcement is after prediction can be applied to historical returns when its `available_at` is earlier. The output also advertises an input clock before that announcement. This violates the registry's announced-action-vintage contract and the requirement for evidenced, causal corporate-action inputs. This is a new-ingress validation obligation, not a request to reopen unchanged Foundation behavior.

A narrow offline probe using the existing 22-bar fixture supplied a dividend of 10 on bar 10, `available_at` at the first close, and `announced_at` one day after the prediction close. The builder accepted it and changed `return_20d_raw` from `0.19801980198019797` to `0.30693069306930676`. Existing future-action coverage mutates `available_at`/`revised_at`, not this explicit announcement clock.

Required correction: fail closed on contradictory action chronology (at minimum availability preceding a supplied announcement), retain absent announcement clocks as absent rather than inventing them, and add an actual-ingress regression proving this record cannot affect the historical output. Continue filtering genuinely future unavailable records before validating their payloads.

### P2 — Missing canonical volume aborts price-only features and independently verified turnover

Location: `src/quant_dca/features/history.py:117–119`.

The unconditional whole-bar validator rejects `OHLCV.volume=None` before the builder reaches its separate `VolumeEvidence` path. This suppresses every feature even when all OHLC prices are valid and action history is verified. It also prevents independent audited original-share units from supplying turnover when the canonical volume field is missing. The implementation report explicitly promises both independent audited volume and that missing/unusable liquidity inputs do not suppress valid price features; price-only registry outputs do not depend on volume.

A narrow offline probe changed only canonical volume to `None` on the existing 22-bar fixture and supplied no volume evidence. Instead of valid price outputs plus missing liquidity, the builder raised `ValueError: INVALID_FEATURE_HISTORY:MISSING_VOLUME`. The same early rejection necessarily occurs with valid independent volume evidence because validation precedes that evidence's use.

Required correction: keep strict raw-bar admission separate from feature-specific dependency availability; do not fill or fabricate canonical volume. Preserve usable price features when only volume is missing and allow separately verified units to satisfy the liquidity dependency. Add regressions both without and with independently evidenced original units.

## Contract checks that passed inspection

- Exactly 22 assigned registry names; returns 5/20/60/120/252, MA distances 20/50/200, slopes 20/60, 252-close high distance, realized volatilities/ratio/downside volatility, ATR, current/max drawdowns/duration, median USD turnover, and Amihud. Literal minimum lengths agree, including the 253-observation current-drawdown requirement.
- Split/dividend total-return chaining is separate from immutable executable raw bars. Same-day mixed split/dividend ordering and unsupported relevant actions fail closed. Coverage is an explicit sourced audit assertion, not inferred from empty action lists.
- Actual exchange sessions are expanded; missing sessions remain missing and break the economic chain. No filling, compression, clipping, identity predictors, target imports, global normalization, or learned transforms were introduced.
- Existing focused tests exercise known-vintage cutoff, future price/action/volume revisions, after-close publication, genuine crisis evidence, short histories, gaps, formulas, zero denominators and zero turnover.
- Turnover uses raw close times explicitly verified original-share volume times direct local/USD spot FX. Historical listing currency is required and checked against the bar. Both fixing and availability are constrained to each historical EOD, with explicit staleness policy. No inverse/cross-pair synthesis or currency fallback was introduced.
- Snapshot-wide provenance and worst selected canonical quality are conservative as documented; coverage and volume assertions do not manufacture provider quality.

## Verification and scope

Accepted the implementation report's **16 focused / 431 full passing tests as reported evidence**; neither suite was rerun. Those tests do not cover the two cases above. Ran only the two narrow synthetic probes described above and `git diff --check 7c8af05 3e619c7` (passed). No market data, network, holdout evaluation, model research, or subagents were used. No implementation changes were made; only this review report was written. Unrelated untracked data was left untouched. Broader unchanged Foundation review is deferred.
