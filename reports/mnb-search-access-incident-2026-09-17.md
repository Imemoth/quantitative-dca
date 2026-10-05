# MNB documentation-search access incident — 2026-09-17

Status: disclosed; excluded observations were exposed in search-tool results, not admitted to development data. This is a breach of the user's 2024+ access restriction. Software implementation continues; the MNB audit performs no further network requests in this work stage.

## What happened

The separate publication-policy audit used broad official-domain web searches. The search tool expanded a live latest-rates HTML result and displayed a table dated 2026-09-16. A later search batch repeated that exposure. No SOAP rate method was called, but that distinction does not make the search-result exposure compliant.

First batch:

```
site:mnb.hu "Az árfolyamok megállapítása 11 órakor történik"
site:mnb.hu "11 órakor" "hivatalos devizaárfolyam"
site:mnb.hu/letoltes "devizaárfolyamok" "11 órakor"
site:mnb.hu "Reproduction of the official exchange rates is permitted"
```

Repeated-exposure batch:

```
site:mnb.hu "hivatalos devizaárfolyam" "módosít"
site:mnb.hu "hivatalos devizaárfolyam" "javít"
site:mnb.hu "hivatalos devizaárfolyam" "helyesbít"
site:mnb.hu "hivatalos devizaárfolyam" "visszamenőleg"
```

Returned live URLs were `https://www.mnb.hu/arfolyamok` and `https://www.mnb.hu/arfolyamok?action=Search`. Individual results were not attributed to one specific query within each batch. No further retrieval was made to investigate this incident; the audit agent reported these facts from existing tool history.

## Impact and evidence boundary

- The numeric observations are not reproduced here, incorporated into repository data, or used in feature/model/policy/source selection. Their exposure remains in the tool history; no claim is made that they were never retained anywhere.
- No financial experiment, model fit, OOS evaluation, retrospective-holdout evaluation, or configuration freeze occurred.
- The exposed date is outside the designated 2024-01-01 through 2026-09-11 retrospective-holdout window, but is still prohibited 2024+ data. This does not excuse the access. The historical holdout remains explicitly non-pristine; there is no pristine-unaccessed certification.
- The true forward lockbox has not begun. It can only consist of new observations after a future final configuration freeze; no already observed value can be included.
- The audit's unit/direction wording used a live table's column label, not its numeric values. Exclude that live-page evidence from source admission: any required unit/direction conclusion must stand on the static service manual and permitted historical sample independently.
- MNB remains RAW_ONLY, quality tier NULL. The prior-day proxy is an unadmitted candidate, not a validated substitution. No provider or feature choice is justified by the exposed observations.

## Corrections and prevention

The original audit commit `3452995` incorrectly described the work as containing no 2024+ observation exposure. Correction `047d593` fixes the access record without erasing the original git history. This report adds the repeated-exposure details. The earlier project incident reports remain intact.

For remaining provider-documentation audit work, broad web searches that can expand live market pages are disallowed. Use known exact static documentation resources whose provenance is assessed before retrieval; a provider domain restriction alone is insufficient. If safe discovery cannot be established before sending the request, mark the evidence gap unresolved. Do not retrieve the live MNB rate pages or their query variants.

This documentation control does not prohibit a separately validated provider adapter from making an explicitly bounded historical SOAP request. Such requests still require all observation/vintage bounds before transmission, no redirects to unbounded resources, and the existing admission/leakage gates. No new human-approval requirement is introduced. Software tests and implementation proceed without accessing the excluded data.
