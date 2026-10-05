"""Evidenced, bounded next-open targets, physically separate from features.

O0 is the first exchange open strictly after the EOD signal. Holding returns
exit at O5/O20/O60; wait windows contain exactly O0..O4 and O0..O19. Returns
are unreinvested total wealth on the baseline holder's split-equivalent units.
All amounts are gross of transaction costs (no fitted cost/policy assumptions).
The Foundation economic-cost ledger supplies both endpoint wealth and delayed
entry cost: raw split-equivalent fill plus entitled cash distributions. Native
cashflows give local results; Foundation payable-date FX gives HUF results.

Targets reflect supplied, explicitly versioned evidence, not final truth.
Later revisions require rebuilding. Each horizon has its own maturity and
censor status. An incomplete aggregate has no target_end_timestamp and must
not be admitted as a complete multi-output training row.
"""
from collections import defaultdict
from dataclasses import dataclass, fields
from datetime import date, datetime, timezone

from quant_dca.calendars.service import (
    next_eligible_open, previous_eligible_eod, eligible_session_open,
)
from quant_dca.canonical.validate import DiscontinuityEvidence, validate_ohlcv
from quant_dca.corporate_actions.economics import economic_acquisition_cost, EconomicAcquisitionCost
from quant_dca.fx.conversion import FXService, FXQuoteUnavailable, StaleFXQuote
from quant_dca.point_in_time.asof import latest_known
from quant_dca.types import OHLCV, CorporateAction, Security, QualityTier

START = datetime(2010, 1, 1, tzinfo=timezone.utc)
END = datetime(2023, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class ActionCoverage:
    """Externally verified complete supplied action history, including absence.

    This is an audit assertion, never inferred from an empty action list.
    Supply separate narrow intervals to avoid late broad audits delaying short
    labels. Coverage must include all versions known through label_as_of.
    """
    security_id: str
    start_session: str
    end_session: str
    available_at: datetime
    source: str
    reference: str


@dataclass(frozen=True, slots=True)
class HorizonTarget:
    horizon: int
    target_end_timestamp: datetime | None = None
    censor_reason: str | None = None
    return_local: float | None = None
    return_huf: float | None = None
    direction_local: bool | None = None
    direction_huf: bool | None = None
    executable_min_return_local: float | None = None
    executable_min_return_huf: float | None = None
    better_entry_local: bool | None = None
    better_entry_huf: bool | None = None
    raw_bars: tuple[OHLCV, ...] = ()
    raw_versions: tuple[OHLCV, ...] = ()
    action_versions: tuple[CorporateAction, ...] = ()
    selected_actions: tuple[CorporateAction, ...] = ()
    selected_listing: Security | None = None
    listing_versions: tuple[Security, ...] = ()
    action_coverage: ActionCoverage | None = None
    discontinuity_evidence: tuple[DiscontinuityEvidence, ...] = ()
    economic_costs: tuple[EconomicAcquisitionCost, ...] = ()


@dataclass(frozen=True, slots=True)
class TargetRow:
    security_id: str
    exchange: str
    signal_at: datetime
    label_as_of: datetime
    baseline_open_at: datetime
    horizons: tuple[HorizonTarget, ...]
    target_end_timestamp: datetime | None
    censor_reason: str | None
    return_5d_local: float | None = None
    return_20d_local: float | None = None
    return_60d_local: float | None = None
    return_5d_huf: float | None = None
    return_20d_huf: float | None = None
    return_60d_huf: float | None = None
    direction_5d_local: bool | None = None
    direction_20d_local: bool | None = None
    direction_60d_local: bool | None = None
    direction_5d_huf: bool | None = None
    direction_20d_huf: bool | None = None
    direction_60d_huf: bool | None = None
    executable_min_return_5d_local: float | None = None
    executable_min_return_20d_local: float | None = None
    executable_min_return_5d_huf: float | None = None
    executable_min_return_20d_huf: float | None = None
    better_entry_5d_local: bool | None = None
    better_entry_20d_local: bool | None = None
    better_entry_5d_huf: bool | None = None
    better_entry_20d_huf: bool | None = None

    @property
    def selected_actions(self):
        return tuple(dict.fromkeys(a for h in self.horizons for a in h.selected_actions))

    @property
    def economic_costs(self):
        return tuple(c for h in self.horizons for c in h.economic_costs)


class _Censored(Exception):
    pass


def _aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('INVALID_TARGET_TIMESTAMP')
    return value


def _bounded(value, as_of):
    value = _aware(value)
    if not START <= value <= END:
        raise _Censored('DEVELOPMENT_DEPENDENCY_UNAVAILABLE')
    if value > as_of:
        raise _Censored('LABEL_EVIDENCE_NOT_YET_AVAILABLE')


def _provenance(row, as_of):
    for f in fields(row):
        if f.name in {'available_at', 'published_at', 'revised_at', 'announced_at'}:
            value = getattr(row, f.name)
            if value is not None:
                _bounded(value, as_of)
                if value > row.available_at:
                    raise ValueError('INVALID_TARGET_CHRONOLOGY')
    if not row.source.strip() or not row.revision_id.strip() or not isinstance(row.quality, QualityTier):
        raise ValueError('INVALID_TARGET_PROVENANCE')


@dataclass(frozen=True)
class _Prepared:
    horizon: int
    bars: tuple
    raw_versions: tuple
    versions: tuple
    actions: tuple
    listing: Security
    listing_versions: tuple
    coverage: ActionCoverage
    evidence: tuple
    maturity: datetime


def _prepare(horizon, opens, prices, actions, listings, coverages, evidence,
             security_id, exchange, as_of):
    end = opens[horizon]
    if end > END:
        raise _Censored('DEVELOPMENT_WINDOW_UNAVAILABLE')
    if end > as_of:
        raise _Censored('LABEL_WINDOW_NOT_YET_AVAILABLE')
    start_day, end_day = opens[0].date().isoformat(), end.date().isoformat()
    coverage_candidates = [c for c in coverages if c.security_id == security_id
        and c.start_session <= start_day and c.end_session >= end_day]
    if not coverage_candidates:
        raise _Censored('ACTION_COVERAGE_UNAVAILABLE')
    # An earlier complete audit is sufficient; never replace it merely because
    # another supplied interval has a later verification time.
    coverage = min(coverage_candidates, key=lambda c: _aware(c.available_at))
    _bounded(coverage.available_at, as_of)
    if not coverage.source.strip() or not coverage.reference.strip():
        raise ValueError('INVALID_ACTION_COVERAGE_PROVENANCE')
    date.fromisoformat(coverage.start_session)
    date.fromisoformat(coverage.end_session)

    groups = defaultdict(list)
    for r in prices:
        if r.security_id == security_id and start_day <= r.session_date <= end_day:
            if not isinstance(r, OHLCV) or r.price_basis != 'unadjusted':
                raise ValueError('RAW_CANONICAL_BAR_REQUIRED')
            _provenance(r, as_of)
            groups[r.session_date].append(r)
    bars = []
    for instant in opens[:horizon+1]:
        group = groups.get(instant.date().isoformat())
        if not group:
            raise _Censored('MISSING_ELIGIBLE_OPEN')
        row = latest_known(group, as_of)
        if row.open is None:
            raise _Censored('MISSING_ELIGIBLE_OPEN')
        bars.append(row)
    if any(r.exchange != exchange or r.currency != bars[0].currency for r in bars):
        raise ValueError('INCONSISTENT_TARGET_LISTING')

    listing_versions = tuple(s for s in listings if s.security_id == security_id)
    if not listing_versions:
        raise _Censored('LISTING_HISTORY_UNAVAILABLE')
    for s in listing_versions:
        _provenance(s, as_of)
    listing = latest_known(listing_versions, as_of)
    if listing.exchange != exchange or listing.currency != bars[0].currency:
        raise ValueError('INCONSISTENT_TARGET_LISTING')
    if listing.active_from > start_day or (listing.active_to is not None and listing.active_to <= end_day):
        raise _Censored('TERMINAL_LISTING_WITHIN_WINDOW')
    if listing.security_type != 'common_equity' or not listing.primary_listing:
        raise _Censored('INELIGIBLE_LISTING')

    scoped = tuple(a for a in actions if a.security_id == security_id)
    dependency_ids = {a.action_id for a in scoped if start_day <= a.ex_date <= end_day}
    versions = tuple(a for a in scoped if a.action_id in dependency_ids)
    action_groups = defaultdict(list)
    for a in versions:
        _provenance(a, as_of)
        if not a.action_id or a.exchange != exchange or a.currency != bars[0].currency:
            raise ValueError('INVALID_TARGET_ACTION')
        effective = eligible_session_open(exchange, date.fromisoformat(a.ex_date))
        if effective is None:
            raise ValueError('INVALID_ACTION_SESSION')
        if effective > END:
            raise _Censored('DEVELOPMENT_DEPENDENCY_UNAVAILABLE')
        action_groups[a.action_id].append(a)
    selected = tuple(latest_known(action_groups[k], as_of) for k in sorted(action_groups))
    payable_times = []
    for a in selected:
        if start_day <= a.ex_date <= end_day:
            if a.action_type not in {'split', 'dividend'}:
                raise _Censored('UNSUPPORTED_CORPORATE_ACTION')
            if a.action_type == 'dividend' and a.ex_date > start_day:
                if a.payable_at is None:
                    raise _Censored('DIVIDEND_PAYABLE_UNAVAILABLE')
                _bounded(a.payable_at, as_of)
                payable_times.append(a.payable_at)
    used_evidence = tuple(e for e in evidence if e.security_id == security_id
                          and start_day <= e.prior_session < e.session_date <= end_day)
    for e in used_evidence:
        _bounded(e.verified_at, as_of)
    validation = validate_ohlcv(bars, as_of=as_of, discontinuity_evidence=used_evidence)
    if validation.quarantined_rows:
        raise ValueError('INVALID_TARGET_RAW_PANEL:' + ','.join(validation.reasons))
    raw_versions = tuple(r for group in groups.values() for r in group)
    maturity = max([coverage.available_at, *[r.available_at for r in raw_versions],
        *[a.available_at for a in versions], *[s.available_at for s in listing_versions],
        *payable_times, *[e.verified_at for e in used_evidence]])
    return _Prepared(horizon, tuple(bars), raw_versions, versions, selected,
                     listing, listing_versions, coverage, used_evidence, maturity)


class _CheckedFX:
    """Validate injected service results with Foundation's canonical FX rules."""
    def __init__(self, service, as_of):
        self.service, self.as_of = service, as_of

    def resolve(self, base, quote, at_or_before):
        _bounded(at_or_before, self.as_of)
        value = self.service.resolve(base, quote, at_or_before)
        _provenance(value, self.as_of)
        _bounded(value.fixing_at, self.as_of)
        return FXService((value,), max_age=None).resolve(base, quote, at_or_before)


def _bounded_snapshot(prices, actions, listings, evidence, coverage, as_of):
    """Accept already materialized canonical snapshots, never fetch iterators.

    label_as_of is the declared knowledge ceiling; START/END are the fixed
    observation/vintage envelope. Listing inception and coverage-start metadata
    may describe earlier history; they are not market observations. Validate every record, even unrelated ones,
    before selecting target dependencies. Exact built-in containers and exact
    frozen record types exclude user-defined iteration/property fetch hooks.
    """
    coverages = () if coverage is None else (coverage,) if type(coverage) is ActionCoverage else coverage
    collections = (prices, actions, listings, evidence, coverages)
    if any(type(items) not in (list, tuple) for items in collections):
        raise TypeError('MATERIALIZED_TARGET_HISTORY_REQUIRED')
    record_types = (OHLCV, CorporateAction, Security, DiscontinuityEvidence, ActionCoverage)
    for items, record_type in zip(collections, record_types):
        if any(type(row) is not record_type for row in items):
            raise TypeError('CANONICAL_TARGET_SNAPSHOT_REQUIRED:' + record_type.__name__)
    snapshots = tuple(tuple(items) for items in collections)
    date_fields = {'session_date', 'ex_date', 'active_from', 'active_to',
                   'prior_session', 'start_session', 'end_session'}
    for items in snapshots:
        for row in items:
            for field in fields(row):
                value = getattr(row, field.name)
                if value is None:
                    continue
                if field.name.endswith('_at'):
                    _bounded(value, as_of)
                elif field.name in date_fields:
                    day = date.fromisoformat(value)
                    historical_reference = (
                        type(row) is Security and field.name == 'active_from'
                    ) or (type(row) is ActionCoverage and field.name == 'start_session')
                    if day > END.date() or (day < START.date() and not historical_reference):
                        raise _Censored('DEVELOPMENT_DEPENDENCY_UNAVAILABLE')
                    if day > as_of.date():
                        raise _Censored('LABEL_EVIDENCE_NOT_YET_AVAILABLE')
    return snapshots


def _compute(prepared, fx):
    p = prepared
    indexes = tuple(range(p.horizon)) + (p.horizon,) if p.horizon in (5,20) else (0,60)
    costs = tuple(economic_acquisition_cost(p.bars[i], p.bars[0], p.versions, fx) for i in indexes)
    local = tuple(sum(flow.native_amount for flow in c.cashflows) for c in costs)
    huf = tuple(c.total for c in costs)
    returns = ((local[-1]-local[0])/local[0], (huf[-1]-huf[0])/huf[0])
    values = dict(return_local=returns[0], return_huf=returns[1],
                  direction_local=returns[0] > 0, direction_huf=returns[1] > 0)
    if p.horizon in (5,20):
        threshold = .015 if p.horizon == 5 else .03
        for name, amounts in [('local',local), ('huf',huf)]:
            minimum = min(amounts[:-1])
            values[f'executable_min_return_{name}'] = (minimum-amounts[0])/amounts[0]
            # Compare acquisition costs directly to avoid subtractive rounding
            # turning the literal 1.5%/3% boundary into a false negative.
            values[f'better_entry_{name}'] = minimum <= amounts[0]*(1-threshold)
    return HorizonTarget(p.horizon, max(p.maturity, *[c.label_matures_at for c in costs]),
        raw_bars=p.bars, raw_versions=p.raw_versions, action_versions=p.versions, selected_actions=p.actions,
        selected_listing=p.listing, listing_versions=p.listing_versions, action_coverage=p.coverage,
        discontinuity_evidence=p.evidence, economic_costs=costs, **values)


def build_targets(prices, actions, *, security_id, exchange, signal_at, label_as_of,
                  action_coverage, listing_history, fx_service, discontinuity_evidence=()):
    """Build target-only outputs from bounded canonical evidence, with no fetches.

    Missing horizons are censored, malformed evidence raises. FX resolution is
    injected; all known per-horizon requirements are preflighted before any FX
    call. All-censored calendar windows touch no history. Otherwise inputs
    must be built-in lists/tuples of canonical records wholly bounded to
    2010–2023 and label_as_of; lazy/provider iterables are rejected without
    iteration. An out-of-bound horizon never requests a post-2023 quote. The
    caller must separately establish signal-time universe eligibility.
    """
    _aware(signal_at)
    _aware(label_as_of)
    if not START <= signal_at <= label_as_of <= END:
        raise ValueError('DEVELOPMENT_TARGET_CUTOFF_REQUIRED')
    latest_close = previous_eligible_eod(exchange, signal_at)
    baseline = next_eligible_open(exchange, signal_at)
    # Reject intraday signals: an EOD signal belongs after the latest close and
    # before the next open following that close.
    if baseline != next_eligible_open(exchange, latest_close):
        raise ValueError('EOD_SIGNAL_REQUIRED')
    opens = [baseline]
    for _ in range(60):
        opens.append(next_eligible_open(exchange, opens[-1]))
    window_reasons = {h: ('DEVELOPMENT_WINDOW_UNAVAILABLE' if opens[h] > END else
                         'LABEL_WINDOW_NOT_YET_AVAILABLE' if opens[h] > label_as_of else None)
                      for h in (5,20,60)}
    snapshot_reason = None
    if any(reason is None for reason in window_reasons.values()):
        try:
            prices, actions, listings, evidence, coverages = _bounded_snapshot(
                prices, actions, listing_history, discontinuity_evidence, action_coverage, label_as_of)
        except _Censored as exc:
            snapshot_reason = str(exc)
    prepared = []
    for horizon in (5,20,60):
        reason = window_reasons[horizon] or snapshot_reason
        if reason:
            prepared.append(HorizonTarget(horizon, censor_reason=reason))
            continue
        try:
            prepared.append(_prepare(horizon, opens, prices, actions, listings, coverages,
                                     evidence, security_id, exchange, label_as_of))
        except _Censored as exc:
            prepared.append(HorizonTarget(horizon, censor_reason=str(exc)))
    fx = _CheckedFX(fx_service, label_as_of)
    outcomes = []
    for p in prepared:
        if isinstance(p, HorizonTarget):
            outcomes.append(p)
            continue
        try:
            outcomes.append(_compute(p, fx))
        except (FXQuoteUnavailable, StaleFXQuote, _Censored) as exc:
            outcomes.append(HorizonTarget(p.horizon, censor_reason='FX_UNAVAILABLE:' + str(exc)))
    reason = next((h.censor_reason for h in outcomes if h.censor_reason), None)
    maturity = None if reason else max(h.target_end_timestamp for h in outcomes)
    flattened = {}
    for h in outcomes:
        for name in ('return', 'direction', 'executable_min_return', 'better_entry'):
            if h.horizon == 60 and name in ('executable_min_return', 'better_entry'):
                continue
            for currency in ('local', 'huf'):
                flattened[f'{name}_{h.horizon}d_{currency}'] = getattr(h, f'{name}_{currency}')
    return TargetRow(security_id, exchange, signal_at, label_as_of, baseline,
                     tuple(outcomes), maturity, reason, **flattened)
