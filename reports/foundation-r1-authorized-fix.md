# Authorized Foundation F2/R1 residual repair

Date: 2026-09-16. Implementation base: `6fa1901`; controller-only authorization documentation commit `c13d070` preserved. Scope is the expressly authorized residual repair, not a gate waiver or methodology change.

## Causal dependency rule and implementation

Resolve every supplied security/action identity using the existing revision selector before deciding relevance. An identity is a label dependency if **any supplied version** places its ex-date in `(baseline session, fill session]`. Retain only the selected revision of each such identity for dependency availability and `selected_action_versions`; apply its economics only if its selected ex-date is still in that interval. Thus a correction adding an event is applied once, and a correction removing it still supplies necessary maturity/provenance evidence. Distinct identities whose entire supplied history lies outside the interval are not dependencies.

The implementation adds a historical identity-relevance set after `_selected_actions`, then narrows the selected rows before the existing economic, maturity and provenance paths. No raw revision is discarded before identity resolution. Historical rows identify dependencies but never contribute split/dividend arithmetic. The existing full-version selection cutoff is unchanged; unrelated later identities do not contribute their timestamps to maturity. Raw-price/calendar validation, price and action revision ordering, payable cashflows, native/HUF conversion, FX availability and feature/target separation are untouched.

## TDD evidence

New tests were written and run before production changes. All fixtures added by this repair are synthetic, offline, and dated 2020–2023.

RED command:

```text
python -m pytest -q tests/foundation/test_fix_wave.py -k r1
6 failed, 22 deselected in 0.70s
```

All six failures were expected maturity assertion failures, not setup errors. For the three horizons, the original implementation returned `2023-10-04 00:00 UTC` instead of the window-only maturity below, despite equal total cost and cashflows. The three correction-window cases likewise returned that unrelated 2023 timestamp instead of the correction's `2020-01-14 22:00 UTC` availability.

| Horizon | Actual exchange fill session | Expected maturity (UTC) | Total HUF |
| --- | --- | --- | --- |
| 5 | 2020-01-09 | 2020-01-16 00:00 | 101 |
| 20 | 2020-01-31 | 2020-01-31 21:01 | 101 |
| 60 | 2020-03-30 | 2020-03-30 20:01 | 101 |

The full-history test supplies 16 quarterly dividend identities through 2023, in reverse order via an iterator; it checks equal economics/cashflows, literal maturity, identical single-identity provenance, and historical maturity eligibility at 2021-01-01, 2022-01-01 and 2023-01-01. Correction tests cover movement beyond the fill, movement into the window, and movement onto the excluded baseline boundary, with duplicate selected rows and an unrelated later split. Existing correction-removal regressions remain unchanged.

GREEN covering command:

```text
python -m pytest -q tests/foundation/test_fix_wave.py tests/corporate_actions/test_economics.py
48 passed in 1.24s
```

Full suite, run once after implementation:

```text
python -m pytest -q
394 passed in 2.03s
```

`git diff --check` also passed. No network market request, secret inspection, actual raw-dataset read, or holdout experiment was performed. The full suite retains its pre-existing synthetic boundary guards; this repair introduces no post-2023 fixture.

## Changed files

- `src/quant_dca/corporate_actions/economics.py`: documented and enforced identity-level causal dependency scope.
- `tests/foundation/test_fix_wave.py`: six parameterized regression cases.
- `reports/foundation-r1-authorized-fix.md`: this report.

## Self-review and limitations

- Selecting before relevance and retaining historical identity relevance prevents the unsafe latest-ex-date prefilter. Economics still consume one selected revision per identity; provenance retains removal corrections.
- Both maturity and provenance use the same narrowed selected rows. New horizon assertions would fail if unrelated identities were reattached; correction assertions would fail if removed events lost correction knowledge or superseded rows contributed economics.
- The rule is deliberately conservative within an identity: once any supplied version intersects the window, its selected revision remains a dependency. It does not attempt field-level equivalence of successive corrections.
- The caller must supply the relevant revision history: a latest-only snapshot cannot reveal an omitted historical in-window version. This producer does not invent missing history or guarantee final truth against future revisions. Ambiguous supplied revisions still fail closed before relevance, including unrelated identities; that pre-existing validation contract is preserved.
- Historical usability is verified against the producer's `label_matures_at <= training_cutoff` contract. No training implementation or dataset was added or exercised.
- Independent review and the controller's Foundation gate decision remain required. Real-data readiness and all accepted F1/F3/F4/F5/F6 boundaries are outside this residual change.
