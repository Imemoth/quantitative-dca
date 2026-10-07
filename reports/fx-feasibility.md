# FX feasibility

Candidate class: **PROXY_POSSIBLE_WITH_LIMITATION**. Full execution FX admission:
**METHODOLOGY_BLOCKED_BY_DATA**. Provider rows X1/X2 and P25/P26 apply.

The retained MNB sample proves a date-bounded response and quote-unit convention,
not execution-time availability. Read unit per row, normalize to HUF per one
foreign-currency unit and preserve the original quote. A cross uses
HUF/EUR divided by USD/EUR to obtain HUF/USD, with available_at equal to the later
of both leg availabilities. A missing leg cannot be filled from a later release.

| Metadata | Current evidence | Admission requirement |
|---|---|---|
| EUR/HUF and USD/HUF | one retained MNB date | full eligible historical date coverage |
| Fixing/publication | date-only sample; prior policy audit | historical timezone-aware publication bound, not fixing assumption |
| Revision | no historical correction ledger | original values/corrections or an evidenced immutable-value rule |
| Holidays | not reconciled | source and security calendars, historical exceptions |
| Missing dates | no execution rule admitted | only last actually available quote; max-staleness policy reviewed |
| Other EU currencies | no complete historical mapping | enumerate from actual dated universe; acquire required legs |
| Cost | reference quote, not bid/ask execution | separate local cost and HUF conversion, explicit conversion cost assumption |

The ECB framework retrieved now is a 2026 document; it cannot establish the
historical timing regime. Same-date reference rates must never be assumed available
at an earlier equity open. Prior-known reference conversion is a proposal under the
frozen architecture, not a silently activated replacement for execution economics.

Cheapest remediation: dated original policies/publications and a correction audit,
followed by a small bounded historical quote/calendar reconciliation. Paid FX is
not yet justified merely because it offers more rows; it would need to resolve
the actual timestamp/vintage and permitted-use gap.
