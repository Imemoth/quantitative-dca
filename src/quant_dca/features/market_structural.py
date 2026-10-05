"""Ten remaining V1 producers. Boundaries are software candidates, not selected policy.

Source/unit declarations are caller evidence, never proof of real provider truth.
Price adjustment reuses Task2's exact computed closes; no second action formula.
"""
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
import math
import statistics

from quant_dca.calendars.service import eligible_session_close, previous_eligible_eod
from quant_dca.features.history import PriceFeatureSnapshot
from quant_dca.features.fundamentals import select_report
from quant_dca.features.relative import _select_classifications
from quant_dca.features.registry import FeatureRegistry
from quant_dca.features.valuation import _raw_valuation
from quant_dca.fx.conversion import FXService, FXQuoteUnavailable, StaleFXQuote
from quant_dca.point_in_time.asof import latest_known, assert_pit_safe
from quant_dca.snapshot_contracts import development_request, bounded_evidence
from quant_dca.types import FeatureValue, QualityTier, Region

SECTORS = frozenset(('Energy','Materials','Industrials','Consumer Discretionary','Consumer Staples',
    'Health Care','Financials','Technology','Information Technology','Communication Services','Utilities','Real Estate'))


@dataclass(frozen=True, slots=True, kw_only=True)
class StructuralConfig:
    sector_codes: tuple[tuple[str, int], ...]
    cap_usd_edges: tuple[float, ...] = (2e9, 10e9, 200e9)
    beta_edges: tuple[float, ...] = (.8, 1.2)
    version: str = 'structural-software-candidate-v1'

    def __post_init__(self):
        if not self.version or type(self.sector_codes) is not tuple:
            raise ValueError('EXPLICIT_STRUCTURAL_CONFIG_REQUIRED')
        labels, codes = zip(*self.sector_codes) if self.sector_codes else ((),())
        if not labels or len(set(labels)) != len(labels) or len(set(codes)) != len(codes):
            raise ValueError('UNIQUE_SECTOR_CODES_REQUIRED')
        if not set(labels) <= SECTORS or any(type(code) is not int or code < 0 for code in codes):
            raise ValueError('CONTROLLED_ECONOMIC_SECTORS_REQUIRED')
        for edges in (self.cap_usd_edges, self.beta_edges):
            if type(edges) is not tuple or not edges or any(type(x) not in (int,float) or not math.isfinite(x) for x in edges) or tuple(sorted(set(edges))) != edges:
                raise ValueError('ORDERED_FINITE_BUCKET_EDGES_REQUIRED')
        if self.cap_usd_edges[0] <= 0:
            raise ValueError('POSITIVE_CAP_EDGES_REQUIRED')


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketBinding:
    region: Region
    broad_id: str
    broad_exchange: str
    sector_id: str
    sector_exchange: str
    sector_label: str
    vix_series: str
    vix_exchange: str
    vix_source: str
    broad_source: str
    sector_source: str


@dataclass(frozen=True, slots=True)
class MarketStructuralSnapshot:
    features: tuple[FeatureValue, ...]
    beta: float | None
    config: StructuralConfig
    binding: MarketBinding
    evidence: tuple
    fx_max_age: timedelta | None


def _price(snapshot, entity, exchange, region, prediction):
    if type(snapshot) is not PriceFeatureSnapshot or not snapshot.features:
        raise TypeError('EVIDENCED_PRICE_SNAPSHOT_REQUIRED')
    if snapshot.price_basis != 'split_and_dividend_total_return_feature':
        raise ValueError('ADJUSTED_PRICE_BASIS_REQUIRED')
    cutoff = previous_eligible_eod(exchange, prediction)
    for row in snapshot.features:
        if row.entity_id != entity or row.exchange != exchange or row.region is not region or row.as_of != prediction or row.available_at != cutoff:
            raise ValueError('BENCHMARK_BINDING_MISMATCH')
    assert_pit_safe(snapshot.features, prediction)
    return {r.feature:r.value for r in snapshot.features}


def _beta(stock, market):
    if len(stock.sessions) < 253 or len(market.sessions) < 253:
        return None
    if stock.sessions[-253:] != market.sessions[-253:]:
        return None
    left, right = stock.adjusted_close[-253:], market.adjusted_close[-253:]
    if len(left) != 253 or len(right) != 253 or any(x is None or not math.isfinite(x) or x <= 0 for x in (*left,*right)):
        return None
    a = [left[i]/left[i-1]-1 for i in range(1,253)]
    b = [right[i]/right[i-1]-1 for i in range(1,253)]
    variance = statistics.variance(b)
    return None if variance == 0 else statistics.covariance(a,b)/variance


def build_market_structural_features(*, as_of, role, security, stock, broad, sector,
        classifications, reports, valuation_prices, vix, fx_quotes, fx_max_age,
        config, binding):
    development_request(as_of, as_of, role)
    if type(config) is not StructuralConfig or type(binding) is not MarketBinding:
        raise TypeError('EXPLICIT_MARKET_STRUCTURAL_CONFIG_REQUIRED')
    exchanges = ('XNYS','XNAS') if security.region is Region.US else ('XETR','XPAR')
    if security.region not in (Region.US, Region.EU) or security.exchange not in exchanges or binding.region is not security.region:
        raise ValueError('EU_US_LISTED_SCOPE_REQUIRED')
    if binding.broad_exchange not in exchanges or binding.sector_exchange not in exchanges:
        raise ValueError('BENCHMARK_REGION_MISMATCH')
    collections = (classifications,reports,valuation_prices,vix,fx_quotes)
    if any(type(items) not in (tuple,list) for items in collections):
        raise TypeError('MATERIALIZED_MARKET_INPUTS_REQUIRED')
    bounded_evidence((security,stock,broad,sector,*collections))
    cutoff = previous_eligible_eod(security.exchange, as_of)
    assert_pit_safe((security,),cutoff)
    if not security.active_from <= cutoff.date().isoformat() or (security.active_to is not None and security.active_to <= cutoff.date().isoformat()):
        raise ValueError('INACTIVE_SECURITY')
    _price(stock, security.security_id, security.exchange, security.region, as_of)
    bv = _price(broad,binding.broad_id,binding.broad_exchange,binding.region,as_of)
    sv = _price(sector,binding.sector_id,binding.sector_exchange,binding.region,as_of)
    for snapshot, source in ((broad,binding.broad_source),(sector,binding.sector_source)):
        if not source or any(r.source != source for r in snapshot.raw_bars):
            raise ValueError("BENCHMARK_SOURCE_MISMATCH")
    if any(r.currency != security.currency for r in stock.raw_bars):
        raise ValueError("STOCK_LISTING_CURRENCY_MISMATCH")
    if any(r.available_at > cutoff for r in (*broad.features,*sector.features)):
        raise ValueError('BENCHMARK_AFTER_SECURITY_EOD')
    selected_class = _select_classifications(classifications,cutoff=cutoff,eligible_ids=frozenset((security.security_id,))).get(security.security_id)
    label = None if selected_class is None else selected_class.sector_id
    if label is not None and label != binding.sector_label:
        raise ValueError('SECTOR_BENCHMARK_BINDING_MISMATCH')
    if label is not None and label not in dict(config.sector_codes):
        raise ValueError('UNMAPPED_ECONOMIC_SECTOR')
    groups = defaultdict(list)
    for row in vix:
        if row.series != binding.vix_series:
            continue
        if row.unit != 'index_points' or row.region is not Region.GLOBAL or row.exchange != binding.vix_exchange or row.source != binding.vix_source:
            raise ValueError('VIX_SOURCE_UNIT_CALENDAR_MISMATCH')
        if row.available_at <= cutoff:
            groups[row.observation_date].append(row)
    known = {day:latest_known(rows,cutoff) for day,rows in groups.items()}
    latest_source_close = previous_eligible_eod(binding.vix_exchange,cutoff)
    if any(day > latest_source_close.date().isoformat() for day in known):
        raise ValueError('PIT_FUTURE_VIX_OBSERVATION')
    end = (eligible_session_close(binding.vix_exchange,date.fromisoformat(max(known)))
           if known else latest_source_close)
    if end is None:
        raise ValueError('VIX_SESSION_MISMATCH')
    sessions = [end]
    for _ in range(42):
        sessions.append(previous_eligible_eod(binding.vix_exchange,sessions[-1]-timedelta(microseconds=1)))
    sessions.reverse()
    picked = [known.get(t.date().isoformat()) for t in sessions]
    for instant,row in zip(sessions,picked):
        if row is not None:
            if eligible_session_close(binding.vix_exchange,date.fromisoformat(row.observation_date)) != instant:
                raise ValueError('VIX_SESSION_MISMATCH')
            assert_pit_safe((row,),cutoff)
            if row.value is not None and (not isinstance(row.value,(int,float)) or isinstance(row.value,bool) or not math.isfinite(row.value) or row.value < 0):
                raise ValueError('INVALID_VIX_LEVEL')
    level = None if picked[-1] is None else picked[-1].value
    acceleration = None
    if all(r is not None and r.value is not None for r in picked):
        acceleration = picked[-1].value - 2*picked[-21].value + picked[-41].value
    report = select_report(reports,security.security_id,cutoff)
    candidates = [r for r in valuation_prices if r.security_id == security.security_id and r.session_close_at == cutoff and r.available_at <= cutoff]
    price = latest_known(candidates,cutoff) if candidates else None
    cap, quote = None, None
    if price is not None:
        if price.price_basis != 'unadjusted' or price.per_share_basis != 'unadjusted':
            raise ValueError('CAP_UNADJUSTED_SHARE_PRICE_REQUIRED')
        if price.currency != security.currency or report.currency != security.currency or price.region is not security.region or price.exchange != security.exchange or report.region is not security.region or report.exchange != security.exchange:
            raise ValueError('CAP_LISTING_MISMATCH')
        _raw_valuation(report,price,label)  # established currency/share basis contract
        shares = report.values.get('diluted_shares')
        if shares is not None and math.isfinite(shares) and shares > 0:
            cap = price.close * shares
            if price.currency != 'USD':
                try:
                    quote = FXService(fx_quotes,max_age=fx_max_age).resolve(price.currency,'USD',cutoff)
                except (FXQuoteUnavailable,StaleFXQuote):
                    cap = None
                else:
                    if quote.quote_type != 'spot':
                        raise ValueError('CAP_SPOT_FX_REQUIRED')
                    cap *= quote.rate
        if price.quality is QualityTier.C:
            raise ValueError('QUALITY_BELOW_FLOOR:market_cap')
    beta = _beta(stock,broad)
    values = {f'broad_market_momentum_{h}d_raw':bv[f'return_{h}d_raw'] for h in (20,60)}
    values.update({f'sector_momentum_{h}d_raw':sv[f'return_{h}d_raw'] if label else None for h in (20,60)})
    values.update(vix_level_raw=level,vix_acceleration_raw=acceleration,
        region_category=0 if security.region is Region.US else 1,
        sector_category=None if label is None else dict(config.sector_codes)[label],
        market_cap_bucket=None if cap is None else bisect_right(config.cap_usd_edges,cap),
        beta_bucket=None if beta is None else bisect_right(config.beta_edges,beta))
    evidence = (security,stock,broad,sector,selected_class,report,price,quote,*(r for r in picked if r is not None))
    dependencies = {
        'region_category':(security,),
        'sector_category':tuple(r for r in (security,selected_class) if r is not None),
        'market_cap_bucket':tuple(r for r in (security,report,price,quote) if r is not None),
        'beta_bucket':(security,*stock.features,*broad.features),
        'vix_level_raw':tuple(r for r in (security,picked[-1]) if r is not None),
        'vix_acceleration_raw':(security,*(r for r in picked if r is not None)),
    }
    for h in (20,60):
        dependencies[f'broad_market_momentum_{h}d_raw']=(security,*broad.features)
        dependencies[f'sector_momentum_{h}d_raw']=(security,*sector.features,*(() if selected_class is None else (selected_class,)))
    outputs=[]
    for definition in FeatureRegistry.v1():
        if definition.name not in values:
            continue
        inputs=dependencies[definition.name]
        quality=max((r.quality for r in inputs),key=lambda q:list(QualityTier).index(q))
        max_input=max(max(r.available_at,getattr(r,'max_input_available_at',r.available_at)) for r in inputs)
        outputs.append(FeatureValue(feature=definition.name,entity_id=security.security_id,observation_date=cutoff.date().isoformat(),
            as_of=as_of,value=values[definition.name],max_input_available_at=max_input,available_at=cutoff,
            quality=quality,source='market_structural_candidate',revision_id=config.version,
            region=security.region,exchange=security.exchange))
    outputs=tuple(outputs)
    assert_pit_safe(outputs,as_of)
    return MarketStructuralSnapshot(outputs,beta,config,binding,evidence,fx_max_age)
