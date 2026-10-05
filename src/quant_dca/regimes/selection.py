"""Candidate grid and incomplete-evidence comparison contract; no winner policy.

Inner validation likelihood is the only permitted held-out diagnostic here.
External annotations and downstream scalar summaries are caller declarations,
not verified economic results. Labels/targets remain outside the feature API.
Cross-fit alignment must be supplied explicitly; within-fit drift is insufficient.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from quant_dca.features.normalize import PartitionRole
from quant_dca.regimes.unsupervised import (
    CandidateDiagnostics, RegimeCandidate, RegimePartition, candidate_diagnostics, _request,
)
from quant_dca.regimes.interpretable import _number


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    family: str
    n_states: int


def candidate_grid(family: str) -> tuple[CandidateSpec, ...]:
    if family not in ('hmm', 'gmm'):
        raise ValueError('CANDIDATE_FAMILY')
    return tuple(CandidateSpec(family, states) for states in range(3, 9))


@dataclass(frozen=True, slots=True, kw_only=True)
class CrossFitStability:
    state_stability: float
    transition_stability: float
    alignment_note: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ComparisonReport:
    diagnostics: CandidateDiagnostics
    economic_annotations: Mapping[int, str] | None
    downstream_incremental_value: Mapping[int, float] | None
    cross_fit_stability: CrossFitStability | None
    evidence_note: str | None
    missing_evidence: tuple[str, ...]
    complete: bool
    selected_candidate: None = None
    evaluation_scope: str = 'inner_validation_only_not_financial_comparison'
    external_evidence_status: str = 'caller_declared_not_independently_verified'


def comparison_report(
    model: RegimeCandidate, validation: RegimePartition, *,
    economic_annotations: Mapping[int, str] | None = None,
    downstream_incremental_value: Mapping[int, float] | None = None,
    cross_fit_stability: CrossFitStability | None = None,
    evidence_note: str | None = None,
) -> ComparisonReport:
    if not isinstance(validation, RegimePartition) or validation.role is not PartitionRole.VALIDATION:
        raise ValueError('INNER_VALIDATION_REQUIRED')
    if not isinstance(model, RegimeCandidate):
        raise TypeError('RegimeCandidate required')
    _request(validation, fitting=False, model=model)
    supplied = any(value is not None for value in (economic_annotations, downstream_incremental_value, cross_fit_stability))
    if supplied and (not isinstance(evidence_note, str) or not evidence_note.strip()):
        raise ValueError('EXTERNAL_EVIDENCE_NOTE_REQUIRED')
    if economic_annotations is not None:
        if (not isinstance(economic_annotations, Mapping) or
            set(economic_annotations) != set(range(model.provenance.n_states)) or
            any(type(k) is not int or not isinstance(v, str) or not v.strip() for k, v in economic_annotations.items())):
            raise ValueError('ECONOMIC_STATE_ANNOTATIONS_REQUIRED')
        economic_annotations = MappingProxyType(dict(economic_annotations))
    if downstream_incremental_value is not None:
        if not isinstance(downstream_incremental_value, Mapping) or set(downstream_incremental_value) != {5, 20, 60}:
            raise ValueError('DOWNSTREAM_HORIZONS_5_20_60_REQUIRED')
        downstream_incremental_value = MappingProxyType({k: _number(v) for k, v in downstream_incremental_value.items()})
    if cross_fit_stability is not None:
        if not isinstance(cross_fit_stability, CrossFitStability):
            raise TypeError('CrossFitStability required')
        if not isinstance(cross_fit_stability.alignment_note, str) or not cross_fit_stability.alignment_note.strip():
            raise ValueError('CROSS_FIT_ALIGNMENT_REQUIRED')
        if any(not 0 <= _number(v) <= 1 for v in (cross_fit_stability.state_stability, cross_fit_stability.transition_stability)):
            raise ValueError('CROSS_FIT_STABILITY_RANGE')
    diagnostics = candidate_diagnostics(model, validation)
    missing = []
    for name, value in (('economic_interpretability', economic_annotations),
                        ('downstream_incremental_value', downstream_incremental_value),
                        ('cross_fit_stability', cross_fit_stability)):
        if value is None:
            missing.append(name)
    if diagnostics.temporal_state_stability is None:
        missing.append('temporal_state_stability')
    if diagnostics.transition_stability is None:
        missing.append('transition_stability')
    if not diagnostics.converged:
        missing.append('fit_convergence')
    return ComparisonReport(diagnostics=diagnostics, economic_annotations=economic_annotations,
        downstream_incremental_value=downstream_incremental_value, cross_fit_stability=cross_fit_stability,
        evidence_note=evidence_note, missing_evidence=tuple(missing), complete=not missing)
