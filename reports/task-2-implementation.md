# Task 2 implementation — exchange session service

Implemented against the Task 2 brief and approved evaluation amendment dated 2026-09-11.

## Public contracts

- `previous_eligible_eod(exchange, ts)`: latest scheduled regular-session close **at or before** an aware timestamp; includes early closes.
- `next_eligible_open(exchange, ts)`: first scheduled regular-session open **strictly after** an aware timestamp. A query exactly at an open advances to the next session; an intraday query does likewise.
- `nth_subsequent_open(exchange, session, n)`: open of the nth trading session strictly following an exchange-local `datetime.date` session label. `n=1` means next session. Rejects strings/datetimes as labels, holiday/weekend baselines, nonpositive/noninteger n and bool.
- All returned timestamps are standard Python UTC-aware datetimes. Timestamp functions accept other aware timezones and normalize the instant; reject naive and non-datetime values.
- Unsupported MICs and unavailable calendar coverage fail with ValueError; no weekday fallback.

## Supported exchange MICs

| MIC | exchange_calendars schedule |
| --- | --- |
| XNYS | XNYS |
| XNAS | XNYS (explicit shared regular-session mapping, consistent with upstream XNAS alias) |
| XETR | XETR |
| XLON | XLON |
| XPAR | XPAR |

Pinned `exchange-calendars==4.13.2`, the installed and tested version. Each schedule is built from the dependency's local rules for 2009-01-01 through 2030-12-31 and cached. Explicit bounds avoid the package's moving default historical window. The 2009 buffer supports the initial 2010 research boundary. Queries outside this interval, and results requiring sessions outside it, fail closed. This future calendar metadata is not market observations or authorization for holdout evaluation.

## TDD and verification

`reports/task-2-tests.txt` preserves the actual RED run (service absent: ModuleNotFoundError at collection), GREEN run, and full regression output, in that order.

- RED: `python -m pytest tests/calendars/test_service.py -v` — exit 2, expected absent service.
- GREEN: same command — **60 passed**.
- Regression: `python -m pytest -q` — **158 passed**, including the 98 preexisting contract tests.
- `git diff --check` — clean.

Literal fixtures exercise US Labor/Independence/Thanksgiving holidays, Xetra and Paris Easter closures, the 2023 London coronation holiday, US Hurricane Sandy closure, different US/EU DST transition weeks and both fall transitions, monthly first eligible sessions, microsecond/exact-open and exact-close boundaries, early closes, holidays between subsequent sessions, invalid inputs, and exhausted schedule bounds. In particular, the EOD preceding 2010-01-01 is 2009-12-31 for XNYS but 2009-12-30 for XETR. No mocked schedule and no market-data network request was used.

## Limits for downstream consumers

A scheduled close is not the publication/availability timestamp of a provider bar; downstream PIT checks remain mandatory. Schedules represent regular exchange sessions, not security-specific halts, guaranteed execution, extended hours or auction access. Historical calendar reconstruction does not itself provide a PIT archive of when exceptional closures were announced. Future rules may change and need reviewed dependency updates. The dependency pin does not lock transitive dependency versions. Calendar fixtures establish software behavior, not historical research validity. No retrospective holdout evaluation was run.
