"""Optional ex-ante regime feature integration with full candidate fit identity.

In-sample Task9 diagnostics are not accepted as earlier predictive features.
Only a fit completed no later than this request may supply model columns.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
import math

from quant_dca.calendars.service import previous_eligible_eod
from quant_dca.lineage import FeatureLineage
from quant_dca.regimes.interpretable import InterpretableRegimeModel, RegimePrediction, STATES
from quant_dca.regimes.unsupervised import FitProvenance, SIGNAL_UNITS, predict_state_proba
from quant_dca.snapshot_contracts import development_request, bounded_evidence, verify_evidence
from quant_dca.types import FeatureValue, QualityTier, Region


@dataclass(frozen=True, slots=True)
class RegimeFeatureSnapshot:
    as_of: object
    role: object
    fold_id: str
    region: Region
    interpreted: RegimePrediction
    fit: FitProvenance
    probabilities: tuple[float, ...]
    evidence: tuple
    sequence_policy: str
    parameter_scope: str


def _selected_dependencies(interpreted, fit, as_of, prediction_evidence=None):
    """Reapply Task8/9 metadata checks before numeric prediction or source reads.

    Historical observations keep their original prior-EOD PIT cutoff; training
    observations keep each original row.as_of within the fitted train bounds.
    A stored pit_validated flag is evidence metadata, not a validation bypass.
    """
    development_request(fit.train_bounds[0],fit.train_bounds[1],'train')
    if fit.train_bounds[1] > as_of:
        raise ValueError('REGIME_FIT_AFTER_PREDICTION')
    if not interpreted.pit_validated or interpreted.prediction_timestamp != as_of:
        raise ValueError('PIT_VALIDATED_REGIME_REQUIRED')
    current,prior=interpreted.current_eod,interpreted.prior_eod
    development_request(prior,current,'train')
    if (current != previous_eligible_eod(interpreted.benchmark_exchange,as_of)
            or prior != previous_eligible_eod(interpreted.benchmark_exchange,current-timedelta(microseconds=1))):
        raise ValueError('PIT_REGIME_BRANCH_CUTOFF_MISMATCH')
    if fit.region is not interpreted.region or fit.benchmark_exchange != interpreted.benchmark_exchange:
        raise ValueError('REGIME_SOURCE_CALENDAR_MISMATCH')
    if type(interpreted.evidence) is not tuple or type(fit.training_evidence) is not tuple:
        raise TypeError('MATERIALIZED_REGIME_EVIDENCE_REQUIRED')
    groups=defaultdict(list)
    for row in interpreted.evidence:
        if not isinstance(row,FeatureValue) or row.as_of not in (current,prior):
            raise ValueError('PIT_REGIME_EVIDENCE_CUTOFF_MISMATCH')
        groups[row.as_of].append(row)
    current_rows=InterpretableRegimeModel._snapshot(groups[current],current,interpreted.region)
    history_rows=InterpretableRegimeModel._snapshot(groups[prior],prior,interpreted.region)
    train_groups=defaultdict(list)
    for row in fit.training_evidence:
        if not isinstance(row,FeatureValue) or not fit.train_bounds[0] <= row.as_of <= fit.train_bounds[1]:
            raise ValueError('PIT_TRAIN_EVIDENCE_OUTSIDE_FIT_BOUNDS')
        if row.as_of != previous_eligible_eod(fit.benchmark_exchange,row.as_of):
            raise ValueError('PIT_TRAIN_EVIDENCE_NOT_EOD')
        train_groups[row.as_of].append(row)
    if not train_groups:
        raise ValueError('PIT_TRAIN_EVIDENCE_REQUIRED')
    training=tuple(row for at,rows in train_groups.items()
        for row in InterpretableRegimeModel._snapshot(rows,at,fit.region))
    actual=()
    if prediction_evidence is not None:
        if type(prediction_evidence) is not tuple:
            raise TypeError('MATERIALIZED_REGIME_EVIDENCE_REQUIRED')
        actual=InterpretableRegimeModel._snapshot(prediction_evidence,as_of,fit.region)
    return (*current_rows,*history_rows),(*actual,*training)


def validate_regime_snapshot(snapshot, *, as_of, role, fold_id, region):
    """Preflight staged metadata before any immutable source or value is read."""
    development_request(as_of,as_of,role)
    if type(snapshot) is not RegimeFeatureSnapshot:
        raise TypeError('EVIDENCED_REGIME_SNAPSHOT_REQUIRED')
    if snapshot.fold_id != fold_id or snapshot.fit.fold_id != fold_id:
        raise ValueError('REGIME_FOLD_MISMATCH')
    if (snapshot.as_of!=as_of or snapshot.role!=role or snapshot.region is not region
            or snapshot.interpreted.partition_role!=role or snapshot.interpreted.region is not region):
        raise ValueError('REGIME_REQUEST_MISMATCH')
    bounded_evidence(snapshot)
    return _selected_dependencies(snapshot.interpreted,snapshot.fit,as_of,snapshot.evidence)


def _dependency_summary(rows, *, earliest=None):
    # _snapshot has validated every tier and actual availability/publication/
    # revision/input clock. Include every clock, not only declared max_input.
    clocks=[stamp for row in rows for stamp in
        (row.available_at,row.published_at,row.revised_at,row.max_input_available_at) if stamp is not None]
    if earliest is not None:
        clocks.append(earliest)
    latest=max(clocks)
    quality=max((row.quality for row in rows),key=lambda tier:list(QualityTier).index(tier))
    return latest,quality


def build_regime_features(*, as_of, role, fold_id, interpreted, model, partition):
    development_request(as_of,as_of,role)
    fit=model.provenance
    if fit.fold_id != fold_id or partition.fold_id != fold_id:
        raise ValueError('REGIME_FOLD_MISMATCH')
    if fit.train_bounds[1] > as_of:
        raise ValueError('REGIME_FIT_AFTER_PREDICTION')
    if not interpreted.pit_validated or interpreted.prediction_timestamp != as_of:
        raise ValueError('PIT_VALIDATED_REGIME_REQUIRED')
    if interpreted.partition_role != role or partition.role != role or partition.region is not interpreted.region or fit.region is not interpreted.region:
        raise ValueError('REGIME_ROLE_REGION_MISMATCH')
    if interpreted.benchmark_exchange != partition.benchmark_exchange:
        raise ValueError('REGIME_SOURCE_CALENDAR_MISMATCH')
    if partition.starts_at != as_of or partition.ends_at != as_of:
        raise ValueError('SINGLE_PREDICTION_SNAPSHOT_REQUIRED')
    bounded_evidence((interpreted,fit))
    _selected_dependencies(interpreted,fit,as_of)
    result=predict_state_proba(model,partition)  # includes Task9 fitted-state integrity
    _selected_dependencies(interpreted,fit,as_of,result.evidence)
    if result.timestamps != (as_of,) or result.probabilities.shape != (1,fit.n_states):
        raise ValueError('REGIME_OUTPUT_SHAPE_MISMATCH')
    current={r.feature:r for r in interpreted.evidence if r.as_of==interpreted.current_eod}
    actual={r.feature:r for r in result.evidence}
    if set(current)!=set(SIGNAL_UNITS) or set(actual)!=set(current):
        raise ValueError('REGIME_INPUT_SCHEMA_MISMATCH')
    if any(current[n].value != actual[n].value or current[n].available_at != actual[n].available_at for n in current):
        raise ValueError('REGIME_BRANCH_INPUT_MISMATCH')
    return RegimeFeatureSnapshot(as_of,role,fold_id,fit.region,interpreted,fit,
        tuple(float(v) for v in result.probabilities[0]),result.evidence,
        result.sequence_policy,result.parameter_scope)


def append_regime_records(bundle, *, as_of, role, fold_id, region, base_records, universe_hash, security_id):
    development_request(as_of,as_of,role)
    snapshot=bundle.snapshot
    heuristic_inputs,unsupervised_inputs=validate_regime_snapshot(snapshot,as_of=as_of,role=role,
        fold_id=fold_id,region=region)
    source=verify_evidence(snapshot,bundle.source,as_of=as_of)
    base={r['feature']:r for r in base_records}
    for row in snapshot.evidence:
        if row.feature not in SIGNAL_UNITS or row.value!=base[row.feature]['value'] or row.available_at!=base[row.feature]['available_at']:
            raise ValueError('REGIME_BASE_INPUT_MISMATCH')
    if set(r.feature for r in snapshot.evidence)!=set(SIGNAL_UNITS):
        raise ValueError('REGIME_BASE_INPUT_MISMATCH')
    if not 3 <= snapshot.fit.n_states <= 8 or len(snapshot.probabilities)!=snapshot.fit.n_states:
        raise ValueError('REGIME_ACTIVE_STATE_COUNT_MISMATCH')
    heuristic=snapshot.interpreted.probabilities
    if set(heuristic)!=set(STATES):
        raise ValueError('REGIME_INTERPRETABLE_STATE_MISMATCH')
    for values in (tuple(heuristic.values()),snapshot.probabilities):
        if any(not math.isfinite(v) or not 0<=v<=1 for v in values) or not math.isclose(sum(values),1.,abs_tol=1e-9):
            raise ValueError('INVALID_REGIME_PROBABILITIES')
    features=[(f'regime_interpretable_{state.lower()}_probability',heuristic[state]) for state in STATES]
    features += [(f'regime_state_{i}_probability',v) for i,v in enumerate(snapshot.probabilities)]
    summaries={
        'interpretable':_dependency_summary(heuristic_inputs),
        'unsupervised':_dependency_summary(unsupervised_inputs,earliest=snapshot.fit.train_bounds[1]),
    }
    records=[]; lineage=[]
    for name,value in features:
        branch='interpretable' if name.startswith('regime_interpretable_') else 'unsupervised'
        max_input,quality=summaries[branch]
        availability=max(max_input,snapshot.interpreted.current_eod)
        if availability>as_of:
            raise ValueError('REGIME_AVAILABILITY_AFTER_PREDICTION')
        records.append(dict(entity_id=security_id,feature=name,value=value,structural_missing=False,
            as_of=as_of,available_at=availability,max_input_available_at=max_input,quality=quality.value,
            registry_version='features-v1',fold_id=fold_id,role=str(role),producer='RegimeFeatureSnapshot',
            source_snapshot=source,fit_id=snapshot.fit.candidate_id,
            fitted_state_fingerprint=snapshot.fit.fitted_state_fingerprint,
            parameter_scope=snapshot.parameter_scope,sequence_policy=snapshot.sequence_policy))
        lineage.append(FeatureLineage(feature=name,provider='regime_candidate',source_snapshot=source,
            transform='candidate_probability',availability_rule='inputs_and_train_fit_known_before_prediction',
            source_observations=(snapshot.fit.candidate_id,snapshot.fit.fitted_state_fingerprint,snapshot.interpreted.config_hash),
            source_timestamps=(max_input,availability),universe_snapshot=universe_hash))
    return records,lineage,source
