"""Immutable target-only storage; never imported by feature calculations."""
from dataclasses import dataclass
import json

import pandas as pd

from quant_dca.calendars.service import previous_eligible_eod
from quant_dca.fx.conversion import FXService
from quant_dca.snapshot_contracts import development_request,bounded_evidence,verify_evidence,evidence_value,UniverseEvidence
from quant_dca.storage.snapshots import SnapshotRef,write_snapshot
from quant_dca.targets.builder import build_targets
from quant_dca.types import Region


@dataclass(frozen=True, slots=True, kw_only=True)
class TargetInputs:
    prices: tuple
    actions: tuple
    listing_history: tuple
    action_coverage: tuple
    fx_quotes: tuple
    fx_max_age: object
    discontinuity_evidence: tuple = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class TargetRequest:
    security_id: str
    exchange: str
    region: Region
    signal_at: object
    inputs: TargetInputs
    source: SnapshotRef


def build_target_store(start,end,*,label_as_of,role,requests,universe,universe_source,root):
    """Build 20 named labels per signal, retaining horizon-specific censoring.

    Bounds and all per-request clocks are checked before source verification,
    histories or FX resolution. Only explicit materialized development inputs.
    """
    development_request(start,end,role)
    development_request(end,label_as_of,role)
    if type(requests) not in (tuple,list) or not requests:
        raise TypeError('MATERIALIZED_TARGET_REQUESTS_REQUIRED')
    keys=set()
    for request in requests:
        if type(request) is not TargetRequest:
            raise TypeError('TARGET_REQUEST_REQUIRED')
        development_request(request.signal_at,request.signal_at,role)
        if not start<=request.signal_at<=end:
            raise ValueError('SIGNAL_OUTSIDE_REQUEST')
        admitted=('XNYS','XNAS') if request.region is Region.US else ('XETR','XPAR')
        if request.region not in (Region.US,Region.EU) or request.exchange not in admitted:
            raise ValueError('EU_US_LISTED_SCOPE_REQUIRED')
        key=(request.security_id,request.signal_at)
        if key in keys:
            raise ValueError('DUPLICATE_TARGET_REQUEST')
        keys.add(key)
    if type(universe) is not UniverseEvidence:
        raise TypeError('UNIVERSE_EVIDENCE_REQUIRED')
    universe_hash=verify_evidence(universe,universe_source,as_of=label_as_of)
    index=universe.index()
    prepared=[]
    for request in requests:
        cutoff=previous_eligible_eod(request.exchange,request.signal_at)
        members={r.security_id:r for r in index.eligible_universe(cutoff,request.region)}
        if request.security_id not in members or members[request.security_id].exchange!=request.exchange:
            raise ValueError('INELIGIBLE_AT_SIGNAL_EOD')
        data=request.inputs
        if type(data) is not TargetInputs or any(type(getattr(data,name)) is not tuple for name in
                ('prices','actions','listing_history','action_coverage','fx_quotes','discontinuity_evidence')):
            raise TypeError('MATERIALIZED_TARGET_INPUTS_REQUIRED')
        bounded_evidence(data)
        source=verify_evidence(data,request.source,as_of=label_as_of)
        prepared.append((request,source))
    records=[]; sources=[universe_hash]
    for request,source in prepared:
        data=request.inputs
        result=build_targets(data.prices,data.actions,security_id=request.security_id,exchange=request.exchange,
            signal_at=request.signal_at,label_as_of=label_as_of,action_coverage=data.action_coverage,
            listing_history=data.listing_history,fx_service=FXService(data.fx_quotes,max_age=data.fx_max_age),
            discontinuity_evidence=data.discontinuity_evidence)
        sources.append(source)
        for horizon in result.horizons:
            prefixes=('return','direction','executable_min_return','better_entry') if horizon.horizon in (5,20) else ('return','direction')
            provenance=json.dumps(evidence_value(horizon),sort_keys=True,separators=(',',':'))
            for prefix in prefixes:
                for currency in ('local','huf'):
                    value=getattr(horizon,f'{prefix}_{currency}')
                    records.append(dict(entity_id=request.security_id,target=f'{prefix}_{horizon.horizon}d_{currency}',
                        value=None if value is None else float(value),horizon=horizon.horizon,currency_basis=currency,
                        signal_at=request.signal_at,baseline_open_at=result.baseline_open_at,label_as_of=label_as_of,
                        target_end_timestamp=horizon.target_end_timestamp,censor_reason=horizon.censor_reason,
                        source_snapshot=source,universe_snapshot=universe_hash,economic_provenance_json=provenance,
                        role=str(role),schema_status='software_contract_not_research_admission'))
    return write_snapshot(pd.DataFrame(records),'targets',label_as_of,root=root,source_hashes=sources,schema_version='targets-v1')
