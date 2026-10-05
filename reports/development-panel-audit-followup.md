# Development-panel evidence audit follow-up — 2026-09-16

## Scope and decision

This audit is limited to retained raw evidence whose requested observation and
vintage/publication bounds end no later than `2023-12-31`. It applies the
approved 2010–2014 warm-up and 2015–2023 development protocol. It does not
inspect credentials, use a FRED secret, run a model, access the retrospective
holdout, assign provider quality tiers, or treat synthetic fixture data as
financial evidence.

**Decision: the remaining research panel is not ready.** The repository proves
bounded raw access for a narrow macro set, one active US demo equity, two SEC
quarter indexes plus one filing, and one date-level MNB FX sample. It still has
no usable EU equity panel, continuous execution-safe FX series, historical
active/delisted universe, corporate-action ledger, or pan-US/EU fundamentals
panel. None of the observed raw artifacts has passed canonical admission.

## Independent retained-artifact checks

All 13 pre-existing raw files in the five audit directories below were read and
rehashed. Every SHA-256 matched its content-addressed filename. The subsequent
MNB artifact was separately bounded and validated before persistence:

- `data/raw/fred_development_audit/`: four US monthly macro payloads.
- `data/raw/fred_eu_development_audit/`: one euro-area monthly aggregate.
- `data/raw/fred_yield_development_audit/`: four bounded yield chunks.
- `data/raw/eodhd_development_audit/`: one AAPL daily-history payload.
- `data/raw/sec_index_audit/`: two quarter indexes and one original filing.
- `data/raw/mnb_development_audit/`: one WSDL-verified, single-date EUR/USD
  official HUF reference-rate response.

The following is actual retained evidence, not provider documentation:

| Domain/source | Actual bounded raw evidence | Grain and observed coverage | PIT/publication evidence actually present | Admission and material limit |
|---|---|---|---|---|
| US macro — FRED/ALFRED | CPIAUCSL 830 rows; CPILFESL 822; UNRATE 296; FEDFUNDS 169 | Each has 167 monthly periods, `2010-01-01..2023-11-01` | Date-level `realtime_start`/`realtime_end`; multiple records per period in several series | `RAW_ONLY`; no intraday release time, complete revision proof, full basket, or rights conclusion |
| US yields — FRED/ALFRED | DGS10 chunks 1,826 + 3,653 rows; DGS2 chunks 1,826 + 3,651 | 3,650 distinct observation dates per series; 3,501 dates with a nonmissing value; nonmissing span `2010-01-04..2023-12-28` | Date-level realtime intervals; later chunks legitimately repeat older observation dates under later realtime windows | `RAW_ONLY`; overlapping chunks need reviewed stitching and clipped boundaries are not genuine revision events |
| EU macro — FRED/ALFRED | One euro-area aggregate, 362 rows | 167 monthly periods, `2010-01-01..2023-11-01` | Date-level realtime intervals | `RAW_ONLY`; one aggregate does not establish pan-EU geography, historical membership, definitions, or intraday release timing |
| US OHLCV — EODHD demo | AAPL.US, 3,522 rows | One active symbol, daily `2010-01-04..2023-12-29`; fields are OHLC, adjusted close, and volume | No historical correction ledger or publication timestamp | `RAW_ONLY`; no broad universe, delisted names, action reconciliation, or original-volume proof |
| US filings — SEC archive | 2010 Q1 index: 300,561 filing rows; 2023 Q4 index: 251,348; one 2010 10-K raw filing | Two quarters and one document, not a security panel | Filing sample contains raw `ACCEPTANCE-DATETIME=20100104172243`; timezone and public-dissemination equivalence remain unverified | `RAW_ONLY`; no canonical parser, issuer/security history, amendments/restatements normalization, or continuous 2010–2023 coverage |
| FX — MNB | One validated SOAP response, SHA-256 `871e3a88215724f7ac347b2a77b5ebb98b9c8a2bccf84fb4694fbb70745048d2` | One day, `2023-12-29`: EUR/HUF 382.78 and USD/HUF 346.44; unit 1 | Date-only official daily quotation; no time, timezone, vintage, or correction ledger | `RAW_ONLY`; proves bounded free access only, not execution-time availability or continuous coverage |

The synthetic canonical and feature snapshots under `data/fixture_snapshots/`
were excluded. They demonstrate software behavior only.

## Required source-audit fields and panel gaps

`NULL` below means no quality tier is assigned. Candidate remedies are not
validated capabilities.

| Domain | Evidence status | Date coverage | US/EU and active/delisted coverage | Corporate actions | PIT/revisions/publication | Request bounds | Rate/cost/license | Admission / tier | Remaining analytical blocker |
|---|---|---|---|---|---|---|---|---|---|
| US macro | Observed raw | Four monthly series through 2023-11; two daily yields through 2023-12-28 | US only; equity status N/A | N/A | Date-level realtime intervals; intraday and completeness unresolved | Observation and realtime windows bounded before send; yields split below the observed 2,000-vintage-date limit | Authenticated access previously succeeded; rate and per-series reuse rights unverified; no purchase | `RAW_ONLY` / `NULL` | Availability policy, chunk stitching, full required basket, admission |
| EU macro | Observed raw | One monthly series through 2023-11 | Euro-area aggregate only | N/A | Date-level realtime intervals; definition/geography history and release time unresolved | Observation and realtime bounded before send | Same unresolved rights/rate position; no purchase | `RAW_ONLY` / `NULL` | Full EU monetary-jurisdiction coverage and semantics |
| US OHLCV | Observed raw sample | AAPL 2010-01-04..2023-12-29 | One active US demo name; no delisted coverage | Not reconciled | Current returned history; correction-state PIT and publication unverified | `from`/`to` bounded before send | Demo access only; limits and rights unverified; no purchase | `RAW_ONLY` / `NULL` | Broad survivorship-controlled panel, actions, liquidity semantics |
| EU OHLCV | Access failure only | None | SAP.XETRA returned 403 in prior bounded probe | Unverified | Unverified | Prior request bounded before send | Demo insufficient; paid product not tested | `UNAVAILABLE` / `NULL` | Entire EU price panel and historical eligibility |
| FX | Observed raw sample plus prior access failures | One MNB day, `2023-12-29`, EUR/HUF and USD/HUF; no series | MNB official HUF reference sample; EODHD EURHUF.FOREX previously returned 403 | N/A | Date-only quote observed; no intraday publication time, vintage/correction ledger, or executable/open semantics | MNB observation/quote date fixed to one pre-2024 day before send; redirects disabled and response bounds checked | MNB required no credential or purchase; rate limit and reuse rights unverified | `RAW_ONLY` / `NULL` | Continuous coverage and a rule proving availability at or before each security execution |
| US fundamentals | Observed raw samples | Two isolated quarters and one filing | US filing samples; no security-universe or delisted mapping | Not normalized | Raw acceptance field on one filing only; amendment/restatement behavior unverified | Immutable quarter/accession paths selected before send | Public access succeeded; rate/usage details unresolved; no purchase | `RAW_ONLY` / `NULL` | Canonical dated parser, security mapping, continuous panel |
| EU fundamentals | No raw evidence | None | No pan-EU issuer panel | N/A | No verified PIT/revision/publication ledger | No tested bounded contract | Unverified; no purchase | `UNAVAILABLE` / `NULL` | Entire domain missing |
| Corporate actions | No raw evidence | None | No US/EU event ledger or terminal economics | None observed | Announcement, correction, cancellation, ex/pay availability absent | No tested bounded contract | Unverified; no purchase | `UNAVAILABLE` / `NULL` | Return construction and delisting economics |
| Historical universe/delistings | No raw evidence | None | No active/delisted US/EU membership panel | Terminal events absent | No historical membership-known-at ledger | No tested bounded contract | Unverified; no purchase | `UNAVAILABLE` / `NULL` | Primary survivorship blocker |
| Sector/index context | No raw evidence | None | No historical classifications/components | N/A | No dated snapshot/rebalance-publication evidence | No tested bounded contract | Rights/entitlement unverified; no purchase | `UNAVAILABLE` / `NULL` | Selected context features unavailable |
| Scheduled event calendars | No raw dataset | BLS 2023 documentation only | No complete US/EU macro/issuer calendar | N/A | No preserved ex-ante schedule versions | No tested data contract | Unverified; no purchase | `UNAVAILABLE` / `NULL` | Calendar features cannot be reconstructed from realized dates |

## Free official FX validation attempt

The official MNB documentation describes `GetExchangeRates(startDate,
endDate, currencyNames)` and output with a date-only `Day` plus currency unit
and rate. Unlike the unbounded `GetCurrentExchangeRates`, this method exposes a
request-time historical interval. Documentation alone was not treated as
usability evidence.

The initial HTTPS POST to the documentation URL returned HTTP 404. No data was
obtained or persisted, and there was no blind retry. A static metadata request
to the official `?WSDL` resource then returned HTTP 200 (`4,143` bytes;
SHA-256 `2ba41f51d4ebd8f804427362a5b41b22bc39810eec5e9ab5f484ebe99657a2fe`).
The WSDL established all three details needed to correct the transport without
guessing:

- service address: `http://www.mnb.hu/arfolyamok.asmx`
- binding: `CustomBinding_MNBArfolyamServiceSoap`
- SOAP action:
  `http://www.mnb.hu/webservices/MNBArfolyamServiceSoap/GetExchangeRates`

One tightly bounded call was then made to that exact service contract:

- Endpoint: `http://www.mnb.hu/arfolyamok.asmx`
- Method: SOAP `GetExchangeRates`
- Pre-transmission bound: `startDate=2023-12-29`,
  `endDate=2023-12-29`, `currencyNames=EUR,USD`
- Credentials: none
- Redirects: disabled
- Actual outcome: HTTP 200; 479 response bytes
- Validated contents: one `Day`, exactly `2023-12-29`; EUR unit 1 rate
  `382,78`; USD unit 1 rate `346,44`; no unexpected date or currency
- Raw response:
  `data/raw/mnb_development_audit/871e3a88215724f7ac347b2a77b5ebb98b9c8a2bccf84fb4694fbb70745048d2.raw`
- Manifest:
  `data/raw/mnb_development_audit/871e3a88215724f7ac347b2a77b5ebb98b9c8a2bccf84fb4694fbb70745048d2.manifest.json`
- Raw SHA-256:
  `871e3a88215724f7ac347b2a77b5ebb98b9c8a2bccf84fb4694fbb70745048d2`
- No `GetInfo`, current-rate, unbounded-date, 2024+ observation, credential,
  alternate provider, or broader-range call was made

This is direct bounded access evidence for date-level official HUF reference
quotations. The documentation states that dates have no time or time zone and
exposes no vintage/revision history. The response therefore does not prove
availability before a US/EU security open, historical correction state,
continuous 2010–2023 coverage, executable pricing, or spreads.

Official references inspected:

- [MNB current and historic exchange-rate web-service documentation](https://www.mnb.hu/letoltes/documentation-on-the-mnb-s-web-service-on-current-and-historic-exchange-rates.pdf)
- [MNB GetExchangeRates service page](https://www.mnb.hu/arfolyamok.asmx?op=GetExchangeRates)

## Concrete next validation step

Before a broader MNB data request, establish from official material the
historical publication-time policy, correction/revision behavior, quote units
and direction, and whether older daily values can be changed without a retained
version ledger. If those semantics support a conservative prior-known rule,
the next data probe should be one fixed, short pre-2024 interval with EUR and
USD, redirects disabled, response date/currency checks before persistence, and
a content-addressed manifest. Do not call `GetInfo` or
`GetCurrentExchangeRates`, because they expose a modern unbounded interval.

The source remains `RAW_ONLY` with quality tier `NULL`. A prior-day MNB
reference rate is only an **unverified proxy candidate** until publication and
correction facts support it and the real-panel leakage gate accepts the rule; a
same-day later fixing cannot price an earlier open.

## Unverified candidates, not remedies

- **Free proxy candidate:** MNB prior-known date-level HUF reference rates,
  conditional on successful bounded access and verified historical publication
  and correction policy. This does not supply executable spreads or intraday
  open quotes.
- **Alternative official candidate:** ECB bounded observation-period reference
  rates. Its vintage/correction and publication-time restriction has not been
  established, so no development data request is authorized by this audit.
- **Paid candidate:** a timestamped historical FX feed with bounded retrieval,
  revision/correction lineage, and rights for the required US/EU/HUF pairs.
  Product coverage, entitlement, cost, and suitability are unverified; no
  purchase is justified by the current evidence.
- **Panel candidates:** professional survivorship-controlled equities,
  corporate actions, PIT fundamentals, and historical classifications remain
  unverified paid options only. They do not become required purchases until a
  bounded free/public path and the exact prototype evidence need are separately
  assessed.

## Gate and risk assessment

The missing historical universe/delistings, corporate actions, EU prices, and
execution-safe FX are **critical, high-confidence blockers**: using the current
artifacts for cross-sectional 2015–2023 research would create survivorship,
return, regional-selection, and currency-timing bias. The narrow macro and SEC
evidence is useful for provider-access engineering but cannot offset those
gaps. Development research remains blocked pending actual bounded raw evidence,
source-specific availability rules, a quality/admission report, canonical
quarantine/admission, and the required real-panel leakage gate.
