# MNB official exchange-rate publication-policy audit — 2026-09-17

## Scope and decision

This is a documentation-only audit of the Magyar Nemzeti Bank (MNB) official
exchange-rate service. It addresses publication timing, correction/revision
behavior, quote unit and direction, reuse, and rate limits. It applies the
development-data boundary in
`docs/evaluation-protocol-amendment-2026-09-11.md` and does not assign a
provider quality tier.

No MNB rate-data endpoint was called. In particular, this audit did not call
`GetInfo`, `GetCurrentExchangeRates`, `GetDateInterval`, or
`GetExchangeRates`; it did not send an unbounded-history, current-rate, or
2024+ observation query to the web service. The network retrievals were public
MNB web pages and two static MNB web-service documentation PDFs. One search
result unexpectedly expanded MNB's live “latest official exchange rates” web
page and exposed a numeric rate table dated `2026-09-16`. Those current
observations were not requested as research data, persisted, transcribed into
this report, compared, or used in any finding. This is nevertheless 2024+
market-data exposure and is recorded here rather than described as if it had
not occurred. The previously retained one-day `2023-12-29` response described in
`reports/development-panel-audit-followup.md` remains the only observed MNB
rate-data sample considered here.

**Decision: MNB is not yet established as an execution-time-safe historical FX
source.** The official material supports a conservative prior-MNB-business-day
proxy candidate, but does not prove the exact publication time, the historical
continuity of today's timing policy throughout 2010–2023, or any correction and
vintage semantics. No broader data request is justified until those gaps are
resolved or the research design explicitly accepts the conservative proxy and
its limitations.

## Verified facts

| Topic | Fact supported by official primary material | Evidentiary limit |
|---|---|---|
| Current fixing schedule | MNB's current English policy page says official rates are fixed on each weekday except national public holidays, at 11:00, and remain valid until publication of the next day's rates. It lists publication via the MNB website and Reuters/Bloomberg pages. | Fixing at 11:00 is not a statement that website/API publication occurs at exactly 11:00. The page gives no publication timestamp, latency bound, timezone label, effective-date timestamp, or machine-readable publication event. |
| Current calculation description | The current English page describes an EUR/HUF fixing based on 10 active domestic banks after dropping two high and two low quotes. The current Hungarian page instead describes eight institutions after dropping one high and one low quote, and says the fixing occurs at 11:00. | The language versions conflict on a material methodology detail. Neither page exposes a visible effective date or version history. They establish today's displayed policy only and should not be projected backward without dated evidence. |
| Web-service dates | The MNB web-service documentation says date values are ISO 8601 dates without time or timezone. `GetExchangeRates` accepts caller-supplied `startDate`, `endDate`, and comma-separated currency names and returns one `Day` element per quoted date. | The response schema cannot prove when a day's rate first became available or whether it was later replaced. |
| Units and direction | The service documentation defines `unit` per currency. Its examples show `unit="1"` for EUR and USD, and `unit="100"` for currencies such as JPY. The current Hungarian rate table labels the numeric column “Forintban kifejezett érték” (value expressed in forints). Together these establish the interpretation: a row is HUF per the stated number of foreign-currency units. Thus an EUR row with `unit=1` is HUF per EUR; it is not EUR per HUF. | Unit must be read from every row rather than assumed to be one for every currency. The audit only needs EUR and USD, for which both the 2015 documentation examples and the retained 2023 sample use unit 1. |
| Historical API documentation | The Hungarian PDF is an MNB-hosted document whose embedded creation/modification timestamp is 2015-09-16 and whose HTTP `Last-Modified` header was also 2015-09-16 when retrieved on 2026-09-17. Its examples include a last available date of 2015-07-23 and a bounded `GetExchangeRates` response for 2014-12-31. The English MNB PDF has an embedded 2016-11-21 timestamp and a 2016-11-29 HTTP `Last-Modified` header. | These dated documents establish the date-only bounded query contract by 2015, not the 11:00 publication policy, actual daily publication latency, correction behavior, or the contract before 2015. Server headers and embedded metadata are provenance signals, not a guarantee that the files were never replaced while retaining their dates. |
| Reproduction | The current English fixing/publication page says reproduction of official exchange rates is permitted and disclaims responsibility for reproduced information. The Hungarian version says republication for print and electronic press is unrestricted and similarly disclaims responsibility. | This supports republication of the rates at the level stated on that page. It does not expressly grant every form of API extraction, bulk redistribution, sublicensing, or commercial dataset reuse. |
| General website terms | MNB's current general terms say MNB owns the website copyright, unauthorized use of all or part is unlawful, MNB may change website content without notice, and only printed formally released publications are considered official and reliable. | The exchange-rate page's specific reproduction permission and the general website terms are not reconciled for a stored research dataset or downstream redistribution. A rights conclusion broader than internal research use requires clarification from MNB or counsel. |
| Authentication, price, and limits | The published service documentation describes the query methods without an API key, account, tariff, quota, retry rule, or request-rate limit. The earlier one-day audit call succeeded without credentials or purchase. | Absence of a published quota is not evidence of unlimited use. No official throughput, concurrency, acceptable-use, or bulk-download allowance was found. No load or limit test was performed. |

## Publication-time finding

The currently displayed MNB policy proves a daily **fixing time** of 11:00 and
says the resulting rates are published on the internet and wire services. It
does not state an exact publication time or maximum delay after the fixing.
Because the API returns dates without time or timezone, a downloaded historical
row cannot itself show whether it was available before any Budapest, EU, or US
execution timestamp.

The 11:00 statement is also not proven as a continuous rule for the full
2010–2023 research period. The dated 2015/2016 service manuals document the API
shape but contain no fixing or publication clock. No dated MNB policy document
was found that establishes an unchanged publication rule for 2010–2014, or
even an exact post-fixing release deadline for 2015–2023. The differing current
Hungarian and English calculation descriptions reinforce the need for a dated
policy record; they do not by themselves show when the methodology changed.

Therefore a same-date MNB rate must not be treated as known at a same-date
security open. The present evidence does not justify converting the current
11:00 fixing statement into an assumed historical 11:00 availability timestamp.

## Correction and revision finding

Neither the current policy pages nor the web-service manual states whether a
published daily official rate can be corrected, how a correction is announced,
whether the API overwrites the prior value, or whether earlier vintages remain
available. The `GetExchangeRates` schema has a quote date, currency, unit, and
value, but no publication timestamp, retrieval-as-of field, revision number,
correction flag, or vintage endpoint. MNB's general reservation that website
content may change without notice is not a rate-specific correction policy.

The defensible status is therefore **unknown correction behavior with no
documented vintage ledger**. Historical values must not be labelled unrevised,
immutable, or point-in-time merely because the API returns them today. A
content-addressed capture can prove what this project received at retrieval
time, but it cannot reconstruct the value that was visible on the historical
date.

## Narrow proxy candidate

A **prior MNB business-day official HUF reference rate**, carried forward until
the next MNB publication day, is a narrowly supportable proxy candidate for
research that executes on a later day. This uses the current policy's statement
that a published rate remains valid until the next day's rates are published
and avoids relying on an unproved same-day publication clock.

The candidate is still provisional:

- require at least one full MNB business-day lag relative to the security
  execution date; do not infer availability from the API's date alone;
- preserve the returned `unit` and normalize explicitly to HUF per one foreign
  currency unit before inversion or cross-rate construction;
- treat it as a non-executable official reference rate with no bid/ask spread;
- record retrieval time and raw hash, while marking historical correction
  state as unknown;
- do not claim the current fixing methodology or exact clock held throughout
  2010–2023;
- keep provider quality tier `NULL` and admission `RAW_ONLY` until the broader
  evidence and leakage gates are satisfied.

No new observation sample was intentionally fetched because another sample
cannot resolve publication timing or correction lineage. If the project's
internal source-admission decision admits the prior-day proxy under the
existing protocol and leakage gates, the next observation request may be one
fixed short pre-2024 interval for EUR and USD only, with both date bounds and
currencies fixed before transmission, redirects disabled, and response dates,
currencies, and units checked before content-addressed persistence. That
request must still exclude `GetInfo`, `GetCurrentExchangeRates`, unbounded
history, and 2024+ observations.

## Remaining gaps and required primary evidence

1. A dated MNB notice, archived MNB policy, formal rule, or direct written MNB
   clarification that states the actual publication time or maximum publication
   delay and its effective dates during 2010–2023.
2. A rate-specific MNB correction policy stating whether official daily values
   may change, how corrections are disclosed, and whether prior versions can be
   retrieved.
3. An MNB statement covering automated-service quotas, fair-use/rate limits,
   and permission for the project's intended storage and redistribution.
4. Reconciliation of the current Hungarian and English methodology pages,
   including effective dates for the eight-bank/one-trim and
   ten-bank/two-trim descriptions.

Until those items are obtained, the source cannot support same-day execution
semantics, historical as-of reconstruction, or a provider quality assignment.

## Official sources inspected

- MNB, [Fixing and publication of the official exchange rates](https://www.mnb.hu/en/statistics/statistical-data-and-information/statistical-time-series/exchange-rates/fixing-and-publication-of-the-official-exchange-rates) (current English page, retrieved 2026-09-17).
- MNB, [A hivatalos devizaárfolyamok megállapítása és publikálása](https://mnb.hu/statisztika/statisztikai-adatok-informaciok/adatok-idosorok/arfolyamok-lekerdezese/a-hivatalos-devizaarfolyamok-megallapitasa-es-publikalasa) (current Hungarian page, retrieved 2026-09-17).
- MNB, [Documentation on the MNB's web service on current and historic exchange rates](https://www.mnb.hu/letoltes/documentation-on-the-mnb-s-web-service-on-current-and-historic-exchange-rates.pdf) (English PDF; embedded document date 2016-11-21).
- MNB, [Aktuális és a régebbi árfolyamok webszolgáltatásának dokumentációja](https://www.mnb.hu/letoltes/aktualis-es-a-regebbi-arfolyamok-webszolgaltatasanak-dokumentacioja-1.pdf) (Hungarian PDF; embedded document date 2015-09-16).
- MNB, [Terms of use](https://www.mnb.hu/en/the-central-bank/about-the-mnb/terms-of-use) (current page, retrieved 2026-09-17).
