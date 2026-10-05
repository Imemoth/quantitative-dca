# Provider validation continuation — 2026-09-12

Controlling protocol: docs/evaluation-protocol-amendment-2026-09-11.md. This report supplements the earlier partial documentation audit; it does not silently promote candidate sources to validated providers.

## Observed access evidence

- Stooq daily download: explicit 2023-01-03..2023-01-06 request returned HTTP404 and provider-branded error HTML. No historical data obtained. This is an endpoint/access failure, not evidence about Stooq historical coverage.
- FRED/ALFRED observations: request supplied both observation and realtime/vintage ranges 2010-01-01..2023-12-31; HTTP400 explicitly requires api_key. Environment FRED_API_KEY was absent (only presence checked, no secrets printed). Public documentation capability is not working access. No macro observations obtained.
- EODHD demo EOD: explicit 2023-01-03..2023-01-06 request returned HTTP200 and four dated US equity records with date/open/high/low/close/adjusted_close/volume. This supports only bounded access and schema for the sampled symbol/dates. Corporate-action reconciliation, revisions, publication latency, original-unit volume, licensed usage and wider active/delisted coverage remain unverified. No quality tier assigned.
- Additional bounded probe raw bytes/manifests, where obtained, live in data/raw/provider_probes/. These are provider-access evidence, not an admitted research panel.

## Capability gaps and remedies

| Required capability | Current gap and bias | Narrow permissible path | Paid remedy candidate / need for prototype |
|---|---|---|---|
| US macro vintages | No API credentials; revised latest values would leak revisions | Obtain free FRED key, validate bounded observation+vintage requests and release timestamps | Institutional macro archive not currently justified; free key route first |
| US/EU OHLCV and actions | Only narrow demo sample; full coverage/actions/revision evidence missing | Validate bounded historical source with separate action ledger and local eligibility evidence | EODHD historical entitlement is a candidate, not a verified solution; no purchase. Full universe data needed for actual broad OOS |
| Historical universe/delistings | No admitted listing/eligibility/terminal-economic ledger; survivorship bias | Dated exchange/issuer records and an explicitly audited proxy universe if coverage can be evidenced | Historical constituent/delisting source may improve coverage; terminal returns must be verified separately |
| EU PIT fundamentals | No pan-EU dated filing panel; publication/restatement risk | Original timestamped issuer/registry reports with compact sector applicability; genuine gaps remain missing | Professional PIT source may help; broader cost is not justified before evidence. A defensible EU proxy must still satisfy historical availability |
| Historical schedules | Current reconstructed dates cannot prove advance knowledge | Announced-date archive, otherwise feature structurally missing | Paid calendar is useful only if it retains schedule vintages; current calendar alone is insufficient |
| FX at execution | Close/fixing after security open would leak | Timestamped prior-known quote or documented same-day FX open with separate proxy flag | Historical FX feed candidate only after timestamp/history audit |

No paid subscription, trial or purchase was initiated. Missing observations are not represented as Tier C data. No fitting or model/feature/policy research occurred during these probes. Implementation proceeds independently of these unresolved ingestion qualifications.

Additional EODHD demo probe results: SAP.XETRA and EURHUF.FOREX both HTTP403. No access-control retry/bypass. These establish that this demo access cannot supply those EU/FX samples; they do not establish that the paid product lacks the data. Raw error bodies and hashed manifests retained.

User subsequently supplied a FRED key; a bounded authenticated validation was initiated. The earlier missing-key result remains historical access evidence, not current credential status.

Authenticated FRED result: HTTP200, complete three-row CPIAUCSL sample for observation range 2023-01-01..2023-03-31 and realtime/vintage range 2023-01-01..2023-12-31. Raw JSON and hashed manifest persisted. Response contains observation date, value, realtime_start and realtime_end; it does not contain intraday publication timestamps. This sample verifies bounded access and the vintage-interval schema, not the correctness of selecting among multiple revisions (that requires separate fixtures and multi-vintage evidence).

Official alternate Stooq .pl bounded SAP.DE query also returned HTTP404. No market data acquired.
