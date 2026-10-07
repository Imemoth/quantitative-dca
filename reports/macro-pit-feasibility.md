# Macro, credit and conditions feasibility

Full US and EU baskets: **METHODOLOGY_BLOCKED_BY_DATA**.
The explicit 23-row topic/jurisdiction inventory is
[macro-series-feasibility.csv](macro-series-feasibility.csv). It distinguishes
retained raw series from unverified candidates; listed candidate names are not
approved economic substitutions or validated API keys/series mappings.

Technical evidence: P02/P21. Usage constraint: P22. Latest-only EU limitation:
P23/P24. ALFRED date-vintage semantics were observed in prior captures, but exact
publication time and full revision completeness are not established. Chunk start
dates can clip vintage intervals; do not fabricate release dates from them.

The current FRED terms present a material **rights blocker for the proposed
software/model/archive workflow**. No new FRED data was fetched or model run.
Current wording does not establish which terms governed older captures; those
historical receipts remain preserved, unadmitted. No new redistribution of raw
FRED data is included in this checkpoint. A direct BLS/Fed/Treasury/ECB/Eurostat
route must independently establish rights and genuine original releases; merely
relabelling FRED data as its upstream source is not a remedy.

Observation date, source publication timestamp, provider availability and revision
time are separate clocks. For every admitted series, document all applicable
clocks, timezone and conservative availability rule, and test release-day boundary
snapshots. A next-day lag addresses time uncertainty only after a credible maximum
release lag is evidenced; it does not repair revised values.

USA gaps include the missing 3M tenor, credit/conditions/liquidity/activity inputs
and the economic distinction between a monthly effective-rate average and a policy
decision rate. EU adds geography composition, euro versus non-euro monetary
jurisdiction, an approved sovereign-curve basis and regional credit/conditions
proxies. Do not replace a conditions index with stress, IG OAS with a different
spread, or all local policy rates with the ECB rate without review.

No macro input became ADMITTED. Recession Core remains
HISTORICAL_DIAGNOSTIC_BLOCKED_BY_DATA_ADMISSION; its software is unchanged. Original
release reconstruction is the first remediation; a paid vintage archive is a later
scoped alternative, subject to a real sample and reuse/retention permission.
