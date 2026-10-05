# Task 5 — point-in-time as-of selection and leakage guard

## Scope and interfaces

Implemented `quant_dca.point_in_time.asof` with two public interfaces:

- `latest_known(rows, as_of)` returns the latest historically knowable vintage
  from one logical series/feature, entity and observation-period group.
- `assert_pit_safe(feature_values, prediction_timestamp)` raises a hard
  `PIT_LEAKAGE` error when a feature or any of its inputs was unavailable at
  the prediction timestamp.

Both functions accept timezone-aware datetimes in any UTC offset and compare
absolute instants. `latest_known` accepts canonical records and mappings. The
brief's mappings containing only `value` and `available_at` are treated as one
implicit group and work without canonical identity fields.

## Selection and validation behavior

`latest_known` validates every supplied row before applying the cutoff. When
identity metadata is present, every row must explicitly and consistently name
one `series` or `feature`, `entity_id`, and `observation_date`. Mixing periods,
series, entities, implicit rows, or series and feature namespaces fails closed.
This prevents a revision for an older observation period from being returned as
the current reading for a different period.

Every availability, publication and revision timestamp must be a valid aware
`datetime`. Publication and revision cannot occur after availability, and a
revision cannot precede publication. The selector filters on
`available_at <= as_of`, then chooses the greatest availability timestamp.
When records share that timestamp, an explicit later `revised_at` is the only
secondary ordering key. Exact duplicates deterministically return the first
input object. Conflicting rows with indistinguishable chronology raise
`PIT_AMBIGUOUS_VINTAGE`; revision IDs are never sorted lexicographically. No
eligible historical vintage raises `PIT_NO_KNOWN_VINTAGE`.

`assert_pit_safe` supports the required iterable-of-datetimes form and actual
`FeatureValue` records (as well as equivalent mappings). For feature records it
enforces:

- `available_at <= prediction_timestamp`
- `max_input_available_at <= prediction_timestamp`
- `as_of <= prediction_timestamp`
- both feature availability and maximum input availability are no later than
  the feature's declared `as_of`
- `max_input_available_at <= available_at`
- common publication/revision/availability chronology

`computed_at` must be an aware datetime when present, but an offline snapshot
may be computed after the historical prediction timestamp. Targets remain a
separate concern; this API accepts and checks feature availability metadata and
does not join or construct targets.

## TDD and verification

The initial focused RED run failed during collection with the expected
`ModuleNotFoundError` for `quant_dca.point_in_time`. After the first
implementation, the focused suite passed 27 tests. A second RED case proved
that feature availability after the feature's own `as_of` was not yet rejected;
it failed with `DID NOT RAISE ValueError`, then passed after the guard was added.

The final focused command, `python -m pytest tests/point_in_time/test_asof.py
-v`, passed 28 tests. The fresh full repository command, `python -m pytest -v`,
passed all 261 tests. `reports/task-5-tests.txt` preserves the RED and GREEN
evidence.

Tests cover historical revision selection, minimal dictionaries, non-UTC aware
offsets, mixed and incomplete groups, deterministic exact duplicates,
ambiguous ties, explicit revision-time ordering, no-known-vintage behavior,
invalid/naive timestamps, invalid publication/revision chronology, bare
datetime leakage, real `FeatureValue` instances, all feature/input cutoff
relations, and permitted later offline computation. They use fixtures only,
with no network or retrospective-holdout access.

## Decisions and concerns

- Callers needing results for many groups must group explicitly and invoke
  `latest_known` once per group. Silent multi-group selection would make the
  requested period ambiguous.
- Revision IDs are provenance labels, not an ordering contract. Providers that
  need a tie resolved must supply chronological `revised_at` evidence.
- Exact duplicate acceptance preserves the first input object's identity while
  returning the same record content. Conflicting tied records fail closed.
- Fixture tests establish software behavior only. They do not establish actual
  2015–2023 coverage, vendor timestamp truth, or historical research validity.
- This task made no network request and did not access or evaluate the
  retrospective holdout.
