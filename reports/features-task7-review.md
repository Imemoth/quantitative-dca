# Task 7 independent spec and quality review

Review scope: base `999ee58` to head `2729520`, supplied Task 7 diff, exact Task 7 brief, `reports/features-plan-preflight.md`, and implementation report. Foundation inspection was limited to the economic ledger contract used by the new builder. No network, real data, financial experiment, repository mutation, or suite rerun was performed. The implementation report's 40 focused / 537 full passing tests are reported evidence, not independently rerun results.

**Spec: FAIL. Quality: FAIL.** One blocking boundary finding remains.

## R1 — High: history iterables are consumed before development-window censorship

Location: `src/quant_dca/targets/builder.py:308`, preceding the `_prepare` boundary check at lines 159–163 and its invocation at lines 312–317.

`build_targets` eagerly converts every supplied price, action, listing, and discontinuity-evidence iterable to a tuple before checking whether any requested horizon is inside the authorized development window. Consequently a lazy provider/history iterator is traversed even when O0 itself is in 2024 and all three horizons must be censored. This violates the frozen requirement that an out-of-bound horizon must not access future market history merely to censor it, and contradicts the implementation report's preflight-before-history claim. Lack of a direct network call inside the builder does not prevent iteration from retrieving records.

Focused synthetic probe: call the builder with a 2023-12-29 21:00 UTC XNYS signal, a 2023-12-31 label cutoff, and a price iterable whose `__iter__` raises `AssertionError('history accessed before out-of-bound horizon censorship')`. Actual result: that assertion is raised at input materialization. Expected result: development-window-censored horizons with no history or FX access. This probe uses no market data and makes no network request.

Required repair: determine authorized horizon windows before consuming evidence. When no horizon is admissible, return censored outcomes without traversing history. For mixed admissible/censored horizons, make the bounded input contract concrete so unrestricted lazy history cannot retrieve 2024 observations while materializing inputs for the shorter labels. Add sentinel coverage for the all-censored case and the mixed-window ingress boundary. Do not resolve this by merely documenting that callers should avoid lazy iterables while retaining an unrestricted consumption path.

## Reviewed contracts that otherwise pass

- EOD validation and calendar numbering implement O0 baseline, O5/O20/O60 exits, and O0..O4/O0..O19 wait windows (`builder.py:263–279,295–307`). Only raw validated opens feed the economic ledger; lows and adjusted prices are not fills (`178–195,239–241,266`).
- Local/HUF costs, split-equivalent units, foregone distributions, payable-date FX, strict-positive directions, and inclusive 1.5%/3% classifications align with the approved contract (`250–280` and the narrowly inspected Foundation economic ledger). The fixture tests cover dividend neutrality, splits, payable FX, and literal thresholds.
- Explicit coverage, listing evidence, selected raw validation, and unsupported terminal-action censorship are present (`165–247`). Missing eligible opens are not skipped. No synthetic terminal payout is introduced.
- Per-horizon revision and dependency maturity is retained; complete short horizons survive a censored 60D horizon, and aggregate maturity is `None` when incomplete (`242–247,280–283,328–338`).
- Targets reside in a separate package. The feature-import architecture test rejects direct and relative target imports. No feature-storage write path was added. Snapshot integration remains Task 10.

No additional research requirement is introduced by this review. Repair R1 within Task 7, then independently review the bounded change. **Task 8 must not start, including after a subsequent PASS; execution must pause for the user after Task 7.**
