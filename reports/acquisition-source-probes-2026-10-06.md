# Bounded acquisition evidence — 2026-10-06

Four completed deliberate requests; no redirects, paid account, new registration,
or private API key used. The earlier interrupted Alpha Vantage attempt has no
retained response: its dispatch/completion count is unknown, not assumed zero.
Completed receipts and hashes are in `observed-source-inventory.json`. Raw bytes
remain outside Git. These probes establish access/shape, not admission or coverage.

| Priority / endpoint | Pre-request bounds | Observed response | Decision |
|---|---|---|---|
| 1. Alpha Vantage `/query`, LISTING_STATUS, active | as-of 2014-07-10 | HTTP 200; 2 bytes; no listing rows | UNAVAILABLE in this demo response; not proof of no active listings |
| 1. Same function, delisted | as-of 2014-07-10 | HTTP 200; 430 rows; 424 Stock, 6 ETF; 0 duplicate symbols; 2 missing names; 0 inverted IPO/delist intervals | RAW_ONLY; no stable security ID, common-equity qualification, historical knowledge, primary-listing or terminal consideration proof |
| 2. EODHD `/api/splits/AAPL.US` | from 2010-01-01 to 2020-12-31 | HTTP 200; 2 dated ratios | RAW_ONLY; no publication/revision clock or complete terminal-action ledger |
| 2. EODHD `/api/div/AAPL.US` | from 2010-01-01 to 2020-12-31 | HTTP 200; 34 records with ex/declaration/record/payment dates, values and currency | RAW_ONLY; date fields are not publication timestamps; historical correction/adjustment basis unproven |

All returned financial/event dates checked against 2023-12-31; IPO inception
dates before 2010 are descriptive listing metadata, not warm-up observations.
Alpha records have dates no later than the requested as-of date. EODHD ex/split
dates must also lie inside their request interval. No provider tier assigned.

## Remaining priorities considered in order

3. FX: retained one-day MNB USD/HUF and EUR/HUF response plus the publication-policy
audit already demonstrate the unsolved date-only/correction issue. More quotes do
not resolve it; no larger download. See `mnb-publication-policy-audit.md`.
4. Fundamentals: two bounded SEC quarter indexes and one original accession exist.
No normalized PIT fact panel/security linkage; no EU archive panel. Current
companyfacts, latest normalized fundamentals and unbounded submissions not fetched.
5. Macro: reuse nine bounded FRED captures; inspect numeric/grain/vintage structure
locally. No new downloads merely to enlarge an unadmitted basket. Date-level
vintages still need release-time, units, geography and series-rights decisions.
6. Context: no dated US/EU sector/index mapping and broad-market/VIX admitted
history. Current component endpoints cannot close historical eligibility.
7. Events: no retained ex-ante schedule versions. Realized dates are insufficient;
do not synthesize known-at dates or silently drop the family.

## Official interface evidence versus observed evidence

- Alpha Vantage [documentation](https://www.alphavantage.co/documentation/):
  LISTING_STATUS supports date/state, US stocks/ETFs; no EU claim. Documentation
  examined 2026-10-06; actual access evidence is the bounded probe above. The
  [support page](https://www.alphavantage.co/support/) states a general free limit
  of 25 requests/day; listing-specific entitlement and reuse rights are unverified.
- EODHD [actions documentation](https://eodhd.com/financial-apis/api-splits-dividends):
  inclusive from/to, dividends filtered by ex-date; current and unadjusted fields
  cannot alone prove historical economic basis. Demo access observed only for the
  named instrument; exact quotas and redistribution rights remain unverified.
- EODHD [exchange list documentation](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours):
  active/delisted filters but no documented historical as-of bound in the inspected
  parameter list. Do not request it as a development universe. This is an endpoint
  limitation, not proof that no historical product exists.

These documents can contain modern examples. The incidental exposure is recorded
in `source-search-access-incident-2026-10-06.md`; no pristine claim is made.
Free demonstration access proves neither unrestricted use nor complete history.
