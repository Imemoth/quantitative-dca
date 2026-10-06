# Recession Risk Core — contract and architecture

Read-only diagnostic scaffold. No financial model or probability claim.

Persistence API: `write_diagnostic(snapshot, config=cfg, evidence=canonical_inputs,
root=...)`. Before any write, the engine replays the supplied canonical evidence
under the supplied configuration and compares the complete snapshot. A mismatch
fails closed. Content and PIT checks are reused, not reimplemented in the writer.
Output contracts reject mutable collections and non-contract nested substitutes;
direct construction does not bypass persistence replay. Admission attestations
remain a trusted reviewed input, not an authenticity certification.

## Flow and boundaries

`DiagnosticConfig + canonical Observation + reviewed Admission + SnapshotRef`
→ request guards → regional EOD → canonical vintage selection → content/admission
verification → usable measures and evidence confidence → configured pillar rules
→ configured scenario conjunctions → immutable MacroRiskSnapshot.

`registry.py` owns the separate 31-input contract, eight vocabularies and optional
rule definitions; `evidence.py` scopes admission; `engine.py` selects and validates;
`rules.py` evaluates declared bands and conjunctions; `contracts.py` contains frozen
outputs; `reporting.py` persists separately and exports the dictionary.

Reuse: canonical Observation/Region/QualityTier, latest_known/assert_pit_safe,
previous_eligible_eod, development_request/bounded_evidence, verify_evidence,
evidence_frame, snapshot_hash and write_snapshot. The security-level macro feature
builder is not called with an invented security; no duplicate weaker PIT selector is
implemented. Derived diagnostic measures must arrive with admitted canonical units
and definitions. This core does not manufacture growth rates from unadmitted indexes.

The sidecar imports no feature, target, model, policy, backtest or regime module.
Shared infrastructure has no new back-reference. Existing feature/regime YAML and
both model dictionaries are byte-identical to main. No ticker is an input; canonical
observations must have entity_id=None. US/FED uses XNYS EOD, EU/ECB uses XETR EOD as
an explicit regional diagnostic reference calendar, not an assertion about every EU
security. Non-euro/unsupported jurisdictions return INSUFFICIENT_EVIDENCE without ECB
fallback. Local diagnostic calendars can be added only with explicit mapping review.

## Evidence and replay

Each input's latest knowable vintage is selected within its period using canonical
economic revision order, then the latest released period is selected. Future
development rows are excluded; malformed selected/future chronology hard-fails.
Selected availability must be <= regional EOD <= requested as_of. Same-day releases
after that EOD await the next eligible EOD. All financial clocks are bounded to
2010–2023, and only role=diagnostic is accepted before touching the iterable.

Admission binds source, series, region/jurisdiction, unit/currency, period scope,
source snapshot identity and assessed quality. It requires nonempty review references
and an availability rule. This is an explicit trusted review attestation; the software
does not authenticate a provider, verify licenses or turn a string reference into
independent truth. No actual source attestation is ADMITTED in this phase.
Canonical source bytes must match their immutable snapshot; paths do not enter output
identity. Conflicting attestations and ambiguous revision clocks hard-fail.

Later development observations never enter earlier output hashes. Selected evidence
references include source/revision/period, availability/publication/revision timestamps,
source hash, admission hash and review references. A raw/nonadmitted observation can
appear as evidence of a gap, but its value is withheld and contributes no usable weight.
No backward fill or fallback to an older good vintage when the latest is missing.

## State contracts

| Pillar | Vocabulary |
|---|---|
| Growth | HEALTHY, COOLING, DETERIORATING, CONTRACTIONARY, UNKNOWN |
| Labor | HEALTHY, COOLING, DETERIORATING, STRESS, UNKNOWN |
| Inflation | BENIGN, ELEVATED, STICKY, ACCELERATING, UNKNOWN |
| Monetary/policy | ACCOMMODATIVE, NEUTRAL, RESTRICTIVE, UNKNOWN |
| Curve | NORMAL, FLAT, INVERTED, UNKNOWN |
| Credit | NORMAL, WATCH, STRESS, CRISIS, UNKNOWN |
| Conditions/liquidity | EASY, NEUTRAL, TIGHT, STRESS, UNKNOWN |
| Market stress | NORMAL, WATCH, STRESS, CRISIS, UNKNOWN |

Vocabulary comes from versioned YAML. Evidence states are COMPLETE_EVIDENCE,
PARTIAL_EVIDENCE or INSUFFICIENT_EVIDENCE. Partial/empty pillars always stay UNKNOWN.
Default economic rules are empty; even full data does not imply HEALTHY.

An optional BandRule maps a single admitted measure to explicit sorted, unique
boundaries ([lower, upper)), state, polarity and fixed description. At most one rule
per pillar/context. Only a complete pillar can emit a driver; each driver identifies
the rule, value, input and selected evidence. No LLM narrative generation.

Overall vocabulary: NORMAL_EXPANSION, SOFT_LANDING, LATE_CYCLE_SLOWDOWN,
STAGFLATION_RISK, RECESSION_RISK, CREDIT_STRESS, RECOVERY, INSUFFICIENT_EVIDENCE.
Optional ordered ScenarioRules are conjunctions of named pillar states; all critical
inputs must be usable. First two matches become dominant/secondary. No score is
normalized into a probability. No matches/default empty rules mean INSUFFICIENT_EVIDENCE.
Fixture band boundaries and scenarios demonstrate software behavior only and are not
stored as economic defaults in the released config.

## Confidence and immutable output

Usable = ADMITTED + acceptable quality + nonmissing finite value + fresh evidence.
Age is calendar days since observation period date; freshness=max(0,1-age/max_age_days).
At the configured age limit the input is stale. Frequency-specific limits are
operational scaffold defaults (10/20/45/65/180 days), not validated economic thresholds.
Admission must review period labeling and carry conventions before real use.

Completeness = usable input count / configured context input count.
Critical completeness = usable critical count / configured critical count.
Data confidence = mean over all configured inputs of
`usable × quality_weight × freshness × publication_certainty`, multiplied by critical
completeness. Weights A=1/B=.7/C=.3; missing publication=.5, explicit publication=1.
Tier A requires explicit publication. These are transparent software heuristics,
not fitted reliability or event probabilities; default quality floor B excludes C.
No hash or test PASS contributes to confidence. Unassigned quality contributes zero.

MacroRiskSnapshot stores as_of/effective EOD, region/jurisdiction, pillar states,
input measures, evidence references, admission/quality, dominant/secondary scenario,
evidence/critical completeness, data confidence, drivers, max input availability,
publication timestamps, config hash, source snapshot hashes and reason codes. It is
frozen and built from immutable tuples. Its identity uses the shared canonical hash.
Persistence uses the existing point_in_time layer under a separate diagnostic root;
it is not a model feature table. Same inputs/config reproduce the same output.

Historical smoke diagnostic: HISTORICAL_DIAGNOSTIC_BLOCKED_BY_DATA_ADMISSION.
Synthetic replay tests do not change that status.
