# Minimum viable research panel (MVRP)

Machine contract: configs/provider_feasibility_v1.json, additive to the unchanged
configs/research_readiness_v1.json. No frozen feature, target, action or regime
contract changed. This contract is an admission checklist, not a model runner.

| Domain | Minimum role | Permitted degradation/proxy boundary |
|---|---|---|
| Historical universe | mandatory US+EU dated primary common-equity identities and eligibility | Audited historical proxy allowed by spec; no current-survivor cohort |
| OHLCV | mandatory eligible sessions, raw opens and original-unit volume | Individual missing/young-history rows flagged; no fake executable fills |
| Corporate actions/terminal economics | mandatory event population and reproducible economic treatment | Unreliable terminal outcomes flagged for sensitivity as spec permits; not dropped |
| FX | mandatory required local/HUF conversion legs | Prior-known reference proxy only if evidenced and reviewed |
| Fundamentals | mandatory vintage values and security/currency linkage | Sector-inapplicable ratios structurally missing; no globally absent family |
| Macro | mandatory regional and monetary-jurisdiction basket | Economically appropriate documented regional proxies require review |
| Market/sector context | mandatory dated benchmark/classification/calendar mappings | Indices/ETFs permitted for context; current classifications cannot be backfilled |
| Scheduled events | mandatory original known-at schedules | Realized dates are not an ex-ante proxy |

None of these eight families is optional. Optional enrichment: additional dashboard
inputs outside the frozen registry; this phase adds none. Degradable means limited
row-level missingness with preserved applicability, not removal of a family.

Coverage must span 2010–2014 warm-up and 2015–2023 development eligible sessions
and release periods for both regions. Eligibility retains the frozen minimum 120
trading sessions, primary common-equity rules, configured liquidity checks and
known published fundamentals where required. Longer lookbacks for young issuers
can remain missing. No extra minimum-security threshold is invented here.

Before a first model run, produce per-year/region/security eligibility denominators,
row counts, listing intervals, delisted and terminal counts, missingness by required
family, and unresolved-case sensitivity bounds. A few surviving US names or one EU
ADR cannot establish those denominators. Numerical coverage acceptance requires
review of the actual cohort; no ratio with a missing denominator can be PASS.

Each admitted row needs stable keys, units/currency, observation/effective dates,
known-at/publication/revision timestamps, immutable source lineage and hashes,
schema/config versions and justified quality tier. A/B-only and AllData views must
be reproducible; missing evidence never becomes C by default. Separate RAW,
CANONICAL, PIT SNAPSHOTS, FEATURE STORE and TARGET STORE. Preserve all 94 dictionary
slots (81 registered outputs and 13 alternative regime slots), the 20 target
definitions, 5D/20D/60D horizons and next-eligible-open execution semantics.

Fallback order for every family is machine-readable: selected primary candidate,
free official original, free commercial route, documented narrow proxy, low-cost
paid route, then methodology-blocked escalation. Each step retains the same PIT,
rights and coverage checks. No route automatically executes or grants a tier.

Admission and real leakage/quality PASS, independent data-methodology review and
explicit human authorization are all required. A tiny proof only tests feasibility;
it cannot substitute for the required development panel or authorize models.
