# Lockbox documentation-example exposure incident

Recorded: 2026-09-11. Status: **REQUIRES USER DISCLOSURE / REVIEW BEFORE FURTHER RESEARCH**.

## What happened

During Task 0 official provider-documentation research, the web search/open/find route returned financial response examples adjacent to interface documentation. A `web.find` request for `adjusted` on the official EODHD EOD API guide returned example OHLCV rows dated **January 2024**. These fall inside the prohibited lockbox. No values, security identities, or more precise dates are reproduced here.

Document: https://eodhd.com/financial-apis/api-for-historical-data-and-volumes

Separately, an official EODHD historical-components documentation search result contained a lockbox-period membership end-date example. That example is not reproduced.

Document: https://eodhd.com/financial-apis-blog/reworked-sp-500-historical-constituents

## Method and factual scope

- Tools used: `functions.exec` orchestrating `tools.web__run`; search queries about provider interfaces, then `open`, then `find` for adjustment semantics. The search/find tool automatically included adjacent examples rather than limiting output to requested schema text.
- Within this provider-audit subtask, this agent made no financial-data API request and accessed no bulk data download, user dataset, lockbox file, live companyfacts payload, or live historical-constituent endpoint. Whole-session request history is recorded in `reports/preflight-verification.md`: the parent made a bounded Stooq request for 2023-01-03 through 2023-01-06, receiving HTTP 404 and no data.
- The displayed response examples entered the agent context. Their authenticity as actual market observations was not independently verified; their lockbox dates mean this cannot be dismissed as a clean audit.
- No examples were copied into data/configuration, and no model, feature selection, performance analysis, or tuning was performed.
- The parent agent was notified of both exposures, including the more serious OHLCV example. The parent then ordered all external research stopped. This report and partial provider matrix were completed from existing evidence only.

## Integrity statement and required controls

**An untouched lockbox cannot be certified for this research session.** Calling the material documentation, not downloading a dataset, or resetting a context does not restore integrity. User disclosure/review is required before research continues; the response must not describe the lockbox as untouched.

Prospective controls, subject to that review: obtain sanitized interface/schema documentation which excludes response examples and market observations before model access; block current/unbounded data endpoints; enforce both observation and vintage/filing cutoffs at the network boundary; separately verify redirects and server-side bounds; record requests and response-date audit results without reproducing prohibited values. Filtering a response after it has already entered model context is too late. Search-result snippets can also include examples, so ordinary metadata-only query intent is insufficient.

No claim is made that these proposed controls have been implemented or validated.
