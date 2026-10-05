# Task 7 R1 repair — independent review

Scope: base `3e86ce7` to head `9db34ca`, the supplied repair diff (read once), original review, implementation correction appendix, and narrowly relevant canonical/listing contracts. No network, subagents, git mutation, or suite rerun. The reported **53 focused / 550 full passing tests** are implementation evidence, not independently rerun results. One local synthetic probe was used below.

**Spec: FAIL. Quality: FAIL. R1: addressed; a newly introduced blocking regression remains.**

## R1 verification

Calendar admissibility now precedes snapshot handling. All-censored windows bypass all history access and FX resolution. For an admissible or mixed window, all five inputs must be exact materialized built-in containers (with the supported single coverage record normalized); a lazy input is rejected before any input collection is iterated. Exact canonical record checks and snapshot timestamp/date checks precede dependency selection and FX. The existing bounded November fixture retains 5D/20D labels while censoring 60D, with independent short maturity. The new sentinel cases directly cover the original eager-ingress failure. This resolves the original R1 mechanism.

## R2 — High: snapshot bounds incorrectly censor valid pre-2010 listing inception dates

Location: `src/quant_dca/targets/builder.py:280–295` (`active_from` included in the generic bounded observation-date set).

The repair treats a listing's inception date as a development observation/vintage date. A canonical listing version published and available within the authorized window may legitimately describe a security listed before 2010. `Security.active_from` is the historical listing start, and the existing target eligibility contract only requires it to precede the baseline. The development history boundary does not require securities to have begun trading in 2010 or later. Requiring every `active_from >= 2010-01-01` silently removes otherwise eligible older securities from every target horizon, introducing a systematic universe restriction.

Synthetic probe: take the existing January 2023 fixture, preserve every bar, action, coverage, provenance timestamp and FX quote, and change only `listing_history[0].active_from` from `2010-01-01` to `1980-12-12` using `dataclasses.replace`. The unchanged fixture returns `[0.0, 0.0, 0.0]`; the historical inception version returns `DEVELOPMENT_DEPENDENCY_UNAVAILABLE` for all three horizons. No pre-2010 observation or publication was added or fetched. This input was admissible under the pre-repair listing logic.

Required repair: distinguish listing interval metadata from market observation and publication/vintage clocks. Preserve truthful historical inception dates for in-window listing versions while retaining the bounded materialized ingress and future-history protections. Do not fabricate a 2010 inception date as a workaround. Add a regression for a pre-2010 inception with authorized publication/availability and valid 2023 target evidence, including short-horizon survival when 60D is censored. Check other interval metadata according to its meaning rather than applying a universal date-field rule.

No other blocking finding was identified within this repair scope. Task 7 needs this bounded correction and independent re-review. **Task 8 must not begin; pause for the user after Task 7, including after a subsequent PASS.**
