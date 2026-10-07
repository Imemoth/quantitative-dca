# Provider decisions — 2026-10-07

Authoritative table: [provider-decision-matrix.csv](provider-decision-matrix.csv).
All requested fields, evidence IDs and bounded-query qualifications are in that
single table. This page is its decision index, not an alternative source of status.
Claims and caveats: [provider-evidence.json](provider-evidence.json). No quality
tier assigned; ACCEPTABLE/PREFERRED mean next candidate to investigate, not admitted.
Prior matrix is preserved in history/acquisition-provider-decision-matrix.md.

| ID | Domain | Provider | Decision | Feasibility classification |
|---|---|---|---|---|
| U1 | historical_universe | Alpha Vantage LISTING_STATUS | REJECT | METHODOLOGY_BLOCKED_BY_DATA |
| U2 | historical_universe;corporate_actions | EODHD delisted/symbol lists | REJECT | METHODOLOGY_BLOCKED_BY_DATA |
| U3 | historical_universe;terminal_economics;fundamentals | Norgate US Platinum | REJECT | UNSUPPORTED_FOR_PIT |
| U4 | historical_universe;terminal_economics;corporate_actions | Sharadar actions plus master | PAID_FALLBACK | METHODOLOGY_BLOCKED_BY_DATA |
| U5 | historical_universe;terminal_economics;ohlcv;corporate_actions | CRSP US Stock database | PAID_FALLBACK | METHODOLOGY_BLOCKED_BY_DATA |
| U6 | historical_universe;terminal_economics;fundamentals | EU issuer/OAM/exchange archives | UNRESOLVED | METHODOLOGY_BLOCKED_BY_DATA |
| U7 | historical_universe;terminal_economics;fundamentals | LSEG PIT/company data and corporate actions enquiry | PAID_FALLBACK | METHODOLOGY_BLOCKED_BY_DATA |
| O1 | ohlcv;corporate_actions | EODHD bounded EOD/split/dividend endpoints | ACCEPTABLE | METHODOLOGY_BLOCKED_BY_DATA |
| O2 | ohlcv | Stooq attempted bounded CSV | REJECT | METHODOLOGY_BLOCKED_BY_DATA |
| O3 | ohlcv;corporate_actions | Sharadar stocks/actions | PAID_FALLBACK | METHODOLOGY_BLOCKED_BY_DATA |
| F1 | fundamentals | SEC original accession archives | PREFERRED | METHODOLOGY_BLOCKED_BY_DATA |
| F2 | fundamentals | Sharadar AR dimensions | PAID_FALLBACK | METHODOLOGY_BLOCKED_BY_DATA |
| F3 | fundamentals | SimFin legacy bulk Python loader | REJECT | UNSUPPORTED_FOR_PIT |
| M1 | macro | FRED/ALFRED API vintage route | UNRESOLVED | METHODOLOGY_BLOCKED_BY_DATA |
| M2 | macro | Eurostat latest API | REJECT | UNSUPPORTED_FOR_PIT |
| M3 | macro | Original BLS/Fed/Treasury/ECB/Eurostat release archives | PREFERRED | METHODOLOGY_BLOCKED_BY_DATA |
| X1 | fx | MNB historical reference quotes | PROXY_ONLY | PROXY_POSSIBLE_WITH_LIMITATION |
| X2 | fx | ECB reference-rate cross conversion | PROXY_ONLY | PROXY_POSSIBLE_WITH_LIMITATION |
| C1 | market_context | Index-owner historical files and classification histories | UNRESOLVED | METHODOLOGY_BLOCKED_BY_DATA |
| E1 | event_calendars | Official historical release schedules and issuer notices | UNRESOLVED | METHODOLOGY_BLOCKED_BY_DATA |

No route presently closes the required US+EU stack. See the final report for
domain-level blockers and paid-provider-escalation.md for purchase conditions.
NOT_ESTABLISHED means no supporting evidence, not an inferred negative capability.
UNSUPPORTED_FOR_PIT is scoped to the named route, never every product of a vendor.
No current/latest financial data endpoint was queried; no new raw capture.
