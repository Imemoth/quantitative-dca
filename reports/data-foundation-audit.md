# Data and point-in-time foundation audit — Task 10

Audit date: 2026-09-15
Fixture cutoff: `2020-03-12T00:00:00+00:00`

## Decision

The foundation software can deterministically validate, quarantine, select a
known vintage, persist immutable canonical and feature snapshots, and verify
feature lineage. This is a **software gate only**. The current provider
artifacts are `RAW_ONLY` or unavailable, Task 0's real-source qualification is
incomplete, and there is no admitted US/EU research panel. Model research must
not consume this fixture or the current raw provider artifacts as evidence.

The synthetic fixture is explicitly
`SYNTHETIC_NOT_RESEARCH_EVIDENCE`. Its internal `QualityTier.C` values exercise
the typed contract only; they do not assess any actual provider and must not be
read as an allowed proxy. Every actual provider/domain tier in the quality map
is `NULL (unassigned)`.

## Deterministic machine evidence

Command, executed twice from the repository root:

```text
python -m quant_dca.tools.build_fixture_snapshot --as-of 2020-03-12
```

Run 1:

```json
{"as_of":"2020-03-12T00:00:00+00:00","canonical_snapshot_sha256":"e3ef981c533cd6d30fda349061162226ca972ef9d4fe53a42f8de6fcd1ee483e","data_sha256":"57b93bfa6e061c092bd165f237a2f8a20f182cbffc222b21eeaa22373ba323df","fixture_classification":"SYNTHETIC_NOT_RESEARCH_EVIDENCE","quarantine_reasons":{"MISSING_VALUE":1},"quarantined_rows":1,"snapshot_path":"data/fixture_snapshots/features/20200312T000000.000000Z/e5f0c42009db82bb3f217d44a451c1ad44960c62e97eaabeb28c4de3ef5f0972.parquet","snapshot_sha256":"e5f0c42009db82bb3f217d44a451c1ad44960c62e97eaabeb28c4de3ef5f0972"}
```

Run 2:

```json
{"as_of":"2020-03-12T00:00:00+00:00","canonical_snapshot_sha256":"e3ef981c533cd6d30fda349061162226ca972ef9d4fe53a42f8de6fcd1ee483e","data_sha256":"57b93bfa6e061c092bd165f237a2f8a20f182cbffc222b21eeaa22373ba323df","fixture_classification":"SYNTHETIC_NOT_RESEARCH_EVIDENCE","quarantine_reasons":{"MISSING_VALUE":1},"quarantined_rows":1,"snapshot_path":"data/fixture_snapshots/features/20200312T000000.000000Z/e5f0c42009db82bb3f217d44a451c1ad44960c62e97eaabeb28c4de3ef5f0972.parquet","snapshot_sha256":"e5f0c42009db82bb3f217d44a451c1ad44960c62e97eaabeb28c4de3ef5f0972"}
```

The two complete outputs and snapshot identities match. The canonical source
snapshot selected `eu-first` and `us-revised`; the later
`us-future-revision` was not knowable at the cutoff. Canonical validation
quarantined one separate row for `MISSING_VALUE`. The feature snapshot binds
its canonical source, availability rule, source observation IDs, source
timestamps, transform, schema and cutoff through `FeatureLineage`.

`snapshot_sha256` is the full metadata-bound identity. `data_sha256` is the
logical table-only digest. Equal table values alone are not sufficient proof of
the same snapshot provenance.

## Observed source inventory

The audit preserves all six observed source/domain rows from
`reports/observed-source-inventory.csv`. “Observed” includes bounded failed
access attempts; it does not mean that usable observations were returned.

| # | Provider / inventory domain | Actual evidence | Admission | Tier |
|---:|---|---|---|---|
| 1 | FRED/ALFRED — US macro | Four monthly series2010-01..2023-11; follow-up bounded vintage chunks obtained DGS10/DGS2 nonmissing dates2010-01-04..2023-12-28 | `RAW_ONLY` | NULL |
| 2 | EODHD demo — US OHLCV | One active demo symbol, 3,522 rows, 2010-01-04..2023-12-29 | `RAW_ONLY` | NULL |
| 3 | EODHD demo — EU OHLCV and FX | SAP.XETRA and EURHUF.FOREX bounded requests returned 403; no data | `UNAVAILABLE` | NULL |
| 4 | Stooq — US/EU OHLCV | Bounded US `.com` and EU `.pl` paths returned 404; no data | `UNAVAILABLE` | NULL |
| 5 | SEC archive — US fundamentals | Two quarter indexes and one original 2010 10-K; canonical adapter remains unavailable | `RAW_ONLY` | NULL |
| 6 | FRED/ALFRED — EU macro | One euro-area aggregate series, 362 rows for 167 periods, 2010-01..2023-11 | `RAW_ONLY` | NULL |

The detailed evidence, limits and restrictions are in
`reports/data-source-quality-map.csv`. The inventory reports support no
automatic B/C assignment, no inferred provider coverage, and no inferred
rights, rate limits, or costs.

Post-Task10 source-audit supplement: `reports/fred-yield-retry-2026-09-15.md`
records the observed2000-vintage JSON limit and successful smaller bounded
requests for the two yields. Their overlapping, request-clipped intervals are
not yet stitched or admitted. This supplements source access evidence only;
the synthetic fixture and its original machine outputs above are unchanged.

## Eleven-domain readiness

| Required domain | State | Primary PIT / bias limitation | Research restriction |
|---|---|---|---|
| US macro | `RAW_ONLY`, tier NULL | Date-level vintages exist, but exact release time, completeness, rights and full basket are unresolved | Not admitted |
| EU macro | `RAW_ONLY`, tier NULL | One euro-area aggregate is not full EU; release time, definition and geography history unresolved | Not admitted |
| US OHLCV | `RAW_ONLY`, tier NULL | One active demo symbol; corrections, actions, volume basis, rights and delisted coverage unresolved | No equity-panel research |
| EU OHLCV | `UNAVAILABLE`, tier NULL | Tested EODHD/Stooq paths returned no usable data | Missing |
| FX | `UNAVAILABLE`, tier NULL | No execution-time quotes, publication timing or correction history | No base-currency conversion research |
| US fundamentals | `RAW_ONLY`, tier NULL | Samples lack parser, fact/restatement handling, dissemination semantics and security mapping | Not admitted |
| EU fundamentals | `UNAVAILABLE`, tier NULL | No pan-EU dated filing panel or publication ledger | Missing |
| Corporate actions | `UNAVAILABLE`, tier NULL | No observed split/dividend/merger/delisting ledger or terminal economics | Missing; returns cannot be certified |
| Historical universe/delistings | `UNAVAILABLE`, tier NULL | No active/delisted US/EU membership and identifier history | Missing; cross-sectional work blocked by survivorship risk |
| Sector/index context | `UNAVAILABLE`, tier NULL | No dated classifications/components, revisions, entitlements or publication times | Corresponding features structurally missing |
| Scheduled event calendars | `UNAVAILABLE`, tier NULL | A discovered 2023 schedule is not a 2010–2023 ex-ante schedule-vintage dataset | Corresponding features structurally missing |

## Quarantine, PIT and survivorship findings

- The fixture machine output records one quarantined synthetic observation and
  the exact reason. Provider raw artifacts have not passed canonical admission,
  so they have no canonical quarantine result. “Zero provider quarantines” is
  not claimed.
- FRED/ALFRED evidence demonstrates date-level vintage intervals but not exact
  historical publication times or revision completeness. SEC's observed raw
  acceptance header is not yet verified as public dissemination time. EODHD's
  currently served price history is not evidence of what correction state was
  available historically.
- One active US demo symbol provides no active/delisted universe. No source
  establishes US/EU historical eligibility, identifier changes, terminal
  consideration, complete corporate actions, or historical sector membership.
  The resulting survivorship and terminal-return risks block real equity-panel
  evidence.
- Every successful request recorded in the provider audits was restricted to
  2023 or earlier before transmission. The audits do not establish rate limits
  or complete license/redistribution rights. No purchase or paid entitlement
  was assumed.

## Protocol and scope

The documentation-response incident remains recorded in
`reports/lockbox-access-incident.md`. Under
`docs/evaluation-protocol-amendment-2026-09-11.md`, 2024-01-01 through
2026-09-11 is a **RETROSPECTIVE HOLDOUT**, not pristine or blind, and it has not
been evaluated here. The amendment authorizes continued software
implementation despite unresolved source gaps; it does not admit data or erase
the incident.

Task 10 does not freeze provider configuration or V1, does not establish full
Task 0 completion, and reports no OOS, retrospective-holdout or forward-lockbox
result. Actual 2015–2023 research evidence still requires a separately admitted
panel. Any later retrospective-holdout evaluation remains subject to complete
V1 freeze and human review.
