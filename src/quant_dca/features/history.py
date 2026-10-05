"""Evidenced per-security/EOD ingress for trailing features.

Coverage is an external audit assertion that the supplied action vintages are
complete over an interval, including verified absence of events. It is never
inferred from an empty list. Volume evidence binds to a raw bar revision.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math

from quant_dca.calendars.service import eligible_session_close, previous_eligible_eod
from quant_dca.canonical.validate import DiscontinuityEvidence, validate_ohlcv
from quant_dca.point_in_time.asof import latest_known, assert_pit_safe
from quant_dca.fx.conversion import FXService, FXQuoteUnavailable, StaleFXQuote
from quant_dca.features.price import compute_trailing_features
from quant_dca.features.registry import FeatureRegistry
from quant_dca.types import FeatureValue, QualityTier


@dataclass(frozen=True)
class ActionCoverage:
    security_id: str
    start_session: str
    end_session: str
    available_at: datetime
    source: str
    reference: str


@dataclass(frozen=True)
class VolumeEvidence:
    security_id: str
    session_date: str
    bar_revision_id: str
    volume: float
    volume_basis: str
    available_at: datetime
    source: str
    reference: str


@dataclass(frozen=True)
class PriceFeatureSnapshot:
    features: tuple[FeatureValue, ...]
    sessions: tuple[str, ...]
    raw_bars: tuple
    selected_actions: tuple
    action_coverage: ActionCoverage
    selected_volume_evidence: tuple[VolumeEvidence, ...]
    selected_fx_quotes: tuple
    selected_listings: tuple
    discontinuity_evidence: tuple
    usd_turnover: tuple[float | None, ...]
    adjusted_close: tuple[float | None, ...] = ()
    fx_max_age: timedelta | None = None
    price_basis: str = "split_and_dividend_total_return_feature"


def _evidence(row):
    assert_pit_safe([row.available_at], row.available_at)
    if not row.source.strip() or not row.reference.strip():
        raise ValueError("MISSING_VERIFICATION_PROVENANCE")


def build_price_features(prices, actions, *, security_id, exchange, as_of,
                         action_coverage, volume_evidence=(), fx_quotes=(), listing_history=(),
                         fx_max_age, discontinuity_evidence=()):
    """Select known vintages at the latest EOD; retain actual session gaps.

    Inputs arriving after that EOD enter the next EOD, even when as_of is later
    on the same evening. Liquidity currency requires a historical Security
    listing matching each raw bar; mixed currencies fail closed because no economic redenomination
    contract is supported. Same-day split plus dividend is also ambiguous.
    """
    cutoff = previous_eligible_eod(exchange, as_of)
    coverage = action_coverage
    _evidence(coverage)
    if coverage.security_id != security_id or coverage.available_at > cutoff:
        raise ValueError("ACTION_COVERAGE_UNAVAILABLE")
    groups = defaultdict(list)
    for r in prices:
        if r.security_id == security_id and r.available_at <= cutoff and r.session_close_at <= cutoff:
            groups[r.session_date].append(r)
    rows = sorted((latest_known(g,cutoff) for g in groups.values()), key=lambda r:r.session_date)
    if not rows:
        raise ValueError("NO_KNOWN_PRICE_HISTORY")
    if any(r.exchange != exchange or r.currency != rows[0].currency for r in rows):
        raise ValueError("INCONSISTENT_LISTING_HISTORY")
    if coverage.start_session > rows[0].session_date or coverage.end_session < cutoff.date().isoformat():
        raise ValueError("INCOMPLETE_ACTION_COVERAGE")
    action_groups = defaultdict(list)
    for a in actions:
        if a.security_id == security_id and a.available_at <= cutoff:
            action_groups[a.action_id].append(a)
    selected = tuple(latest_known(action_groups[k],cutoff) for k in sorted(action_groups))
    by_day = defaultdict(list)
    for a in selected:
        if a.announced_at is not None and a.available_at < a.announced_at:
            raise ValueError("AVAILABILITY_BEFORE_ANNOUNCEMENT")
        if a.exchange != exchange or a.currency != rows[0].currency or not a.action_id or not a.source or not a.revision_id or not isinstance(a.quality,QualityTier):
            raise ValueError("INVALID_ACTION_PROVENANCE")
        effective = eligible_session_close(exchange,date.fromisoformat(a.ex_date))
        if effective is None:
            raise ValueError("INVALID_ACTION_SESSION")
        if effective > cutoff or a.ex_date <= rows[0].session_date:
            continue
        if a.action_type not in {"split","dividend"}:
            raise ValueError("UNSUPPORTED_CORPORATE_ACTION")
        value = a.split_ratio if a.action_type == "split" else a.cash_amount
        if value is None or not math.isfinite(value) or value < 0 or (a.action_type == "split" and value == 0):
            raise ValueError("INVALID_ACTION_VALUE")
        by_day[a.ex_date].append(a)
    for group in by_day.values():
        if len({a.action_type for a in group}) > 1:
            raise ValueError("AMBIGUOUS_SAME_DAY_ACTION_ORDER")
    evidence = tuple(e for e in discontinuity_evidence if e.verified_at <= cutoff and e.security_id == security_id)
    action_evidence = [DiscontinuityEvidence(security_id,p.session_date,r.session_date,
        "corporate_action",coverage.source,coverage.reference,coverage.available_at)
        for p,r in zip(rows,rows[1:]) if r.session_date in by_day]
    validation = validate_ohlcv(rows,as_of=cutoff,discontinuity_evidence=(*evidence,*action_evidence),
                                allow_missing_volume=True)
    if validation.quarantined_rows:
        raise ValueError("INVALID_FEATURE_HISTORY:"+",".join(validation.reasons))
    sessions = []
    day = date.fromisoformat(rows[0].session_date)
    while day <= cutoff.date():
        closing = eligible_session_close(exchange,day)
        if closing is not None and closing <= cutoff:
            sessions.append(day.isoformat())
        day += timedelta(days=1)
    raw = {r.session_date:r for r in rows}
    fx = FXService([q for q in fx_quotes if q.available_at <= cutoff and q.fixing_at <= cutoff],max_age=fx_max_age)
    volume_groups = defaultdict(list)
    for v in volume_evidence:
        if v.security_id == security_id and v.available_at <= cutoff:
            _evidence(v)
            volume_groups[(v.session_date,v.bar_revision_id)].append(v)
    close, high, low, turnover = [],[],[],[]
    listings = tuple(listing_history)
    used_volumes, used_fx, used_listings = [],[],[]
    previous = None
    for session in sessions:
        r = raw.get(session)
        if r is None:
            close.append(None); high.append(None); low.append(None); turnover.append(None)
            previous = None
            continue
        scale = 1.
        if previous is not None:
            action_rows = by_day.get(session,())
            split = math.prod(a.split_ratio for a in action_rows if a.action_type == "split")
            dividend = sum(a.cash_amount for a in action_rows if a.action_type == "dividend")
            economic_close = close[-1]*(r.close*split+dividend)/previous.close
            scale = economic_close/r.close
        close.append(r.close*scale); high.append(r.high*scale); low.append(r.low*scale)
        previous = r
        candidates = volume_groups.get((session,r.revision_id),[])
        if len(set(candidates)) > 1:
            raise ValueError("AMBIGUOUS_VOLUME_EVIDENCE")
        v = candidates[0] if candidates else None
        dv = None
        known_listings = [s for s in listings if s.security_id == security_id and s.available_at <= r.session_close_at]
        listing_groups = defaultdict(list)
        for s in known_listings:
            listing_groups[s.active_from].append(s)
        current_listings = [latest_known(g,r.session_close_at) for g in listing_groups.values()]
        current_listings = [s for s in current_listings if s.active_from <= session and (s.active_to is None or session < s.active_to)]
        if len(current_listings) > 1:
            raise ValueError("AMBIGUOUS_HISTORICAL_CURRENCY")
        listing = current_listings[0] if current_listings else None
        if listing is not None and (listing.currency != r.currency or listing.exchange != exchange):
            raise ValueError("MISMATCHED_HISTORICAL_CURRENCY")
        if listing is not None and (not listing.source or not listing.revision_id or not isinstance(listing.quality,QualityTier)):
            raise ValueError("INVALID_LISTING_PROVENANCE")
        if listing is not None and v is not None and v.volume_basis == "original_share_units" and math.isfinite(v.volume) and v.volume >= 0:
            used_volumes.append(v)
            used_listings.append(listing)
            if r.currency == "USD":
                dv = r.close*v.volume
            else:
                try:
                    q = fx.resolve(r.currency,"USD",r.session_close_at)
                except (FXQuoteUnavailable,StaleFXQuote):
                    pass
                else:
                    if q.quote_type == "spot":
                        used_fx.append(q)
                        dv = r.close*v.volume*q.rate
        turnover.append(dv)
    outputs = compute_trailing_features(close,high,low,turnover)
    definitions = [d for d in FeatureRegistry.v1() if d.domain in {"price_trend","volatility_drawdown","volume_liquidity"}]
    if set(outputs) != {d.name for d in definitions}:
        raise ValueError("TASK2_REGISTRY_MISMATCH")
    inputs = [*rows,*selected,*used_volumes,*used_fx,*used_listings,coverage]
    max_input = max([r.available_at for r in inputs]+[e.verified_at for e in evidence])
    quality = max([r.quality for r in (*rows,*selected,*used_fx,*used_listings)],key=lambda q:list(QualityTier).index(q))
    features = tuple(FeatureValue(feature=d.name,entity_id=security_id,observation_date=sessions[-1],
        as_of=as_of,value=outputs[d.name],max_input_available_at=max_input,
        available_at=cutoff,quality=quality,source="verified_trailing_features",
        revision_id="features-v1",region=rows[0].region,exchange=exchange) for d in definitions)
    assert_pit_safe(features,as_of)
    return PriceFeatureSnapshot(features,tuple(sessions),tuple(rows),selected,coverage,
        tuple(used_volumes),tuple(used_fx),tuple(used_listings),evidence,tuple(turnover),tuple(close),fx_max_age)
