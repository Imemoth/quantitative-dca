# Independent feasibility data / methodology review

Review date: 2026-10-07. Reviewer: independent `feasibility_data_closure` agent.
Reviewed recovered scope: `2717926687378696e8b02a9ed7e3f4d4a4d8e1fe` through
`52e56a4b5671995db251efeeadfa49774faca384`. Recovery documentation in `c976a35`
does not constitute provider evidence. This is a new review because no completed
prior verdict artifact was located; it does not certify an unavailable old review.

## Initial verdict

**CHANGES_REQUIRED — one Important finding (D1), zero Critical findings.**
The substantive final decision **BLOCKED_BY_DATA is supported**. This is an
assessment of the evidence and its stated limitations, not data admission,
empirical provider validation, a real-panel leakage PASS or permission for models.

## Scope and checks

Inspected provider-evidence.json, the 20-row provider matrix, all 94 feature-slot
coverage rows, 23 macro-topic rows, provider_feasibility_v1.json, historical
universe, terminal economics, fundamental PIT, macro, FX, minimum-panel, paid
escalation and final reports. Compared frozen specification section 11 and checked
the recovered diff for frozen features/regimes/dictionaries and source-code drift.
The frozen feature coverage name set is exact, all 94 names are unique, and all
model_research_valid flags remain false. Provider CSV widths are consistent.
No change to frozen features/regimes/dictionaries or src appears in the reviewed
range. No financial observation request or model run was made by this review.

## Critical findings

None.

## Important findings

**D1 — unresolved FRED licensing applicability is encoded as provider rejection.**
Locations: provider-decision-matrix.csv row M1 (`recommended_decision=REJECT`),
provider_feasibility_v1.json macro free_commercial fallback (`current use rights
blocked`), and macro-pit-feasibility.md rights-blocker wording.

Fresh narrow verification of https://fred.stlouisfed.org/legal/ on 2026-10-07
confirms restrictions concerning software/ML and API storage, alongside permitted
research/app uses and separate owner rights. Relevant sections are summarized
Intended and Permissible Use, summarized Prohibited Use, and API Prohibitions
(k)/(l). These justify withholding admission. Their application to this particular
workflow remains a human licensing decision, not a categorical legal verdict.
Current terms also do not establish terms governing earlier captures.

Required correction: explicitly use `LICENSING_REQUIRES_HUMAN_REVIEW`, set M1's
recommendation to `UNRESOLVED`, and align current fallback/report language. Keep
the factual account of the restrictive wording and keep RAW_ONLY / non-admission,
incomplete macro/PIT clocks and the overall BLOCKED_BY_DATA decision. Do not
delete evidence or imply either permission or a universal prohibition.

## Minor findings

None requiring phase-expanding work. Documentation-level provider capability and
prices are not sample validation; the reports already disclose that limitation.

## Supported substantive conclusions

- US historical cohort/identity coverage is incomplete; listings alone do not
  establish terminal consideration or recovery.
- EU lacks a demonstrated identity-to-price-to-original-fundamental chain.
- Original filings are a construction route, not normalized admitted PIT facts.
- Delisting and terminal uncertainty cannot be silently removed. Importantly,
  the reports preserve the frozen allowance for an audited proxy universe and
  flagged unreliable terminal outcomes; they do not require perfect coverage.
- Sharadar is only a bounded US paid pilot candidate subject to rights/sample
  checks. CRSP/LSEG are scoped alternatives, not demonstrated solutions.
- The FX proposal remains a reference proxy requiring timing/revision review.
- No credible proof panel, admitted rows/securities, or research-ready gate exists.
- Purchasing nothing now is consistent with unresolved EU and terminal gaps.

## Declined to judge

Legal enforceability, entitlement or retroactive applicability; vendor completeness
without samples; numerical terminal missingness; actual real-panel PIT/leakage;
expected timing edge or investment returns. No opinion here promotes any source
to ADMITTED or assigns a quality tier. Existing documentation/search exposure
remains recorded; this targeted terms lookup contained no financial observations.

## D1 disposition and final verdict

Independent follow-up on 2026-10-07 inspected only the D1 correction in the
working tree: M1 CSV/Markdown recommendation, macro fallback, P22 caveat, macro
report and US/EU macro quality-map wording. The recommendation is now UNRESOLVED;
the applicability issue is explicitly LICENSING_REQUIRES_HUMAN_REVIEW. A targeted
metadata check confirmed RAW_ONLY remains, no quality tier is assigned, and the
fallback keeps the human-review condition. Restrictive wording and separate
original-owner rights are retained without a categorical legal conclusion.

**D1 RESOLVED. Final verdict: PASS for the blocked feasibility assessment.**
Open Critical findings: 0. Open Important findings: 0. No additional provider
research, financial observations or model runs were performed for this follow-up.
This does not issue legal clearance or change BLOCKED_BY_DATA; all declined-to-judge
items above remain outside the PASS scope. Full-suite verification is recorded
separately by the implementation lead rather than inferred from this review.

## Exact scope of any eventual PASS

After D1 is independently rechecked, PASS can mean only that the **blocked
provider-feasibility assessment** is sufficiently consistent and cautious for
human review. It cannot mean data admission, research readiness or legal clearance.
