# Recession core independent reviews

## Initial review — baseline 3ad752a to f4e863c

Independent spec reviewer: **PASS**, no Critical/Important findings. Checked the
35-section mandate, dictionary, unchanged frozen contracts and zero-evidence probe.
Minor concerns: nested output mutability and stale final readiness test counts.

Independent code-quality reviewer: **FAIL**, no Critical but three Important findings:

1. Frozen output dataclasses accepted caller-owned lists, allowing post-construction
   mutation to change snapshot hashes.
2. Persistence accepted forged snapshots without rechecking development/PIT or
   derived confidence/state consistency; future availability and a pre-development
   as-of could be stored.
3. DiagnosticConfig accepted mutable dataclass substitutes for nested contracts.

Minor: validate_selected did not itself bind observation.series to the definition;
dense validation statements reduce audit readability.

Both reviews excluded financial performance, real provider licensing/authenticity,
economic calibration and real-panel readiness from their verdicts. Neither treated
reported test counts as an independently rerun full suite.

## Controller disposition and fixes

All three Important issues accepted after reproducing the behavior. New boundary
tests initially showed mutable output/config acceptance and five forged persistence
cases storing successfully. Missing replay API caused additional expected failures.
Nonfinite serialization and mutable Context rejection already existed.

Output constructors now enforce exact immutable collection/member types; snapshot
construction checks development/PIT clocks, fraction ranges and empty-evidence
consistency. Config validates concrete frozen member types before using attributes.
Persistence now requires the config and canonical evidence, rebuilds through the
same PIT builder and rejects any mismatch before creating output files. This also
rechecks evidence content hashes instead of trusting embedded provenance strings.

The separate series-binding regression failed before its narrow guard was added.
Readability improved in new boundary code; broad formatting-only churn deferred.

Re-review: **PENDING**. This document does not close the checkpoint.
