# SEC archival access audit — 2026-09-14

The two quarter-index requests were made in the preceding 2026-09-13 work session. The individual filing sample was acquired on 2026-09-14. This audit continues the approved development work; it does not admit a fundamentals panel or execute a model experiment.

## Request-time historical restriction

Quarter-specific immutable-path candidates were selected before network transmission: `/Archives/edgar/full-index/2010/QTR1/master.idx` and `/Archives/edgar/full-index/2023/QTR4/master.idx`. All parsed filing-date rows were checked against the requested year and observed ranges fall within their respective quarters. Redirects were disabled. No modern submissions/companyfacts endpoint was requested.

| Archive | Status | Index rows | Observed filing dates |
|---|---:|---:|---|
| 2010 Q1 | 200 | 300561 | 2010-01-02 .. 2010-03-31 |
| 2023 Q4 | 200 | 251348 | 2023-10-02 .. 2023-12-29 |

The filing sample was chosen deterministically from the 2010 Q1 index: first 10-K with a 2010 accession year ordered by filing date and archive path. This is an access sample, not stock selection for the research universe. Before requesting, its index date was verified within 2010 Q1 and the path matched a 2010 accession; no current issuer page was used.

Sample source: https://www.sec.gov/Archives/edgar/data/12040/0000914317-10-000003.txt
HTTP 200; 1563244 raw bytes; SHA256 `4068f78e6bd5a3e9b6416fbb41be59b5338e25a5e951dc307fbc056042d92fa4`.
An actual raw `ACCEPTANCE-DATETIME` header exists: `20100104172243`. Its timezone and equivalence to public dissemination have NOT been verified, so it is NOT assigned directly to canonical available_at.

## Admission and coverage limits

- Quality tier remains unassigned; these are RAW_ONLY provider access artifacts.
- An index row is a filing, not a distinct common equity or eligible historical security. Forms, funds, amendments and other entities can occur; the row count is not a universe size.
- Two quarter samples do not establish complete 2010–2023 coverage or active/delisted security coverage.
- Original accession retrieval works for the sampled document. XBRL/HTML facts, units, context, restatements, amendments and security mappings are not yet normalized.
- SECProvider remains an explicit IntegrationUnavailable placeholder in the reviewed provider layer. This external access audit does not silently promote it to a working canonical adapter.
- No corporate-action or terminal-return coverage is established. No pan-EU coverage is inferred.
- Rate limits, usage rights and complete free-access conditions were not validated by these successful requests. No paid data purchase occurred.
- No 2024+ data were requested or evaluated; the prior documentation incident remains recorded.

## Next admissible step

Implement a bounded quarter-index/original-accession adapter with RED/GREEN tests, then verify publication/diffusion semantics and normalize original/amended facts separately. This can be pursued without buying a professional dataset. Until then the fundamentals requirement remains unmet for an actual research panel.
