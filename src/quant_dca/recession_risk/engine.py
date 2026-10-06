"""PIT evidence selection for regional diagnostics. Never fits or calls a model."""
from collections import defaultdict
from datetime import date,timezone
import math
from quant_dca.calendars.service import previous_eligible_eod
from quant_dca.point_in_time.asof import latest_known,assert_pit_safe
from quant_dca.snapshot_contracts import development_request,bounded_evidence,evidence_frame,verify_evidence
from quant_dca.storage.snapshots import snapshot_hash
from quant_dca.types import Region,QualityTier
from .registry import DiagnosticConfig,text
from .evidence import InputEvidence,AdmissionStatus
from .contracts import EvidenceReference,InputMeasure,PillarState,MacroRiskSnapshot
from .rules import evaluate_rules

QUALITY_ORDER={QualityTier.A:0,QualityTier.B:1,QualityTier.C:2}


def validate_selected(evidence,definition,cutoff):
    """Hard gate for a selected canonical observation and scoped admission attestation."""
    row=evidence.observation; a=evidence.admission
    assert_pit_safe((row,),cutoff)
    if row.series != definition.series:
        raise ValueError('SERIES_MISMATCH')
    if row.vintage_start is not None and date.fromisoformat(row.vintage_start)>row.available_at.date():
        raise ValueError('VINTAGE_AFTER_AVAILABILITY')
    if row.entity_id is not None:raise ValueError('DIRECT_IDENTITY_PROHIBITED')
    if date.fromisoformat(row.observation_date)>cutoff.date():raise ValueError('FUTURE_OBSERVATION')
    if row.region is not definition.region:raise ValueError('REGION_MISMATCH')
    if row.unit!=definition.unit or row.currency!=definition.currency:raise ValueError('UNIT_OR_CURRENCY_MISMATCH')
    if row.value is not None and (type(row.value) not in (int,float) or not math.isfinite(row.value)):
        raise ValueError('NONFINITE_OR_INVALID_VALUE')
    if (a.source!=row.source or a.series!=definition.series or a.region is not definition.region
        or a.monetary_jurisdiction!=definition.monetary_jurisdiction or a.unit!=definition.unit
        or a.currency!=definition.currency or not a.start<=row.observation_date<=a.end
        or a.source_snapshot_hash!=evidence.snapshot.sha256
        or (a.status is AdmissionStatus.ADMITTED and a.quality is not row.quality)):
        raise ValueError('ADMISSION_BINDING_MISMATCH')
    if a.status is AdmissionStatus.ADMITTED and a.quality is QualityTier.A and row.published_at is None:
        raise ValueError('TIER_A_PUBLICATION_REQUIRED')
    verify_evidence(row,evidence.snapshot,as_of=cutoff)


def _measure(definition,candidates,cutoff):
    grouped=defaultdict(list)
    for item in candidates:grouped[item.observation.observation_date].append(item)
    known=[]
    for period,items in grouped.items():
        try:row=latest_known([i.observation for i in items],cutoff)
        except LookupError:continue
        selected=[i for i in items if i.observation==row]
        # Conflicting attestations must never be resolved by input order.
        if any(i.admission!=selected[0].admission or i.snapshot.sha256!=selected[0].snapshot.sha256 for i in selected[1:]):
            raise ValueError('AMBIGUOUS_ADMISSION')
        known.append(selected[0])
    if not known:
        return InputMeasure(definition.name,definition.pillar,None,definition.unit,'MISSING',None,0,0,None)
    selected=max(known,key=lambda e:e.observation.observation_date)
    validate_selected(selected,definition,cutoff)
    row=selected.observation;a=selected.admission
    ref=EvidenceReference(definition.name,row.source,row.revision_id,row.observation_date,row.available_at,
        row.published_at,row.revised_at,selected.snapshot.sha256,snapshot_hash(evidence_frame(a)),a.evidence_refs)
    age=(cutoff.date()-date.fromisoformat(row.observation_date)).days
    freshness=max(0.0,1-age/definition.max_age_days)
    certainty=1.0 if row.published_at is not None else 0.5
    status=a.status.value
    if a.status is AdmissionStatus.ADMITTED:
        if QUALITY_ORDER[a.quality]>QUALITY_ORDER[definition.quality_floor]:status='QUALITY_BELOW_FLOOR'
        elif age>=definition.max_age_days:status='STALE'
        elif row.value is None:status='MISSING_VALUE'
    usable=status=='ADMITTED'
    return InputMeasure(definition.name,definition.pillar,float(row.value) if usable else None,
        definition.unit,status,a.quality if a.status is AdmissionStatus.ADMITTED else None,
        freshness,certainty,ref)


def build_snapshot(*,as_of,region,monetary_jurisdiction,evidence,config,role='diagnostic'):
    """Read-only development diagnostic; evidence can include later development vintages.

    Later known rows are excluded, selected future rows hard-fail, and any financial
    clock outside 2010–2023 fails. No data iterable is touched before request guards.
    Admission is a caller-supplied reviewed attestation, not an automatic provider audit.
    """
    if role!='diagnostic':raise ValueError('DIAGNOSTIC_ROLE_REQUIRED')
    development_request(as_of,as_of,'train')
    if not isinstance(config,DiagnosticConfig):raise TypeError('DIAGNOSTIC_CONFIG_REQUIRED')
    if region not in (Region.US,Region.EU) or not isinstance(region,Region):raise ValueError('UNSUPPORTED_REGION')
    text(monetary_jurisdiction)
    prediction=as_of.astimezone(timezone.utc)
    context=config.context(region,monetary_jurisdiction)
    definitions=tuple(i for i in config.inputs if i.region is region and (
        context is None or i.monetary_jurisdiction==monetary_jurisdiction))
    cutoff=None if context is None else previous_eligible_eod(context.exchange,prediction)
    if context is None:
        measures=tuple(InputMeasure(i.name,i.pillar,None,i.unit,'UNSUPPORTED_JURISDICTION',None,0,0,None) for i in definitions)
    else:
        materialized=tuple(evidence)
        for item in materialized:
            if not isinstance(item,InputEvidence):raise TypeError('CANONICAL_EVIDENCE_REQUIRED')
            bounded_evidence(item.observation)
        measures=tuple(_measure(i,[e for e in materialized if e.observation.series==i.series],cutoff) for i in definitions)
    usable=tuple(m for m in measures if m.status=='ADMITTED')
    count=len(measures);completeness=len(usable)/count if count else 0.0
    critical={i.name for i in definitions if i.critical}
    critical_completeness=sum(m.name in critical for m in usable)/len(critical) if critical else 0.0
    weights=dict(config.quality_weights)
    confidence=(sum(weights[m.quality.value]*m.freshness*m.publication_certainty for m in usable)/count if count else 0.0)*critical_completeness
    refs=tuple(m.evidence for m in measures if m.evidence is not None)
    sources=tuple(sorted({r.source_snapshot_hash for r in refs}))
    pillars=[]
    for p in config.pillars:
        pm=tuple(m for m in measures if m.pillar==p.name); n=sum(m.status=='ADMITTED' for m in pm)
        state='COMPLETE_EVIDENCE' if pm and n==len(pm) else 'PARTIAL_EVIDENCE' if n else 'INSUFFICIENT_EVIDENCE'
        pillars.append(PillarState(p.name,'UNKNOWN',state,'RULES_NOT_CONFIGURED' if state=='COMPLETE_EVIDENCE' else state))
    admission='COMPLETE_EVIDENCE' if count and len(usable)==count else 'PARTIAL_EVIDENCE' if usable else 'INSUFFICIENT_EVIDENCE'
    pillars,drivers,dominant,secondary=evaluate_rules(tuple(pillars),measures,critical_completeness,config)
    return MacroRiskSnapshot(prediction,cutoff,region,monetary_jurisdiction,pillars,measures,refs,
        admission,max((m.quality for m in usable),key=QUALITY_ORDER.__getitem__,default=None),
        dominant,secondary,completeness,critical_completeness,confidence,drivers,
        max((r.available_at for r in refs),default=None),tuple(sorted({r.published_at for r in refs if r.published_at is not None})),
        config.sha256,sources,('UNSUPPORTED_JURISDICTION',) if context is None else (('DIAGNOSTIC_ONLY','RULES_NOT_CONFIGURED') if not config.rules else ('DIAGNOSTIC_ONLY','UNVALIDATED_RULES')))
