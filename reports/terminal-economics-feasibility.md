# Terminal economics feasibility

US and EU: **METHODOLOGY_BLOCKED_BY_DATA**. Relevant provider rows U3–U7;
source claims P03/P07/P09/P18/P28. No actual terminal event was admitted.

| Event | Required economic record | Current gap |
|---|---|---|
| Cash acquisition | security, amount, currency, effective/payment dates, known-at | No joined original notice and price/session reconciliation |
| Stock acquisition | predecessor/successor IDs, exchange ratio, fractional/cash terms | No observed successor mapping |
| Mixed/elective consideration | additive components versus election alternatives, election rules | Schema support is not tested holder economics |
| Bankruptcy/deregistration | recovery, cancellation, subsequent distributions and evidence cutoff | No recovery ledger; no automatic zero |
| Spin-off/liquidation | parent/child units, distributions, final residual claim | No complete observed chain |
| Halt or venue downgrade | eligible final tradable session and future eligibility | Last available bar does not prove an executable exit |

Acquisition schema detail makes Sharadar a bounded **US pilot candidate**, subject
to rights and original-notice reconciliation. CRSP has a relevant terminal schema,
but a database field does not establish every missing-case policy. Neither closes
EU. Norgate is not a full terminal-economics remedy for this contract.

No automatic sale at the last historical bar: that can use hindsight about the
final tradable session. No removal of failed securities, imputed zero recovery,
unrecorded cash/share election, or double-counted merger and dividend proceeds.

The frozen spec explicitly allows unreliable terminal observations to be flagged
and retained for survivorship sensitivity. This phase does not require impossible
perfect recovery coverage or silently rewrite that rule. It requires a known
event population, explicit uncertainty and reproducible sensitivity treatment.
We have neither a complete event population nor a bounded missing-terminal rate.

Cheapest credible remediation is original historical issuer/exchange/administrator
notices for a bounded cohort, with independent identity and session matching. A
licensed event export becomes worth considering only after a sample demonstrates
the missing economics and rights. A delisted-symbol list alone cannot resolve it.
