# Recession Risk Core — source admission

Status: **HISTORICAL_DIAGNOSTIC_BLOCKED_BY_DATA_ADMISSION**.
No actual macro series is admitted. There is no recession probability, historical
score, fitted model or threshold selection. Software fixtures will not change this.

| Diagnostic inputs | USA/FED evidence | Euro-area/ECB evidence | Other EU jurisdictions |
|---|---|---|---|
| GDP/growth and activity | MISSING | MISSING | MISSING |
| Unemployment | FRED UNRATE RAW_ONLY, date-level vintages | MISSING | MISSING |
| Employment/payroll growth | MISSING | MISSING | MISSING |
| Headline/core inflation | CPI indexes RAW_ONLY; not interchangeable with inflation-rate units | HICP index RAW_ONLY; core MISSING | MISSING |
| PCE/core PCE | MISSING | Not an automatic HICP substitute | MISSING |
| Policy rate | FEDFUNDS monthly average RAW_ONLY; not a silently substituted target rate | MISSING | MISSING; never ECB fallback |
| Yield curve | DGS10/DGS2 RAW_ONLY; DGS3MO MISSING | Sovereign curve MISSING | MISSING |
| HY/IG credit | MISSING; no rights/admission evidence | MISSING | MISSING |
| Financial conditions/liquidity | MISSING | MISSING | MISSING |
| Market stress | VIX MISSING | Regional volatility proxy MISSING | MISSING |
| Sahm-type deterioration | Not computed; requires admitted unemployment vintages and explicit transform | No automatic transfer of US definition | MISSING |

The diagnostic dictionary will use canonical semantic series and explicit units;
it does not claim that a named provider already supplies them. In particular, CPI
and HICP indexes are not annual inflation rates, and an observed macro level does
not establish the corresponding growth or acceleration measure.

The observed raw source spans, request bounds, rights/rate uncertainties and hashes
are in `development-panel-admission.md`, `data-source-quality-map.csv` and
`data-admission-evidence.json`. No proprietary PMI or licensed credit series was
assumed accessible. Official activity proxies remain candidates, not fabricated data.

Admission must bind the canonical observation content, source, series, region,
monetary jurisdiction, units/currency, period scope, quality justification and
publication/availability rule. A source hash establishes integrity, not truth or
permission. Future real diagnostics require review of these records and their actual
supporting evidence before accepting an ADMITTED decision.
