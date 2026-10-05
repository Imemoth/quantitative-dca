# Quant Equity Probability & DCA Engine — V1 Design Specification

**Status:** Design freeze candidate  
**Version:** 1.0-draft-for-user-review  
**Design date:** 2026-09-11  
**Primary use case:** DCA entry timing optimization for liquid US and EU-listed equities  
**Secondary future use case:** short-horizon trading signals, only after V1 timing edge is independently validated

---

## 1. Executive objective

The project will not attempt to predict an exact future stock price. V1 will estimate a set of probabilistic and expected-return targets and convert them into an auditable DCA timing decision.

The final decision objective is **C — DCA entry decision optimization**, built from:

- **A — direction probability**, and
- **B — expected return estimation**.

The system must answer, at each DCA decision point:

> Is it economically preferable to buy now, wait for a better executable entry, or abstain from timing and follow the baseline DCA schedule?

The production action set is:

- `BUY_NOW`
- `WAIT`
- `NO_EDGE`

`STRONG_BUY` may exist only as a reporting label in V1. It does not change position size.

V1 tests **timing edge only**. It must not simultaneously optimize stock selection and timing. Asset selection can be added only after timing performance is understood.

---

## 2. Design principles

1. **Economic usefulness over statistical cosmetics.** A statistically significant but economically negligible effect is not sufficient.
2. **Complexity must earn its place.** A more complex model is adopted only if it produces meaningful incremental out-of-sample value.
3. **Point-in-time correctness is non-negotiable.** No model input may contain information unavailable at the prediction timestamp.
4. **Execution must be realistic.** Signals based on EOD data cannot execute at the same close.
5. **Uncertainty is a valid outcome.** If evidence is conflicting or insufficient, the system returns `NO_EDGE` and follows normal DCA.
6. **The lockbox is sacred.** Final holdout data may be examined only after research decisions are frozen.
7. **No expensive data procurement before evidence of edge.** V1 uses free or low-cost data wherever practical, with explicit data-quality flags.
8. **Research reproducibility.** Every result must be traceable to an immutable dataset, feature schema, model configuration and code version.

---

## 3. Scope

### 3.1 Included markets

V1 covers:

- United States equities
- European Union-listed equities

The predictive universe consists of sufficiently liquid, primary-listed common equities with a large- and mid-cap emphasis.

### 3.2 Excluded from the predictive universe

V1 excludes as target securities:

- ETFs
- preferred shares
- warrants
- OTC securities
- shell/SPAC vehicles before operating-company conversion
- duplicate secondary listings where the primary listing is available

ETFs and indices may still be used as market-context features.

### 3.3 Historical period

- Initial history starts in **2010**.
- Initial training warm-up: **2010-01-01 through 2014-12-31**.
- Development walk-forward OOS: **2015-01-01 through 2023-12-31**.
- Final untouched lockbox: **2024-01-01 through 2026-09-10 EOD**, using only data available by that fixed cutoff.

The 2008 global financial crisis is not required in V1. The 2010–2026 period contains multiple stress, crash, recovery, inflation and policy regimes and is considered sufficient for the prototype.

### 3.4 Data frequency

V1 is **daily / EOD only**.

No intraday signal generation or intraday execution optimization is allowed in V1.

---

## 4. Prediction horizons and targets

V1 uses three horizons:

- **5 trading days** — short entry timing
- **20 trading days** — primary monthly DCA horizon
- **60 trading days** — medium-term return/trend context

A separate 10-day horizon is deliberately excluded as redundant between 5D and 20D.

### 4.1 Direction targets

For each eligible stock and decision timestamp:

- `P(return_5D > 0)`
- `P(return_20D > 0)`
- `P(return_60D > 0)`

### 4.2 Expected-return targets

- `E[return_5D]`
- `E[return_20D]`
- `E[return_60D]`

### 4.3 Better-entry classification targets

A better entry is defined by an **economically meaningful executable price improvement**, not any trivial lower price.

- 5D better entry: at least **1.5%** below the baseline executable acquisition cost
- 20D better entry: at least **3.0%** below the baseline executable acquisition cost

Therefore the targets are:

- `P(executable_better_entry_5D >= 1.5%)`
- `P(executable_better_entry_20D >= 3.0%)`

### 4.4 Better-entry distribution targets

V1 must estimate the distribution of the best executable entry opportunity within the allowed wait window:

- `ExecutableMinReturn_5D`
- `ExecutableMinReturn_20D`

At minimum the decision engine should receive:

- Q25
- Q50 / median
- Q75

and, where robust, an expected value estimate.

### 4.5 Executability rule

The better-entry target must use **future executable session prices**, not intraday lows that cannot be guaranteed as fills.

Reference V1 execution model:

`EOD signal at t -> earliest execution at next tradable session open`

Thus a better-entry window is evaluated using future eligible open prices after the signal timestamp.

### 4.6 Local and investor-base-currency targets

Each timing result is calculated in two forms:

1. local security currency (`USD`, `EUR`, etc.)
2. investor base currency

Default V1 base currency:

`HUF`

The final DCA action is evaluated using effective HUF acquisition cost, including FX, configured execution costs and any economically relevant distributions foregone because of delayed ownership. The same economic-equivalence rule is used when evaluating the 1.5% and 3.0% better-entry thresholds.

For backtest execution, FX must be sampled at or before the security execution timestamp. Preferred order is: (1) a timestamped FX quote aligned to the security open; (2) if only daily FX bars are available, that calendar day's FX open as a documented proxy. A later same-day fixing/close may not be used to price an earlier stock execution.

---

## 5. Market regime architecture

The regime layer is a distinct model subsystem, not merely a collection of volatility features inside the stock model.

Two regime approaches run in parallel.

### 5.1 Interpretable regime branch

Human-auditable reference states:

1. `EXPANSION_RISK_ON`
2. `CORRECTION`
3. `HIGH_VOL_STRESS`
4. `CRISIS`
5. `RECOVERY`

The rule-guided/supervised branch exists as an interpretable benchmark and diagnostic layer.

### 5.2 Unsupervised regime branch

Primary candidate:

- Hidden Markov Model (HMM)

Challenger:

- Gaussian Mixture Model or comparable clustering model

The unsupervised branch tests **3 through 8 states**. It is not forced to match the five human labels.

State-count selection considers:

- out-of-sample likelihood
- state stability through time
- transition stability
- economic interpretability
- incremental predictive usefulness for downstream 5D/20D/60D targets

The system may retain both the interpretable regime and unsupervised state probabilities if both add independently validated value.

### 5.3 Regime outputs

Downstream models should receive probabilities rather than only a hard label where possible, e.g.:

- `P(expansion)`
- `P(correction)`
- `P(stress)`
- `P(crisis)`
- `P(recovery)`
- unsupervised state probabilities
- selected transition-risk measures if validated

---

## 6. Macro architecture

Macro features are region-aware. A joint USA+EU stock model must not use a US-only macro representation.

### 6.1 US macro inputs

At minimum:

- headline CPI
- core CPI
- unemployment rate
- Fed policy rate
- US 10Y–2Y yield curve
- US 10Y–3M yield curve
- US high-yield credit spread
- US investment-grade credit spread
- financial conditions proxy
- Fed balance-sheet / liquidity proxy

### 6.2 European Union macro inputs

At minimum:

- headline HICP
- core HICP
- euro-area/EU unemployment
- ECB policy/deposit rate for EUR monetary jurisdiction
- local central-bank policy rate for non-EUR EU monetary jurisdictions
- EUR/German sovereign curve proxy for the common euro-area rates backdrop
- European high-yield spread proxy
- European investment-grade spread proxy
- European financial-conditions proxy

Each EU security stores a `monetary_jurisdiction` / `currency_area` mapping. Euro-denominated securities use the ECB policy layer; non-euro EU securities use the relevant local policy-rate series while retaining common EU/global risk features. V1 does not require a full country-by-country macro feature explosion.

### 6.3 Global risk inputs

Examples include:

- VIX
- broad global risk-off/equity stress measures

### 6.4 Macro representation

Where economically meaningful, features use a controlled combination of:

- current level
- 3-month change
- 6-month change
- 12-month change
- acceleration/deceleration

Not every series automatically receives every transform.

### 6.5 Publication timing

Macro values are usable only after they were actually released.

Reference period is not availability time.

Vintage-aware data is required where revisions matter. ALFRED/FRED-style vintage handling is preferred for US macro data.

---

## 7. Feature architecture

V1 targets approximately **80–95 final model features**, derived from roughly 50 economically motivated base signals. It explicitly avoids brute-force generation of hundreds of technical indicators.

### 7.1 Price / trend

Candidate set includes:

- 5D return
- 20D return
- 60D return
- 120D return
- 252D return
- distance from MA20
- distance from MA50
- distance from MA200
- normalized 20D trend slope
- normalized 60D trend slope
- distance from 52-week high
- trend consistency measure

RSI, MACD and similar classic indicators are not automatic V1 features. They may enter only as later challengers with documented incremental OOS value.

### 7.2 Volatility / drawdown

Candidate set includes:

- 20D realized volatility
- 60D realized volatility
- 20D/60D volatility ratio
- downside volatility
- ATR as percentage of price
- current drawdown
- 60D maximum drawdown
- 252D maximum drawdown
- drawdown duration
- downside/upside volatility asymmetry

### 7.3 Volume / liquidity

Candidate set includes:

- 20D median dollar volume
- volume z-score
- 20D/60D volume trend
- Amihud-type illiquidity proxy
- gap frequency
- abnormal-volume × price-direction interaction

V1 does not attempt to infer high-frequency market microstructure from EOD data.

### 7.4 Relative strength / cross-sectional

Candidate set includes:

- 20D / 60D / 120D return relative to sector
- 20D / 60D / 120D return relative to broad market
- momentum sector percentile
- momentum universe percentile
- volatility sector percentile
- drawdown sector percentile

Cross-sectional values must be calculated using only the eligible universe present at the historical timestamp.

### 7.5 Fundamentals / quality / growth

Point-in-time candidate set includes:

- revenue YoY growth
- EPS YoY growth
- FCF YoY growth
- gross margin
- operating margin
- FCF margin
- operating-margin YoY change
- ROIC
- ROE
- net debt / EBITDA
- interest coverage
- share dilution YoY
- last known earnings surprise
- days since last reported earnings

Fundamental metrics have an explicit `applicability` mask. Economically invalid metrics are not force-imputed across sectors. In particular, banks/insurers must not be treated as if industrial `net debt / EBITDA` or conventional `EV/EBITDA` were meaningful. For financials, V1 uses a compact sector-appropriate subset where reliable point-in-time data exists, such as P/E, price/book or tangible-book proxies, ROE and selected capital/credit-quality measures. Unavailable sector-specific measures remain structurally missing.

US-GAAP and IFRS standardized fields are normalized through the canonical provider layer and carry source/data-quality metadata; cross-region comparability is checked during Work-phase data audit.

### 7.6 Valuation

Candidate set includes:

- trailing P/E
- EV/EBITDA
- price/sales
- FCF yield
- earnings yield
- valuation relative to own rolling history
- P/E sector percentile
- EV/EBITDA sector percentile
- FCF-yield sector percentile

Forward valuation metrics may be included only when point-in-time estimate history is reliable enough to avoid revision/look-ahead contamination.

### 7.7 Market / cross-asset

Candidate set includes:

- broad-market 20D / 60D momentum
- technology/growth benchmark momentum where relevant
- sector 20D / 60D momentum
- VIX level
- VIX change / acceleration
- market-breadth proxy
- index realized volatility
- regional market features

### 7.8 Known event-calendar risk

V1 includes a small point-in-time event-risk block because short DCA horizons are sensitive to scheduled gap catalysts. Only events whose dates were genuinely known/announced at the prediction timestamp are permitted. Candidate features include:

- days to next announced earnings release
- binary announced-earnings-within-5D / within-20D
- days to next scheduled Fed/ECB policy decision relevant to the security
- binary major-policy-event-within-5D
- days to next scheduled CPI/HICP release relevant to the region

If a future event date was not yet announced at the historical prediction timestamp, the feature is missing. Today's reconstructed event calendar may not be projected backward.

### 7.9 Categorical structural features

Allowed examples:

- region
- sector
- market-cap bucket
- beta bucket
- growth/value characteristics
- liquidity class

### 7.10 Ticker identity

Direct ticker identity is **prohibited in V1**.

The model must learn relationships based on economic characteristics, not memorize that a particular ticker historically performed well.

---

## 8. Normalization rules

Normalization is feature-specific and point-in-time.

Possible representations include:

- raw value
- rolling historical z-score
- sector percentile
- full eligible-universe percentile

Guidelines:

- price/volatility/liquidity: raw plus selected rolling and cross-sectional forms
- fundamentals: raw plus sector-relative representation where meaningful
- valuation: raw plus own-history normalization plus sector percentile
- macro: level plus trend/acceleration
- regime: probabilities directly

No full-history normalization is allowed.

---

## 9. Point-in-time truth model

The central rule is:

> A feature may be used only if it was actually available at the prediction timestamp.

### 9.1 Canonical timestamps

Each observation stores, as applicable:

- `observation_date`
- `period_end`
- `published_at`
- `available_at`
- `effective_date`
- `market_session`
- `source`
- `revision_id`

### 9.2 As-of joins

Feature reconstruction uses:

`available_at <= prediction_timestamp`

This is an as-of join, not an ordinary historical join.

### 9.3 EOD execution convention

Reference convention:

`market close -> feature calculation -> signal -> next tradable session open execution`

If an input timestamp is ambiguous, the conservative next-session availability assumption is used.

### 9.4 Earnings availability

- before-market release: may enter the first EOD feature snapshot after that session
- after-market release: may enter the following session's EOD snapshot
- uncertain release timestamp: conservative next-session treatment

V1 intentionally avoids intraday reaction modeling.

### 9.5 Macro availability

Even if a macro release occurs before the market open, V1 incorporates it into the next EOD signal-generation cycle rather than modeling same-session intraday execution.

### 9.6 Revisions and restatements

Historical predictions must use the value known at the historical timestamp, not today's revised value.

This applies to:

- macro revisions
- corporate restatements
- analyst estimates/revisions if introduced later

### 9.7 Universe point-in-time

Historical universe membership must use historical eligibility, not today's constituent list projected backwards.

Required conceptual fields include:

- active_from
- active_to
- exchange
- region
- historical index membership where available

---

## 10. Corporate actions and return integrity

A mechanical ex-dividend price drop must not be interpreted as a successful dip entry.

The feature and target pipeline therefore uses appropriate corporate-action-adjusted price series for economic return calculations. For DCA timing comparisons, the system also calculates an **economic acquisition cost** so that waiting across an ex-dividend date does not receive false credit merely because the raw share price mechanically falls.

Conceptually, when the baseline buy-now holder would have become entitled to a distribution before the delayed entry, the value of that foregone distribution is added to the delayed-entry economic cost (with the same currency-conversion convention). Thus timing edge is measured on an economically equivalent basis rather than raw quoted price alone.

The portfolio simulator separately handles:

- actual fill price
- dividends/cashflows
- splits
- mergers/spin-offs where applicable
- delistings
- FX
- transaction costs

Feature-return accounting and execution accounting must remain conceptually separate.

---

## 11. Universe eligibility and survivorship handling

Survivorship-free data is the desired end state, but V1 may use an audited proxy universe to avoid expensive institutional data costs before edge is proven.

### 11.1 Eligibility requirements

Initial eligibility requires:

- active primary common equity
- USA or European Union
- minimum 120 trading sessions of history
- sufficient liquidity according to configured thresholds
- at least one known published fundamental report where fundamental features are required

Longer-history features may remain missing for younger companies.

### 11.2 Delistings

A security may not disappear from the historical sample merely because it no longer trades today.

Where reliable data exists, use:

- delisting price
- merger consideration
- bankruptcy recovery/terminal value

If terminal return is unreliable, flag the observation and include it in survivorship-sensitivity analysis rather than silently removing it.

---

## 12. Data-source strategy

V1 prioritizes free or low-cost sources and uses a provider abstraction layer.

Conceptual flow:

`raw provider -> provider adapter -> canonical schema -> PIT validation -> feature store`

Potential source categories:

- FRED / ALFRED for US macro and vintages
- low-cost/free historical OHLCV providers
- historical constituent/delisting proxy sources
- low-cost fundamental APIs where sufficiently reliable
- separate European data adapters where US providers are inadequate

The model and downstream layers must not depend directly on a specific vendor schema.

Institutional PIT datasets are considered only after V1 passes the predefined evidence gates.

---

## 13. Data quality architecture

Every source/observation is assigned a quality tier:

- **Tier A:** true point-in-time, timestamped, revision-aware
- **Tier B:** reliable historical data with some PIT/revision limitations
- **Tier C:** reconstructed/proxy data with documented uncertainty

Backtest reporting must distinguish at least:

- results using A/B quality data
- results using all permitted data

If apparent edge depends materially on Tier C data, it is not considered fully validated.

### 13.1 Missing data

Rules:

- no backward fill
- macro/fundamental values may be forward-carried only after they were genuinely known
- price observations are not blindly forward-filled
- exchange calendars distinguish holidays from data failures
- line-model imputation is fit only on the current training fold
- tree models may use native missing handling
- missing-indicator features are added only when economically/data-quality justified

### 13.2 Outliers

True market extremes are preserved.

Data errors are quarantined.

Examples of invalid records include:

- high < low
- impossible/negative volume
- duplicate sessions
- currency mismatch
- huge discontinuity unexplained by a verified corporate action

A crisis observation is not removed merely because it is statistically extreme.

---

## 14. Model stack

V1 uses a **hybrid champion/challenger architecture**.

Deep learning is explicitly excluded from V1.

### 14.1 Direction classification

Baseline:

- regularized logistic regression / Elastic Net logistic model

Challenger:

- gradient-boosted decision trees

Targets:

- 5D direction
- 20D direction
- 60D direction
- 5D better-entry event
- 20D better-entry event

### 14.2 Expected-return regression

Baselines:

- Elastic Net regression
- Huber regression

Challenger:

- gradient-boosted regression

### 14.3 Better-entry distribution

Baseline:

- linear quantile regression

Challenger:

- boosted-tree quantile regression

Required quantiles at minimum:

- Q25
- Q50
- Q75

### 14.4 Probability calibration

Candidate calibration methods:

- Platt scaling
- isotonic calibration

Calibration is trained exclusively inside the current training/validation structure.

The DCA policy receives calibrated probabilities, not raw arbitrary model scores.

### 14.5 Ensemble policy

Ensembling is **not the default**.

An ensemble is permitted only if:

1. each component independently shows positive OOS value;
2. their predictions/errors are sufficiently non-redundant;
3. combination improves nested OOS performance;
4. the improvement is economically meaningful.

Permitted V1 ensemble form:

`weighted average of model predictions`

Weights may be selected only through inner time-series validation.

No unconstrained neural/meta-model stacking is permitted in V1.

---

## 15. Validation architecture

V1 uses **nested expanding walk-forward validation with purging and embargo**.

### 15.1 Initial train

2010–2014 provides the first warm-up/training history.

### 15.2 Development outer OOS

2015–2023 is evaluated in expanding walk-forward blocks.

Reference outer block size:

- **quarterly**

Reference model refit frequency:

- **quarterly**

Feature values are refreshed at EOD / relevant release availability.

### 15.3 Inner validation

Only the currently available training history may be used for:

- hyperparameter selection
- feature selection
- probability calibration
- allowed ensemble weights
- regime state-count selection

Outer OOS data cannot be used for these choices.

### 15.4 Purging, label maturity and embargo

A training row is eligible only when its complete target window is already known at the model-training cutoff. Formally:

`target_end_timestamp <= training_cutoff_timestamp`

Because the longest target is 60 trading days, observations near a fold boundary whose 60D label would extend into the validation/test block are purged automatically. The 5D and 20D tasks apply the same rule using their own target end timestamps.

In addition, V1 applies a **5-trading-session embargo** between the latest target end included in model fitting/model selection and the first signal timestamp of the next validation/test block.

For a later expanding refit, previously tested periods may enter training only after their applicable labels have matured and the embargo requirement is satisfied, matching what would have become knowable in live operation.

### 15.5 Final lockbox

2024-01-01 through 2026-09-10 EOD remains untouched until:

- feature schema is frozen
- model families are frozen
- hyperparameter protocol is frozen
- DCA policy thresholds are frozen
- benchmark definitions are frozen
- success/kill criteria are frozen

The lockbox is then run once as the final historical confirmation.

If the lockbox fails, the project may return to research, but the same lockbox may no longer be treated as an untouched final test for the revised V2 design.

---

## 16. DCA policy engine

### 16.1 Monthly decision cycle and baseline timestamp

For the reference V1 backtest, the monthly contribution is assumed to be available before the **first eligible trading session of each calendar month**. The decision snapshot is the EOD snapshot from the immediately preceding eligible session.

Therefore:

- baseline decision timestamp = previous eligible session EOD
- baseline Fixed-DCA execution = first eligible session open of the new month
- if the contribution has a later real-world availability timestamp, production uses the first eligible session open at or after that timestamp and all benchmarks use the same availability rule

This convention prevents the timing model from receiving an artificial advantage from a different cash-availability assumption.

The portfolio simulator exposes `monthly_contribution_huf` as configuration. The reference user configuration may use 5,500 HUF per unit, while timing metrics remain comparable across contribution sizes except where fixed/minimum fees or lot constraints create non-linear costs. Fractional-share support and platform-specific minimums are therefore execution-model configuration, not hard-coded model assumptions.

At each monthly DCA decision point the engine produces:

- 5D direction probability
- 5D expected return
- 5D better-entry probability
- 5D executable entry distribution
- 20D direction probability
- 20D expected return
- 20D better-entry probability
- 20D executable entry distribution
- 60D direction probability
- 60D expected return
- regime probabilities/state
- local-currency timing value
- base-currency timing value
- confidence/uncertainty measures

### 16.2 Initial 5D WAIT gate

A `WAIT` action requires both:

- `P(>=1.5% better executable entry within 5D) >= 60%`
- `NetWaitEV_5D >= +0.50%` after configured costs

If these conditions are not met with sufficient confidence, the policy returns `BUY_NOW` or `NO_EDGE`.

### 16.3 Daily EOD reevaluation during WAIT

A WAIT does not mean blindly waiting five days.

After every new EOD snapshot during the allowed window:

- features are rebuilt
- predictions are refreshed
- the policy is rerun

Day 0 is the baseline monthly execution session that was skipped because of the WAIT decision. The initial deadline is the **open of the fifth subsequent eligible trading session**. A decision affecting that deadline must therefore be generated no later than the immediately preceding EOD snapshot.

If the model has observed a materially improved acquisition context by an EOD snapshot and the refreshed policy switches to `BUY_NOW`, execution occurs at the next eligible session open. The backtest credits only the actual simulated next-open acquisition cost; it never assumes a fill at an already observed close or historical intraday low.

### 16.4 5D to 20D extension

After the initial window, continued waiting is permitted only with stronger evidence:

- `P(>=3% better executable entry within remaining 20D horizon) >= 65%`
- incremental `NetWaitEV >= +0.75%`

### 16.5 Maximum wait

Maximum deferral for a single monthly DCA contribution:

- **20 eligible trading sessions after the baseline session**

If still waiting, mandatory execution occurs at the open of the twentieth subsequent eligible session. The last policy evaluation that may affect this deadline occurs at the immediately preceding EOD snapshot.

V1 does not allow multi-month cash carry-over for timing purposes. That would combine timing with cash-allocation optimization and is explicitly deferred to a later version.

### 16.6 NO_EDGE

`NO_EDGE` means the model has insufficient reliable evidence to outperform baseline timing.

It does **not** mean remaining in cash.

Action:

- at the initial monthly decision: `NO_EDGE -> execute at the baseline Fixed-DCA open`
- after a WAIT has already begun: `NO_EDGE -> terminate the deferral and execute at the next eligible session open`

The engine never attempts to recreate a baseline execution timestamp that has already passed.

Reasons may include:

- missing/low-quality inputs
- excessive uncertainty
- meaningful disagreement between model families
- historically poor timing reliability in the detected regime
- poor probability calibration

---

## 17. Net Wait EV

The DCA policy must not base WAIT solely on dip probability.

Conceptually:

`NetWaitEV = ExpectedEntryGain - OpportunityCost - IncrementalExecutionFriction`

For the HUF policy, FX is already embedded in HUF-denominated acquisition-cost targets and must **not** be subtracted a second time. For local-currency diagnostics, the same calculation is performed without the HUF conversion layer.

V1 research is limited to two permitted estimators for `NetWaitEV`; Work must select one using only the 2015–2023 nested development protocol and freeze it before the lockbox:

1. **Component EV estimator:** calibrated better-entry probability combined with conditional entry-gain and conditional miss-cost regressions using the same baseline/challenger model families already permitted in the Better-Entry engine.
2. **Cross-fitted policy-value estimator:** a simple regularized regression fitted only on out-of-fold simulated wait-vs-buy acquisition-cost outcomes generated by the frozen reference policy. It may use only current model outputs and current point-in-time features; it may not be an unconstrained meta-learner.

Selection criterion is incremental nested-OOS policy value and calibration/stability, not in-sample fit. If neither estimator produces a stable, economically interpretable `NetWaitEV`, the WAIT action is disabled for the affected policy/horizon in V1 and the system falls back to `BUY_NOW` / `NO_EDGE`. This prevents an unvalidated EV approximation from manufacturing timing decisions.

Probability, expected return, better-entry magnitude and uncertainty must remain independently reported even when `NetWaitEV` is used.

---

## 18. Benchmark architecture

V1 timing performance is compared against multiple fixed benchmarks using the **same security, same contribution amount and same initial decision date**.

Only entry timing varies.

### B0 — Fixed DCA

Buy at the scheduled monthly execution point.

Primary benchmark.

### B1 — Random DCA

Randomly choose a permitted executable entry session within the same monthly window. The reported benchmark is a distribution from **5,000 reproducible full-path simulations** using stored random seeds, not one lucky random schedule.

Used to distinguish genuine timing skill from calendar luck.

### B2 — Simple Dip Rule

Mechanical, non-ML executable rule. After skipping the baseline open, each EOD compares the current economically adjusted acquisition proxy with the baseline reference. If it is at least 1.5% better, the benchmark submits a buy for the next eligible open; otherwise it executes at the fifth-session deadline. The benchmark receives credit only for the actual next-open simulated fill, not the triggering close.

### B3 — Trend/Dip heuristic

A transparent Smart-DCA-style baseline using a small set of trend, drawdown, stress and dip conditions.

### B4 — Always Buy Now

Execute immediately at the first allowed session.

### B5 — Perfect Foresight / Oracle

Retrospective best executable entry in the permitted future window.

The Oracle is not a tradable benchmark. It establishes the maximum timing opportunity that actually existed.

---

## 19. Evaluation metrics

### 19.1 Entry Price Improvement (EPI)

`EPI = (benchmark acquisition cost - model acquisition cost) / benchmark acquisition cost`

Primary economic timing metric.

To prevent thousands of correlated cross-sectional stock observations from creating false statistical precision, the **primary pooled EPI** is computed in two stages: first take the equal-weight mean EPI across eligible securities within each monthly DCA cohort, then average those cohort-level EPI values through time. Security-level observations remain available for sector/ticker diagnostics, but they are not treated as independent time observations for the primary significance claim.

### 19.2 Better-entry hit rate

Measures how often the predefined 1.5% / 3% executable thresholds were achieved when predicted.

### 19.3 Opportunity cost

Measures the cost of waiting when price moves against the WAIT decision.

### 19.4 Regret

Difference between model entry and Oracle best executable entry.

### 19.5 Oracle capture ratio

`CapturedEdge / AvailableOracleOpportunity`

Calculated only where meaningful timing opportunity existed.

### 19.6 Forward returns

Post-entry realized returns over:

- 5D
- 20D
- 60D

### 19.7 WAIT failure rate

Frequency and economic cost of WAIT decisions that failed to produce the required improvement.

### 19.8 Probability quality

Primary:

- Brier Score
- Brier Skill Score versus a base-rate model
- calibration curve/reliability diagnostics

AUC may be reported but is secondary.

### 19.9 Expected-return ranking quality

Cross-sectional rank IC / Spearman correlation between predicted and realized returns.

Stability through time is more important than a single high observation.

---

## 20. Predefined success criteria

V1 proceeds to a more expensive/production-oriented phase only if the combined evidence is strong enough.

### 20.1 Primary timing edge

Required:

- net mean EPI versus Fixed DCA: **>= +0.50%**
- moving-block bootstrap 95% confidence interval lower bound: **> 0**, using calendar-month DCA cohorts as the resampling unit, preserving all securities within a cohort, a default 3-month block length, and 10,000 resamples
- remains positive after configured transaction/spread/FX costs

### 20.2 Complexity hurdle

The ML engine should beat the Simple Dip Rule by at least approximately:

- **+0.15% net mean EPI**

If complexity adds negligible value, the simpler rule wins.

### 20.3 Oracle capture

Target:

- approximately **>=20–25% mean Oracle Capture Ratio** where meaningful opportunity exists

### 20.4 WAIT quality

Required:

- `NetTimingValue > 0`
- high-confidence WAIT predictions should provide at least **10 percentage points precision lift** over the natural base rate of the event

### 20.5 Probability model quality

Required:

- Brier Skill Score > 0

Preferred:

- BSS > 5%

Strong:

- BSS > 10%

Probability calibration must be acceptable for decision use.

### 20.6 Return-model quality

Persistent positive OOS rank IC is required for the return layer to influence the policy.

An approximate sustained range of **0.02–0.05** may already be economically interesting, but stability matters more than a single high IC.

### 20.7 Time stability

Across 2015–2026 historical OOS/lockbox assessment, the desired robustness pattern is:

- positive Fixed-DCA timing edge in at least roughly **8 of 12 calendar years**
- no single year should contribute more than approximately **30–35%** of total edge

### 20.8 Regime stability

Desired:

- positive timing edge in at least **3 of 5 interpretable regimes**

The system may abstain via `NO_EDGE` in historically unreliable regimes.

### 20.9 Cross-sectional robustness

Edge must not depend almost entirely on:

- one ticker
- one narrow industry
- one region
- one market-cap bucket

If it does, the result is reclassified as a narrower specialized model rather than a general DCA timing engine.

### 20.10 Cost stress test

Required scenario runs:

- 0 bps
- 10 bps
- 25 bps
- 50 bps

The edge must not disappear under trivial friction assumptions.

---

## 21. Kill criteria

Do not purchase expensive institutional datasets or proceed to production if the evidence shows one or more of the following without a credible, pre-specified explanation:

- net EPI <= 0 versus Fixed DCA
- no statistically robust positive timing advantage
- Simple Dip Rule matches or beats the ML system
- edge is dominated by one year or narrow sector
- WAIT opportunity cost consumes the dip gains
- probability models are materially miscalibrated
- strong inner validation but major outer-OOS collapse
- edge disappears under modest transaction-cost stress
- edge materially depends on low-quality Tier C data

Failure means:

> the hypothesis is not validated in its current form.

It does not justify adding hundreds of features or unrestricted model complexity to rescue the backtest.

---

## 22. Leakage and overfitting blacklist

The following are prohibited in V1:

- full-history normalization or z-scores
- current index membership mechanically projected into the past without audit
- revised macro values used before their historical publication/revision time
- restated fundamentals projected backward as if originally known
- future analyst estimates/revisions
- future earnings dates not yet announced at the prediction timestamp
- any future 5D/20D/60D price aggregate used as a feature
- target-derived features
- outer OOS data used for feature/model selection
- lockbox data used during research iteration
- cross-sectional statistics calculated from future/current universe membership
- keeping a feature solely because it improved the final test
- direct ticker identity
- unrestricted AutoML
- deep neural networks in V1

---

## 23. Research ledger and experiment governance

Every experiment must record:

- hypothesis
- experiment ID
- data snapshot/version
- feature schema version
- model family/configuration
- training cutoff
- validation protocol
- parameter/search space
- reason for the experiment
- result
- decision

The number of model families and hyperparameter ranges is deliberately constrained to reduce research overfitting.

Outer OOS results may be inspected during development only according to the predefined walk-forward research protocol. The final lockbox remains untouched until design freeze.

---

## 24. Reproducibility and lineage

Every run must be reproducible using at minimum:

- `run_id`
- `data_snapshot_hash`
- `feature_schema_version`
- `model_config_hash`
- `code_version`
- `random_seed`
- `training_cutoff`

Every feature should support lineage back to:

- source observations
- provider
- timestamps
- transforms
- universe membership used in cross-sectional calculations

Feature snapshots are immutable.

---

## 25. Storage and processing architecture

V1 should avoid unnecessary infrastructure.

Reference stack:

- Parquet for columnar persisted datasets
- DuckDB for local analytical queries
- Python for processing/modeling/backtesting

Logical data layers:

1. `RAW`
2. `CANONICAL`
3. `POINT_IN_TIME`
4. `FEATURE_STORE`
5. `TARGET_STORE`
6. `TRAINING_SETS`
7. `PREDICTIONS`
8. `BACKTEST_RESULTS`
9. `REPORTS`

Feature and target stores must be logically and preferably physically separate.

---

## 26. Reference repository architecture

```text
quant-dca-engine/
|
|-- configs/
|-- data/
|   |-- raw/
|   |-- canonical/
|   |-- point_in_time/
|   |-- features/
|   `-- targets/
|
|-- src/
|   |-- providers/
|   |-- universe/
|   |-- calendars/
|   |-- point_in_time/
|   |-- features/
|   |-- regimes/
|   |-- models/
|   |-- calibration/
|   |-- policy/
|   |-- backtest/
|   |-- metrics/
|   `-- reporting/
|
|-- tests/
|-- experiments/
|-- reports/
`-- docs/
```

Research notebooks may be used for exploration and visualization, but production/business logic must not live only in notebooks.

---

## 27. Required automated tests

The implementation is not considered trustworthy without automated tests covering at minimum:

1. `feature.available_at <= prediction_timestamp`
2. target windows begin strictly after the prediction/execution reference point
3. rolling features never access future observations
4. cross-sectional percentiles use only the historical eligible universe
5. macro vintage selection is correct
6. earnings/fundamental availability timestamps are respected
7. corporate-action adjustment is consistent
8. ex-dividend movement is not falsely counted as a timing dip
9. US and EU exchange calendars/holidays are handled correctly
10. FX conversion is deterministic and point-in-time
11. purging removes target-overlap leakage
12. embargo logic behaves as configured
13. next-open execution never uses future signal data
14. identical input/configuration reproduces identical output
15. feature and target pipelines remain separated
16. low-quality/invalid raw observations enter quarantine rather than silently propagating
17. scheduled-event features use only event dates announced/known by the prediction timestamp
18. sector-inapplicable fundamental fields remain structurally missing and are not economically nonsensical imputations
19. delayed-entry economic cost correctly accounts for foregone distributions across ex-dividend dates

Any feature with:

`max(feature.available_at) > prediction_timestamp`

must cause a **hard failure**, not a warning.

---

## 28. Reference prediction output

Example schema:

```text
Ticker: AMD
AsOf: 2026-09-10 EOD
BaseCurrency: HUF

REGIME
Interpretable state: CORRECTION
P(Stress): 0.31
P(Recovery): 0.17
Unsupervised state: 3

5D
P(positive return): 0.54
Expected return: +0.8%
P(>=1.5% better executable entry): 0.68
Expected executable entry improvement: 2.1%
Entry Q25/Q50/Q75: ...

20D
P(positive return): 0.64
Expected return: +3.6%
P(>=3.0% better executable entry): 0.51
Entry Q25/Q50/Q75: ...

60D
P(positive return): 0.70
Expected return: +7.2%

LOCAL TIMING VALUE
...

HUF TIMING VALUE
...

NetWaitEV: +0.94%

ACTION
WAIT

Confidence: 73/100
NextEvaluation: next EOD
InitialMaxWait: 5 trading days
HardMaxWait: 20 trading days
```

Every prediction must include model/version/run provenance in machine-readable form.

---

## 29. Work-phase research deliverables

Before Codex production implementation, the research phase should produce at minimum:

1. audited data-source inventory and quality-tier map
2. historical universe reconstruction report
3. canonical point-in-time schema
4. feature dictionary with formula, source and availability rule
5. target dictionary with executable-price definitions
6. regime-model comparison for 3–8 unsupervised states
7. baseline vs challenger model comparison by target
8. probability-calibration report
9. quarterly nested expanding walk-forward results for 2015–2023
10. benchmark comparison: Fixed DCA, Random, Simple Dip, Trend/Dip, Buy Now, Oracle
11. regime/sector/region/year robustness analysis
12. cost-stress analysis
13. data-quality sensitivity analysis
14. frozen V1 configuration before lockbox
15. single final lockbox report for 2024-01-01 through 2026-09-10
16. explicit `PASS`, `FAIL`, or `NARROW_EDGE` recommendation

`NARROW_EDGE` means the system appears useful only in a clearly defined subset such as a sector or regime and must not be represented as a general DCA engine.

---

## 30. Transition rule to Codex implementation

Codex receives a production implementation mandate only after the research outputs identify a frozen architecture/configuration worth implementing.

The handoff must contain:

- this approved design specification
- validated data-provider choices
- frozen canonical schemas
- final feature dictionary
- final target dictionary
- selected champion models and calibration methods
- selected regime configuration
- frozen DCA policy thresholds
- benchmark definitions
- success/kill criteria
- research results and lockbox conclusion

Codex should not be asked to invent the investment methodology during implementation.

---

## 31. Deferred V2+ scope

Explicitly deferred until V1 demonstrates credible edge:

- intraday data
- short-horizon active trading signals
- position sizing optimization
- stock selection + timing optimization in the same decision layer
- multi-month DCA cash carry-over
- direct ticker embeddings/identity
- deep learning / LSTM / Transformer models
- unrestricted AutoML
- options/derivatives
- expensive institutional data subscriptions
- reinforcement learning

---

## 32. Final V1 architecture

```text
USA + EUROPE POINT-IN-TIME DATA
              |
              v
      QUALITY / PIT LAYER
              |
              v
        FEATURE ENGINE
        ~80-95 features
              |
              v
         REGIME ENGINE
   interpretable + HMM/GMM
              |
     +--------+--------+
     |        |        |
     v        v        v
 Direction   Return   Better-entry
 models      models      models
     |        |        |
     v        v        v
 calibration quantiles uncertainty
     +--------+--------+
              |
              v
        DCA POLICY ENGINE
              |
              v
     BUY_NOW / WAIT / NO_EDGE
              |
              v
       HUF EXECUTION MODEL
              |
              v
            BACKTEST
              |
              v
 Fixed / Random / Dip / Heuristic /
      Buy Now / Oracle benchmarks
              |
              v
 NESTED WALK-FORWARD DEVELOPMENT
           2015-2023
              |
              v
       FREEZE CONFIGURATION
              |
              v
        FINAL LOCKBOX
   2024-01-01 -> 2026-09-10
              |
              v
      PASS / FAIL / NARROW_EDGE
```

---

## 33. Design-freeze decisions

The following are considered approved V1 design decisions unless changed during user review:

- final objective: DCA entry optimization using direction + expected-return submodels
- horizons: 5D / 20D / 60D
- better-entry thresholds: 1.5% at 5D, 3.0% at 20D
- markets: USA + European Union
- history starts in 2010
- daily/EOD architecture only
- controlled 80–95 feature design
- technical + market + macro + fundamental inputs from V1
- rolling and cross-sectional normalization
- separate interpretable and unsupervised regime models
- unsupervised regime search over 3–8 states
- hybrid champion/challenger model stack
- no deep learning in V1
- point-in-time timestamps and as-of joins
- local-currency and HUF-base-currency evaluation
- nested expanding walk-forward validation
- quarterly outer blocks and quarterly model refits
- 2015–2023 development OOS
- 2024-01-01 to 2026-09-10 untouched lockbox
- mandatory purge/embargo
- baseline DCA fallback for `NO_EDGE`
- maximum 20 trading-day wait
- initial WAIT threshold 60% + 0.50% NetWaitEV
- extension threshold 65% + 0.75% incremental NetWaitEV
- predefined success and kill criteria
- provider abstraction layer
- free/low-cost prototype data strategy
- survivorship-free end-state with audited proxy allowed in V1
- Parquet + DuckDB reference storage
- hard automated leakage tests
- immutable/reproducible experiment tracking

---

## 34. Spec self-review result

The specification has been checked for:

- unresolved placeholders: **none**
- contradictory target horizons: **none**
- contradiction between EOD signals and execution timing: **resolved via next-session-open reference execution**
- use of non-executable intraday lows in better-entry targets: **explicitly prohibited**
- USA-only macro assumptions in joint USA/EU modeling: **resolved with region-aware macro architecture**
- look-ahead risk from macro revisions/restatements: **explicit PIT/vintage rule**
- survivorship bias: **explicit end-state and proxy-audit requirement**
- overlap leakage across 5D/20D/60D labels: **purge/embargo required**
- human overfitting to final holdout: **separate 2024–2026 lockbox**
- over-complex ensemble risk: **champion/challenger and incremental-OOS requirement**
- confusion between timing and stock selection: **V1 timing-only mandate**
- ambiguity in `NO_EDGE`: **resolved as baseline-DCA fallback**
- ambiguity in multi-month cash carry: **explicitly excluded from V1**
- ambiguity in final implementation stack: **reference architecture provided without unnecessarily locking vendor-specific libraries**
- monthly baseline timestamp ambiguity: **resolved using previous-session EOD -> first eligible monthly open**
- purge/embargo ambiguity: **resolved with label-maturity rule plus 5-session embargo**
- EU monetary-policy ambiguity: **resolved with monetary-jurisdiction mapping**
- FX look-ahead at execution: **resolved with timestamp-aligned quote / same-day FX-open fallback**
- NetWaitEV estimator ambiguity: **constrained to two predeclared research candidates, frozen before lockbox; WAIT disabled if neither validates**
- ex-dividend false-entry edge: **resolved through economic acquisition cost / foregone-distribution adjustment**
- financial-sector metric applicability: **resolved through sector applicability masks and financial-specific fundamentals**
- scheduled-event look-ahead: **resolved through point-in-time announced-event calendars**
- cross-sectional pseudo-replication: **resolved through monthly cohort aggregation and block bootstrap**

No architectural blocker remains for the next phase after user approval of this written specification.
