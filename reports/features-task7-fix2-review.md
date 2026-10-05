# Task 7 R2 repair — independent review

Scope: base `a5f3beb` to head `024634e`, the supplied R2 diff, exact Task 7 brief, R1 review, and implementation correction appendix. Review was limited to the R2 change: pre-2010 listing inception and action-coverage start reference metadata. No network, market data, subagents, git mutation, or suite rerun was used. The reported **59 focused / 556 full passing tests** are implementation evidence, not independently rerun results. Task 8 was not reviewed or changed.

**R2: ADDRESSED. Spec: PASS. Quality: PASS.**

## R2 verification

`_bounded_snapshot` now exempts only `Security.active_from` and `ActionCoverage.start_session` from the 2010 lower bound. Those fields describe interval starts, so an in-window listing version or coverage audit may truthfully refer to history before the development observation window. The values are preserved rather than rewritten, and the existing target eligibility/coverage checks still require the referenced intervals to cover the requested 2023 horizon.

The exception does not weaken the other boundary controls. Every `*_at` field still passes through `_bounded`, so publication, revision, availability, announcement, payable, market-session, and verification timestamps remain within 2010–2023 and at or before `label_as_of`. Market observations and action/discontinuity dates retain the 2010 lower bound. All date fields, including the two reference fields, retain the 2023 upper bound and declared knowledge-cutoff check. Exact canonical materialized ingress and preflight-before-FX behavior are unchanged.

The added regressions cover a bounded 1980 listing inception, a pre-2010 coverage start, and late-2023 short-horizon survival when 60D is censored. They also retain explicit rejection coverage for pre-2010 listing publication, price observation, and action observation. Existing unrelated-record tests continue to exercise post-2023 listing and coverage bounds. The implementation appendix accurately describes the bounded exception and reported verification.

No blocking spec or code-quality finding was identified within this fix scope. Task 7 may close at this gate. **Task 8 must remain untouched; pause for the user before any Task 8 work.**
