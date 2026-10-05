# Features/Targets/Regimes — final review fixes F1/F2/F3

Base: `02a61d8`. Scope: the single final-fix batch accepted in `reports/features-final-review.md`. Implementation complete; scoped independent re-review remains the controller's responsibility. This report does not mark the subsystem or research gates PASS and does not alter prior review history.

## Narrow corrections

**F1 — target names cannot enter either FoldImputer feature schema.** The feature-only name validator now also rejects precisely `return|direction` × `5|20|60` × `local|huf`. Existing wait-target prefix guards remain. Together these cover all 20 canonical dictionary targets in both numeric and categorical constructor paths. No feature module imports the target package, and legitimate trailing `return_{5,20,60,120,252}d_raw` columns continue to fit and impute normally.

**F2 — the universe hash must describe the producer's actual eligible cohort.** Before accepting a RelativeFeatureSnapshot or ValuationFeatureSnapshot, snapshot assembly compares its full `eligible_security_ids` cohort with the eligible universe independently reconstructed from the supplied immutable historical UniverseEvidence at the feature EOD. Cardinality and identities must match. The check concerns the full eligible cohort, not the subset with finite values; eligible peers with missing observations remain valid missing peers.

The regression recomputes genuine relative and valuation producers with eligible `{TEST, PEER}`, binds each complete output/evidence object to its own immutable source, and successfully assembles them with the corresponding two-member universe. It then keeps each genuine producer bundle unchanged and attempts to attach the legitimate one-member `{TEST}` universe/source: both producer paths reject the mismatch. Separate positive coverage keeps the full two-member cohort while providing only TEST's finite observations; ranks remain the valid singleton 0.5 and the snapshot is admitted.

**F3 — peer valuation closes must be current for the peer's calendar.** Valuation cross sections now require the peer quote to match `previous_eligible_eod(peer.exchange, target_cutoff)` and the historical eligible listing's exchange. A missing current peer close is missing, rather than a stale value carried from an earlier session. In the reported fixture, current A P/E10 and stale B P/E5 now leave A's rank at 0.5, not 1.0. Valid different-calendar prior closes remain usable: the positive fixture admits Frankfurt's Dec23 close at the Paris Dec24 2021 trading-day cutoff while Frankfurt is closed.

The production changes are limited to three existing files: `features/normalize.py`, `features/snapshots.py`, and `features/valuation.py`. No horizons, target arithmetic, thresholds, normalization method, regime fit policy, source admission rules or other methodology was redesigned.

## TDD evidence

Runtime: `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python`. Its launcher was absent at resumption; restored the venv using the declared `.[test]` dependencies. No repeated baseline suite was needed.

RED command:

```text
/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m pytest tests/features/test_normalize.py tests/features/test_fundamentals.py tests/features/test_feature_integration.py -q
```

Observed **27 failed, 99 passed in 26.52s** before production changes:

- 24 failures for 12 return/direction target names accepted in two constructor paths. The eight wait-target names were already rejected; the new parameterized regression covers all 20 targets in both paths and checks the tested name set against the committed target dictionary.
- Two failures for genuine content-bound two-member relative/valuation outputs admitted with a different one-member universe.
- One literal rank failure: stale peer produced 1.0 instead of the expected singleton 0.5.

Positive controls already passed in RED: legitimate trailing raw returns, finite-value subsets of a matching eligible cohort, and the valid Frankfurt-holiday prior close. No fixture/setup error was used as RED evidence.

GREEN: the same focused command passed **126 tests in 25.39s** after the three narrow guards. Self-review confirmed that the target-name pattern does not catch raw trailing returns, cohort checking does not require a price for every eligible peer, and quote freshness uses the peer calendar rather than the target calendar.

## Scope and limitations

All data in the regressions are synthetic, inside 2010–2023. No provider/raw data or existing fixture-snapshot directories were read or staged. Provider data/network requests **0**; financial/OOS research runs **0**. No subagents were used. Parent status, ledger, manifest, review and checkpoint drafts are excluded from the commit.

The fixes establish software invariants only. Provider vintage truth, quality evidence, real-panel admission and financial usefulness remain upstream/later research questions. Final verification counts and exact commands follow below after completion of the required runs.

## Final verification and handoff

The workspace resumption removed the first in-progress verification process, its temporary logs and the Python launcher. Code and the already observed RED/focused GREEN results remained intact. The declared runtime was restored again; only the unfinished required checks were rerun. No result is claimed for the interrupted run.

Completed commands with `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python`:

| Check | Result |
|---|---|
| `-m pytest tests/features tests/targets tests/regimes -v` | **410 passed in 37.04s** |
| `-m pytest -q` | **804 passed in 37.62s**, clean output (758 previous + 46 added regression/positive-control cases) |
| `-m compileall -q src tests` | Exit 0 |
| `git diff --check` | Exit 0 |
| Scoped `git diff --cached --check` | Exit 0 |

Files in this scoped change: `src/quant_dca/features/{normalize,snapshots,valuation}.py`, `tests/features/{test_normalize,test_fundamentals,test_feature_integration}.py`, and this report. All three accepted findings are implemented and verified. No remaining software blocker was identified in self-review; scoped independent final-fix review and the whole-subsystem decision remain with the controller.
