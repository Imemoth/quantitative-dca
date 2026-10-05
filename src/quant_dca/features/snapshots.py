"""Assemble evidenced producers into immutable, predictor-only V1 snapshots.

Hashes establish exact declared evidence identity, not provider admission or truth.
Administrative entity keys live only in long storage rows and join_keys.
"""
from dataclasses import dataclass
import math

import pandas as pd

from quant_dca.calendars.service import previous_eligible_eod
from quant_dca.features.history import PriceFeatureSnapshot
from quant_dca.features.relative import RelativeFeatureSnapshot
from quant_dca.features.fundamentals import FundamentalFeatureSnapshot
from quant_dca.features.valuation import ValuationFeatureSnapshot
from quant_dca.features.macro import MacroFeatureSnapshot
from quant_dca.features.events import EventFeatureSnapshot
from quant_dca.features.market_structural import MarketStructuralSnapshot
from quant_dca.features.registry import FeatureRegistry
from quant_dca.lineage import FeatureLineage
from quant_dca.point_in_time.asof import assert_pit_safe
from quant_dca.snapshot_contracts import development_request, bounded_evidence, verify_evidence, UniverseEvidence, assert_selected_evidence_pit
from quant_dca.storage.snapshots import SnapshotRef, write_snapshot
from quant_dca.types import QualityTier, Region

PRODUCER_DOMAINS = {
    PriceFeatureSnapshot: frozenset(('price_trend','volatility_drawdown','volume_liquidity')),
    RelativeFeatureSnapshot: frozenset(('relative_strength',)),
    FundamentalFeatureSnapshot: frozenset(('fundamentals',)),
    ValuationFeatureSnapshot: frozenset(('valuation',)),
    MacroFeatureSnapshot: frozenset(('macro',)),
    EventFeatureSnapshot: frozenset(('event_calendar',)),
    MarketStructuralSnapshot: frozenset(('market_cross_asset','structural')),
}


@dataclass(frozen=True, slots=True)
class ProducerBundle:
    snapshot: object
    source: SnapshotRef


@dataclass(frozen=True, slots=True)
class FeatureSnapshot:
    reference: SnapshotRef
    predictors: pd.DataFrame
    structural_missing: pd.DataFrame
    join_keys: tuple[tuple[str, object], ...]
    regime_status: str


def build_feature_snapshot(as_of, registry_version, *, role, fold_id, security_id,
        region, exchange, bundles, universe, universe_source, root, regimes=None):
    development_request(as_of,as_of,role)
    if not isinstance(fold_id,str) or not fold_id.strip():
        raise ValueError('FOLD_ID_REQUIRED')
    if regimes is not None:
        from quant_dca.regimes.integration import validate_regime_snapshot
        validate_regime_snapshot(regimes.snapshot,as_of=as_of,role=role,fold_id=fold_id,region=region)
    registry = FeatureRegistry.v1()
    if registry_version != registry.version:
        raise ValueError('REGISTRY_VERSION_MISMATCH')
    admitted = ('XNYS','XNAS') if region is Region.US else ('XETR','XPAR')
    if region not in (Region.US,Region.EU) or exchange not in admitted:
        raise ValueError('EU_US_LISTED_SCOPE_REQUIRED')
    if type(bundles) not in (tuple,list) or type(universe) is not UniverseEvidence:
        raise TypeError('MATERIALIZED_PRODUCER_UNIVERSE_REQUIRED')
    cutoff = previous_eligible_eod(exchange,as_of)
    bounded_evidence(universe)
    universe_hash = verify_evidence(universe,universe_source,as_of=as_of)
    eligible = {r.security_id:r for r in universe.index().eligible_universe(cutoff,region)}
    security = eligible.get(security_id)
    if security is None or security.exchange != exchange:
        raise ValueError('INELIGIBLE_AT_FEATURE_EOD')
    kinds = [type(b.snapshot) for b in bundles if type(b) is ProducerBundle]
    if len(kinds) != len(bundles) or len(kinds) != len(PRODUCER_DOMAINS) or set(kinds) != set(PRODUCER_DOMAINS):
        raise ValueError('EXACT_PRODUCER_COVERAGE_REQUIRED')
    records, lineage, sources = [],[],[universe_hash]
    for bundle in bundles:
        snapshot = bundle.snapshot
        if type(snapshot) in (RelativeFeatureSnapshot,ValuationFeatureSnapshot):
            cohort=snapshot.eligible_security_ids
            if len(cohort)!=len(eligible) or set(cohort)!=set(eligible):
                raise ValueError("PRODUCER_UNIVERSE_COHORT_MISMATCH")
        bounded_evidence(snapshot)
        assert_selected_evidence_pit(snapshot,cutoff)
        source_hash = verify_evidence(snapshot,bundle.source,as_of=as_of)
        sources.append(source_hash)
        definitions = {d.name:d for d in registry if d.domain in PRODUCER_DOMAINS[type(snapshot)]}
        if len(snapshot.features) != len(definitions) or {r.feature for r in snapshot.features} != set(definitions):
            raise ValueError('EXACT_FEATURE_COVERAGE_REQUIRED')
        assert_pit_safe(snapshot.features,as_of)
        masks = getattr(snapshot,'applicability',{})
        for row in snapshot.features:
            definition = definitions[row.feature]
            if row.entity_id != security_id or row.region is not region or row.exchange != exchange or row.as_of != as_of or row.available_at != cutoff:
                raise ValueError('FEATURE_ENTITY_CLOCK_MISMATCH')
            if not isinstance(row.quality,QualityTier) or list(QualityTier).index(row.quality) > list(QualityTier).index(definition.quality_floor):
                raise ValueError('QUALITY_BELOW_REGISTRY_FLOOR')
            if row.value is not None and (isinstance(row.value,bool) or not isinstance(row.value,(int,float)) or not math.isfinite(row.value)):
                raise ValueError('INVALID_FEATURE_VALUE')
            applicable = masks.get(row.feature,masks.get(row.feature.removesuffix('_raw'),True))
            structural = not applicable
            if structural and row.value is not None:
                raise ValueError('STRUCTURAL_MISSING_VALUE_PRESENT')
            records.append(dict(entity_id=security_id,feature=row.feature,value=row.value,structural_missing=structural,
                as_of=as_of,available_at=row.available_at,max_input_available_at=row.max_input_available_at,
                quality=row.quality.value,registry_version=registry_version,fold_id=fold_id,role=str(role),
                producer=type(snapshot).__name__,source_snapshot=source_hash))
            lineage.append(FeatureLineage(feature=row.feature,provider='evidenced_producer',source_snapshot=source_hash,
                transform=definition.transform,availability_rule=definition.availability_rule,
                source_observations=(type(snapshot).__name__,row.observation_date,row.revision_id),
                source_timestamps=(row.max_input_available_at,row.available_at),universe_snapshot=universe_hash))
    names = list(registry.names())
    status = 'base_only_incomplete_regime_integration'
    if regimes is not None:
        from quant_dca.regimes.integration import append_regime_records
        extra, extra_lineage, extra_source = append_regime_records(regimes,as_of=as_of,role=role,
            fold_id=fold_id,region=region,base_records=records,universe_hash=universe_hash,security_id=security_id)
        records.extend(extra); lineage.extend(extra_lineage); sources.append(extra_source)
        names.extend(r['feature'] for r in extra)
        status = 'complete_software_candidate_not_research_selected'
    if not registry.panel_budget.final_min <= len(names) <= registry.panel_budget.final_max:
        raise ValueError('FEATURE_PANEL_BUDGET')
    reference = write_snapshot(pd.DataFrame(records),'features',as_of,root=root,source_hashes=sources,
        schema_version=registry_version,lineage=lineage)
    by_name = {r['feature']:r for r in records}
    predictors = pd.DataFrame([{name:by_name[name]['value'] for name in names}])
    missing = pd.DataFrame([{name:by_name[name]['structural_missing'] for name in names}])
    return FeatureSnapshot(reference,predictors,missing,((security_id,as_of),),status)
