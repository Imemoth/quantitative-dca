# Features Task 5 implementation report

Date: 2026-09-17  
Scope: region-aware macro and announced scheduled-event features  
Status: implementation complete; pending independent review

## Implemented contract

- `src/quant_dca/features/macro.py` emits exactly the 13 macro features already registered in `features-v1`.
- `src/quant_dca/features/events.py` emits exactly the 6 event-calendar features already registered in `features-v1`.
- No registry, model, target, regime, provider, dataset, or audit contract changed.

## Design choices

### Macro

- Provider series IDs are supplied through `MacroSeriesMap`. Regional series, monetary-jurisdiction policy/liquidity series, US curve legs, EU curve legs, and the global risk series are explicit mappings rather than inferred identities.
- Every observation period first resolves to its latest vintage known at the eligible EOD cutoff. The builder then selects the latest released observation period. A recently revised older period therefore cannot displace a later observation period.
- Three-month policy-rate and central-bank-liquidity changes anchor on the selected current observation period and select the latest knowable observation no later than three calendar months before it.
- US curve features are calculated from explicit 10Y, 2Y, and 3M legs. The EU curve proxy is calculated from explicit common-backdrop long and short legs. No redundant transform family was generated.
- A security's `monetary_jurisdiction` is mandatory. A non-euro EU security resolves only through its local jurisdiction mapping; missing local evidence remains missing and never falls back to ECB data.
- Tier C selected macro or classification evidence fails the Tier B registry floor. Unknown series evidence remains missing. Future candidate vintages are validated and filtered by the canonical as-of selector; the direct classification record fails on future availability.

### Scheduled events

- The plan's `days_until_known_event` helper remains intentionally date-only and conservative. An announcement on the prediction date does not establish within-day availability, so it returns missing.
- Production event features require aware `event_at`, `announced_at`, and `available_at` timestamps plus provenance, quality, revision identity, status, and the relevance key for the event type.
- Event versions resolve by `event_id` at the eligible EOD cutoff. Known cancellations and reschedules replace earlier versions; future revisions do not alter the historical snapshot.
- Earnings relevance uses `security_id`, policy relevance uses `monetary_jurisdiction`, and inflation-release relevance uses `region`.
- Event distance counts actual exchange sessions. Holidays and weekends do not count. An announced after-close event on the snapshot date has distance zero; an event that occurred before the EOD cutoff is no longer a future event.
- Tier C selected calendar evidence fails the Tier B floor. The direct security classification fails on future availability.

### Feature provenance

- Each `FeatureValue` records the requested prediction timestamp in `as_of`, the eligible EOD snapshot date, the maximum availability timestamp of its selected direct dependencies, the worst accepted dependency quality, and the security region/exchange/currency.
- Macro and event builders run `assert_pit_safe` on their outputs before returning them.

## TDD and verification evidence

RED was observed before either production module existed:

```text
python -m pytest tests/features/test_macro_events.py -v
ModuleNotFoundError: No module named 'quant_dca.features.events'
```

The focused suite then passed after implementation:

```text
python -m pytest tests/features/test_macro_events.py -v
9 passed
```

The first full-suite verification after the implementation passed:

```text
python -m pytest -q
477 passed in 14.30s
```

Focused tests cover exact registered output sets, vintage-before-period selection, future-vintage filtering, local non-euro policy mapping, direct future-input rejection, announcement availability, revisions and cancellations, same-day event timing, holiday-aware session distance, and Tier B floors.

## Limitations

- `MacroSeriesMap` is controlled metadata supplied by the caller. This task does not claim provider coverage or choose production series IDs.
- The macro block implements only the transforms frozen in the 13 registered outputs. It does not add broad 3M/6M/12M transform grids, full-history normalization, or learned parameters.
- Scheduled-event distances use supported security-exchange calendars and their frozen coverage window. Security-specific halts and unscheduled events are outside this calendar contract.
- Missing evidence is preserved. The builders do not impute macro values, reconstruct historical calendars from current calendars, or substitute regional policy proxies.
- All verification used fixtures dated within the authorized research boundary. No network data was requested or consumed.

## Independent review fix round 1

All three accepted P2 findings from `features-task5-review.md` were addressed:

- Session distance now derives the event day and cutoff day from their aware instants in the security exchange timezone. Equivalent UTC and New York representations that cross midnight therefore produce the same distance and within-5D threshold result.
- Event provenance now retains the latest known state of each historical candidate identity. An identity enters that causal scope only when a version known by the cutoff was both relevant to the security and still future at the cutoff. This carries known cancellations and relevance-changing revisions into `max_input_available_at` and worst-quality propagation without adding unrelated identities or unavailable future versions. `EventFeatureSnapshot.dependencies` exposes the evidence by event type.
- The security classification must be effective on the exchange-local cutoff date under `[active_from, active_to)` before its exchange, region, or monetary jurisdiction can be used.

The regression tests were observed failing before the fix:

```text
UTC/local representation: 6.0 sessions != 5.0 sessions
known cancellation: max_input_available_at 2020-01-03 != 2020-01-09
only cancellation: security clock 2010-01-01 != cancellation clock 2020-01-09
active_to at cutoff: expected INACTIVE_SECURITY_CLASSIFICATION was not raised
```

Final fix-round verification:

```text
python -m pytest tests/features/test_macro_events.py -v
13 passed in 2.44s

python -m pytest -q
481 passed in 14.76s
```
