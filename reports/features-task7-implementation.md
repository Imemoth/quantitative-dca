# Task 7 — isolated executable target builder

Status: implementation complete, independent review pending. Task 8 has not started.

Scope: `src/quant_dca/targets/`, `tests/targets/`, and this report only. No shared Foundation or feature code changes. This is software/fixture evidence, not financial research or provider admission.

## Contracts and rulings

- `best_executable_improvement` preserves the plan's pure scalar interface; 100 versus opens 101/98/99 produces exactly 0.02. The evidenced builder uses validated unadjusted canonical opens, never lows or adjusted feature prices.
- `TargetRow` exposes local/HUF 5/20/60 holding returns and strict-positive direction labels, plus local/HUF 5/20 executable minimum returns and better-entry booleans. Minimum return is `(minimum economic acquisition cost - baseline cost) / baseline cost`; lower is better. Classification uses costs directly at the inclusive 1.5%/3% thresholds.
- Numbering ruling, recorded by parent in `999ee58`: O0 is the first eligible open strictly after the EOD signal. Returns exit at O5/O20/O60, giving 5/20/60 holding intervals. Wait windows contain exactly the five/twenty future opens O0..O4/O0..O19, including the baseline. This resolves the abbreviated plan's unspecified endpoint without an implicit off-by-one choice. Including O0 means executable minimum return cannot exceed zero.
- Each `HorizonTarget` carries its own label maturity, censor reason, raw selected bars and supplied raw revisions, action revisions and selected actions, listing versions and selection, coverage, discontinuity evidence, and Foundation economic cashflow ledgers with complete FX quote provenance. The aggregate maturity is the maximum only when all horizons are available; otherwise it is `None`. Consumers must use per-horizon maturity for individual tasks and must never admit an incomplete aggregate as a complete multi-output row.
- Per-horizon censoring ruling: missing 60D evidence must not discard complete 5D/20D labels. A November 2023 fixture proves short labels survive while 60D is development-bound-censored. Separate narrow action-coverage audits preserve independent short maturity; a later broad coverage audit genuinely delays the labels that depend on it.

## Economics, evidence, and bounds

The builder reuses Foundation `economic_acquisition_cost` (including its corrected action-identity revision selection) for raw split-equivalent fills, foregone distributions, and payable-date FX. Native cashflows produce local values; the same ledger's HUF values produce investor-currency values. Endpoint total wealth includes distributions without reinvestment. Targets are gross of transaction costs, with no fitted cost assumption, model, policy, or parameter search.

Explicit complete action-history coverage is mandatory even for an empty action list. Coverage is an external audit assertion, never fabricated from absence. Supplied provenance/quality records are retained; this code makes no provider-tier assignment. Listing evidence is mandatory; terminal listing dates or unsupported terminal actions censor the affected horizons. Unsupported actions at the baseline open are also rejected before FX. Missing eligible opens are not skipped or filled from adjacent sessions. Signal-time universe eligibility remains the caller's separate Foundation responsibility.

All three horizons are preflighted before any FX resolution. A horizon that extends beyond 2023 is censored before inspecting its future market history or resolving FX. Required raw/action/listing publication, revision, availability, action observation, payable, coverage, and discontinuity clocks are bounded; unavailable label-time requirements censor instead of inventing mature labels. Requests for cashflow FX are bounded before calling the injected service; returned quotes are additionally checked using Foundation FX validation and must be known at or before their cashflow instant. No market-data/network request is performed by this builder. Calendar queries beyond 2023 are offline schedule metadata only.

Labels are truths of supplied bounded versions, not guarantees of final unrevised truth. Later evidence requires rebuilding and preserving the new maturity. All consumed raw/action/listing versions and explicit discontinuity evidence contribute to maturity, including corrections that move actions outside a short window. Large split discontinuities require explicit canonical validation evidence; they are not silently accepted because an action happens to be present.

## Verification

Declared dependencies were restored using `python -m pip install -e '.[test]'` because the runtime initially lacked pytest; no dependency declaration changed and no market data were downloaded.

TDD evidence:

1. Focused initial RED: `python -m pytest tests/targets/test_executable.py -q` failed collection because `quant_dca.targets` did not exist.
2. Initial implementation GREEN covered scalar fills, thresholds, dividend neutrality, split invariance, local/HUF differences, holiday calendars, missing opens, explicit action coverage, terminal censoring, development bounds before FX, revisions, and architecture separation. One fixture required an explicit original-publication clock to satisfy Foundation's deliberate unambiguous-revision contract.
3. Additional regression RED demonstrated an older raw version delivered late was omitted from maturity; GREEN now retains and includes every consumed raw version.
4. Additional regression RED demonstrated a terminal action at O0 was ignored; GREEN now censors it before FX resolution.
5. Final focused: `python -m pytest tests/targets -q` — **40 passed**.
6. Full repository: `python -m pytest -q` — **537 passed in 8.20s** (497 prior + 40 target tests).

The architecture test parses every feature module and rejects target imports, including relative `from ... import targets` forms. The implementation has no feature-package import and no feature-storage write path. Immutable target snapshot integration/dictionaries remain Task 10; existing Foundation storage separation tests remain passing.

Additional literal coverage includes 2% ex-dividend neutrality, split-then-dividend share units, payable FX changing HUF but not local return, revisions moving events outside a horizon, exact threshold and just-above-threshold values, 10:1 split validation evidence, intraday signal rejection, post-fill FX exclusion, malformed raw panel rejection, and 2015/2022/late-2023 boundaries.

## Limits and next gate

No real PIT panel has been admitted; no financial baseline/challenger, nested OOS, regime fitting, or holdout evaluation has run. Unsupported merger/spin-off/delisting payoffs remain censored, not approximated. Missing FX censors the dual-currency horizon. These fixtures establish software behavior only. Independent Task 7 review must complete, then execution pauses for the user before Task 8 as instructed.

## Independent review repair — round 1 (R1)

The independent review in `reports/features-task7-review.md` found that the original builder materialized input iterables before horizon censorship. That could execute a lazy provider even when every horizon extended beyond development history. The original report's preflight-before-history statement was therefore too broad; this repair makes it true for the enforced input contract.

The builder now determines all calendar horizon bounds before touching evidence. If every horizon is inadmissible, it returns the appropriate per-horizon censor reasons without iterating or type-inspecting any supplied history and without resolving FX. For mixed windows, histories must be already materialized exact built-in lists or tuples containing exact canonical frozen record types (coverage also accepts its existing single-record form). Arbitrary iterables and container subclasses are rejected before iteration, so unrestricted provider histories cannot fetch while being converted. `label_as_of` declares the knowledge ceiling and fixed 2010–2023 constants declare the observation/vintage envelope. Every record's date/timestamp content, including unrelated records, is checked against this envelope before dependency selection or FX. Out-of-envelope snapshots yield censored labels, not filtered partial acceptance. Valid bounded snapshots still preserve complete short labels when 60D is censored.

TDD: 13 new sentinel/bounds cases first failed against the original implementation (40 existing tests passed), including all-history zero-access, each lazy ingress in mixed windows, unrelated post-2023 bar/action/listing/coverage/discontinuity/publication records, and observations beyond the declared knowledge cutoff. After repair: **53 target tests passed**. One full suite run: **550 passed in 8.22s**. No Foundation changes, new dependencies, network access, financial research, or Task 8 work. Independent re-review pending.

## Independent review repair — round 2 (R2)

`reports/features-task7-fix-review.md` confirms R1 is addressed and identifies an overstrict lower bound: listing inception is historical reference metadata, not a market observation. The snapshot validator now permits a `Security.active_from` before 2010 when its publication/availability evidence is bounded. The closely related `ActionCoverage.start_session` is also an interval-reference start and may precede 2010; no pre-2010 action records are consequently consumed or admitted. Other observation dates and all publication, revision, availability, FX, and payable timestamps retain their existing bounds. Both metadata exceptions retain the 2023 upper bound and declared knowledge-cutoff check. No date is rewritten to manufacture a 2010 inception.

TDD: three new acceptance regressions failed before repair: a 1980 listing inception with 2023 knowledge, a pre-2010 coverage interval start, and a 1980 inception retaining late-2023 5D/20D labels when 60D is censored. Three additional rejection cases prove that pre-2010 listing publication, price observations, and action observations remain unavailable. Existing post-2023 snapshot and lazy-ingress protections remain passing. Final focused: **59 passed in 1.22s**. One full suite run: **556 passed in 8.43s**. Only target builder/tests/report changed; no network, financial research, shared Foundation change, or Task 8 work. Independent re-review pending.
