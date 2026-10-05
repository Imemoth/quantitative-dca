### Spec Compliance

- ❌ **Spec FAIL.** The diff implements all eight relative-strength outputs and explicit historical-universe ranking, but it does not fully enforce the required historical cutoff or hard-fail future-available direct inputs (`src/quant_dca/features/relative.py:187`, `src/quant_dca/features/relative.py:308`).

### Strengths

- `src/quant_dca/features/relative.py:109-139` defines a deterministic eligible-only percentile, including literal tie, singleton, missing, non-finite, and ineligible behavior; `tests/features/test_relative.py:29-48` checks those cases without deriving expected values from the implementation.
- `src/quant_dca/features/relative.py:150-162` produces exactly the six 20/60/120 stock-minus-sector/market returns and two historical percentiles, while `src/quant_dca/features/relative.py:374-376` fails if those names diverge from the V1 relative-strength registry.
- `src/quant_dca/features/relative.py:310-315` obtains eligibility only from the supplied `UniverseIndex`; `tests/features/test_relative.py:224-238` proves exclusion of a future member and retention of a later-delisted member. Security identifiers remain grouping metadata and are not emitted as numeric features (`src/quant_dca/features/relative.py:395-409`).
- `src/quant_dca/features/relative.py:167-178` applies the canonical PIT guard and validates availability, finite values, provenance, revisions, and quality for selected features. `src/quant_dca/features/relative.py:378-425` conservatively propagates clocks and worst quality and retains the selected provenance-bearing evidence in the snapshot.
- The diff adds no full-history normalization, imputation, empirical selection, future/outside-OOS evaluation, network access, or unrelated task work.

### Issues

#### Critical (Must Fix)

- None.

#### Important (Should Fix)

- `src/quant_dca/features/relative.py:308-315`, `src/quant_dca/features/relative.py:327-343` — eligibility and classifications are resolved at `previous_eligible_eod(exchange, prediction)`, before the code reads the stock return `observation_date`. Consequently, a valid but stale historical return supplied after a later close is ranked against the later membership/classification state: a security delisted between the observation and prediction cutoffs is rejected, while a later joiner can enter the rank universe. The existing regression only covers a prediction before the next close (`tests/features/test_relative.py:297-337`), where the prediction-derived cutoff happens to equal the observation EOD. Resolve the exchange-session EOD from the aligned return observation date (and verify that timestamp), then query `UniverseIndex` and classifications at that historical cutoff; add an after-close stale-row regression covering both a later delisting and later join.
- `src/quant_dca/features/relative.py:181-192` — a supplied direct stock, sector, or market return whose `available_at` is after the feature cutoff is silently skipped. With other horizons present, this yields a partially missing output instead of the required hard failure for a future-available input. This path also bypasses `_validate_feature`, so its PIT/provenance/quality checks never run. Validate every supplied direct row first and raise the PIT leakage error when either availability clock exceeds the historical cutoff; reserve missing output for an actually absent operand. Add a focused direct-input test for each mapping role or a parameterized equivalent.

#### Minor (Nice to Have)

- None.

### Assessment

**Task quality:** Needs fixes — **Quality FAIL**

**Reasoning:** The implementation is well structured and the reported evidence is substantial (`9` focused, `103` covering, and `446` full-suite tests passed), so those suites were not rerun. The two boundary defects can alter the eligible population or hide future data as missing, which makes the historical relative features untrustworthy until fixed.
