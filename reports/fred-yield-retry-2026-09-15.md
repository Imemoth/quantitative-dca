# Bounded FRED yield retry — 2026-09-15

This is source-access evidence only, not a model experiment or admitted data.

Two observation requests were made through `BoundedFREDTransport`, one for
`DGS10` and one for `DGS2`. Each request fixed both the observation interval and
the realtime/vintage interval to `2010-01-01..2023-12-31` before transmission.
The endpoint was the FRED series-observations endpoint; redirects were disabled.
No credential or credential-bearing URL is retained here.

Both requests returned HTTP 400. The transport raised `ValueError` with the
sanitized status. No observation payload or raw snapshot was persisted, and no
quality tier was assigned. This narrows the previously unspecified failure to
the HTTP/request stage; it does not establish the provider's underlying reason.

A subsequent equally bounded diagnostic request for DGS10 was started to
inspect only the sanitized error fields. The work session ended before its
result was retained, and its process was absent on resume. Its result is
unknown. Do not infer an invalid credential, a date-range limit, lack of vintage
coverage, or a rate limit from the 400 status alone.

The four previously acquired US macro series and all earlier audit evidence
remain unchanged and RAW_ONLY. No holdout evaluation or purchase occurred.

## Retained diagnostic on resume

A new, equally bounded DGS10 diagnostic returned HTTP400 with a decoded error:
the requested realtime period contains3444 vintage dates, exceeding the2000
vintage-date maximum for the requested file type. This is direct endpoint
evidence, not an inference from documentation or a credential failure.

The narrow follow-up is to split only the realtime interval into
`2010-01-01..2016-12-31` and `2017-01-01..2023-12-31`, while keeping observation
bounds at `2010-01-01..2023-12-31`. Each subrequest remains bounded before
transmission; no endpoint change or unrestricted-history fallback is used.
Response intervals can be clipped to these request windows: chunk boundaries
must not be mistaken for genuine publication or revision dates. Any successful
payload remains RAW_ONLY pending reviewed stitching and availability policy.

## Successful bounded chunks

All four chunks passed response completeness, echoed observation/realtime
bounds, and every row's date/vintage-bound checks before raw persistence.

| Series | Realtime interval | Rows | Raw SHA-256 |
|---|---|---:|---|
| DGS10 | 2010-01-01..2016-12-31 | 1826 | 9184a33dec0c5a61331ce32b7e04c229f07c45f8b0c8bd8be824d520593edfd3 |
| DGS10 | 2017-01-01..2023-12-31 | 3653 | 23c2b578847d88befd4e32ee5e8a288b207b48f502e9561bf79256b310f557f1 |
| DGS2 | 2010-01-01..2016-12-31 | 1826 | 94f9a64d997c0c650f8a32338038572abdb0d335194d7b5a683814b2ddf8e4d5 |
| DGS2 | 2017-01-01..2023-12-31 | 3651 | 9f75704502ea5c7d29654e9cd8eeb4088db19d4985eb8b2f4bd4b0c11dc12b29 |

Raw files and manifests are under `data/raw/fred_yield_development_audit/`,
partitioned by series and realtime request window. Each series has3650 distinct
observation dates across chunks, of which3501 have at least one nonmissing
value, spanning2010-01-04..2023-12-28. These are structural counts, not proof of
complete vintage coverage. The raw chunk totals5479/5477 overlap in observation
dates and must not be presented as unique market sessions. Missing-value row
counts are224/225 respectively, also including overlap.

The initial seven-year chunks end at observation date2016-12-29; the later
chunks end at2023-12-28 within the permitted vintage cutoff. No request was
extended into2024 to fill later observations.

Quality remains unassigned and admission remains RAW_ONLY. Intraday release
timing, revision completeness, chunk-boundary interpretation, rate limits and
per-series licensing remain unresolved. This data-volume limitation is handled
by smaller bounded requests; it does not justify a paid purchase. No provider
adapter implementation or model/feature/policy experiment was changed here.
