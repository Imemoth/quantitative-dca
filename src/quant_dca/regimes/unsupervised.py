"""Bounded software candidates, not an executed financial regime comparison.

The explicit three-signal schema is a candidate, not a research-selected input
set. Canonical checks validate declared metadata, not provider truth or admission.
Targets never enter this module. Train scaling uses population standard deviation;
zero-variance dimensions use scale 1, with no imputation or clipping.

HMM outputs use forward filtering conditional on full-train fitted parameters.
Training outputs are NOT walk-forward estimates. Every request and explicit
sequence start resets the HMM prior; validation is an independent sequence even
when contiguous with train. No smoothing/Viterbi probabilities are exposed.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from importlib.metadata import version
import json
import math
from types import MappingProxyType

import numpy as np
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from quant_dca.calendars.service import previous_eligible_eod
from quant_dca.features.normalize import PartitionRole
from quant_dca.regimes.interpretable import InterpretableRegimeModel, _number, _timestamp
from quant_dca.types import FeatureValue, Region

SIGNAL_UNITS = MappingProxyType({
    'broad_market_momentum_20d_raw': 'fractional_return',
    'vix_level_raw': 'index_points',
    'high_yield_spread_raw': 'percentage_points',
})
_SEQUENCE_POLICY = 'independent_reset_at_request_and_sequence_start'
_PARAMETER_SCOPE = 'full_training_partition_not_walk_forward'
_LIKELIHOOD_UNITS = 'log_density_in_declared_raw_signal_units'


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimeSnapshot:
    eod: datetime
    sequence_id: str
    features: Iterable[FeatureValue]


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimePartition:
    """Lazy data envelope: validation occurs at fit/predict, before iteration."""
    snapshots: Iterable[RegimeSnapshot]
    role: PartitionRole
    fold_id: str
    starts_at: datetime
    ends_at: datetime
    region: Region
    benchmark_exchange: str
    feature_units: Mapping[str, str]


@dataclass(frozen=True, slots=True, kw_only=True)
class FitProvenance:
    candidate_id: str
    fitted_state_fingerprint: str
    family: str
    n_states: int
    seed: int
    fold_id: str
    train_bounds: tuple[datetime, datetime]
    region: Region
    benchmark_exchange: str
    signal_units: tuple[tuple[str, str], ...]
    scale_mean: tuple[float, ...]
    scale_std: tuple[float, ...]
    training_evidence: tuple[FeatureValue, ...]
    sequence_starts: tuple[int, ...]
    estimator: str
    dependency_versions: tuple[tuple[str, str], ...]
    configuration: tuple[tuple[str, object], ...]
    sequence_policy: str = _SEQUENCE_POLICY
    parameter_scope: str = _PARAMETER_SCOPE
    schema_status: str = 'software_candidate_not_research_selected'


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimeCandidate:
    """Common HMM/GMM wrapper. The private estimator is not a prediction API."""
    provenance: FitProvenance
    _estimator: GaussianHMM | GaussianMixture
    converged: bool
    iterations: int


@dataclass(frozen=True, slots=True, kw_only=True)
class StateProbabilities:
    probabilities: np.ndarray
    log_likelihood: float
    standardized_log_likelihood: float
    candidate_id: str
    timestamps: tuple[datetime, ...]
    sequence_starts: tuple[int, ...]
    role: PartitionRole
    evidence: tuple[FeatureValue, ...]
    pit_validated: bool = True
    sequence_policy: str = _SEQUENCE_POLICY
    parameter_scope: str = _PARAMETER_SCOPE
    likelihood_units: str = _LIKELIHOOD_UNITS


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateDiagnostics:
    candidate_id: str
    role: PartitionRole
    log_likelihood: float
    mean_log_likelihood: float
    occupancy: tuple[float, ...]
    transition_matrix: tuple[tuple[float | None, ...], ...]
    transition_count: int
    temporal_state_stability: float | None
    transition_stability: float | None
    converged: bool
    iterations: int
    sequence_starts: tuple[int, ...]
    likelihood_units: str = _LIKELIHOOD_UNITS
    sequence_policy: str = _SEQUENCE_POLICY
    state_alignment_scope: str = 'within_fitted_candidate_only_cross_fit_alignment_not_performed'


def _request(partition: RegimePartition, *, fitting: bool, model: RegimeCandidate | None = None) -> None:
    if not isinstance(partition, RegimePartition):
        raise TypeError('RegimePartition required')
    if not isinstance(partition.role, PartitionRole):
        raise TypeError('PartitionRole required')
    if fitting and partition.role is not PartitionRole.TRAIN:
        raise ValueError('TRAIN_PARTITION_REQUIRED')
    if partition.role not in (PartitionRole.TRAIN, PartitionRole.VALIDATION):
        raise ValueError('DEVELOPMENT_PARTITION_REQUIRED')
    start, end = map(_timestamp, (partition.starts_at, partition.ends_at))
    if start > end:
        raise ValueError('PARTITION_BOUNDARY_ORDER')
    if not isinstance(partition.fold_id, str) or not partition.fold_id.strip():
        raise ValueError('FOLD_ID_REQUIRED')
    if not isinstance(partition.region, Region) or partition.region not in (Region.US, Region.EU):
        raise ValueError('REGION_REQUIRED')
    exchanges = ('XNYS', 'XNAS') if partition.region is Region.US else ('XETR', 'XLON', 'XPAR')
    if partition.benchmark_exchange not in exchanges:
        raise ValueError('BENCHMARK_REGION_MISMATCH')
    if not isinstance(partition.feature_units, Mapping) or dict(partition.feature_units) != dict(SIGNAL_UNITS):
        raise ValueError('EXPLICIT_FEATURE_UNITS_REQUIRED')
    if model is not None:
        fit = model.provenance
        if partition.fold_id != fit.fold_id:
            raise ValueError('FOLD_ID_MISMATCH')
        if partition.region != fit.region or partition.benchmark_exchange != fit.benchmark_exchange:
            raise ValueError('MODEL_REGION_MISMATCH')
        if partition.role is PartitionRole.TRAIN:
            if start < fit.train_bounds[0] or end > fit.train_bounds[1]:
                raise ValueError('TRAIN_PARTITION_BOUNDARY_MISMATCH')
        elif start <= fit.train_bounds[1]:
            raise ValueError('PARTITION_BOUNDARY_OVERLAP')


def _materialize(partition: RegimePartition):
    snapshots = tuple(partition.snapshots)
    if not snapshots:
        raise ValueError('EMPTY_PARTITION')
    rows, starts, seen = [], [], set()
    previous = None
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, RegimeSnapshot):
            raise TypeError('RegimeSnapshot required')
        at = _timestamp(snapshot.eod)
        if not partition.starts_at <= at <= partition.ends_at:
            raise ValueError('SNAPSHOT_OUTSIDE_BOUNDARY')
        if at != previous_eligible_eod(partition.benchmark_exchange, at):
            raise ValueError('SNAPSHOT_NOT_BENCHMARK_EOD')
        if not isinstance(snapshot.sequence_id, str) or not snapshot.sequence_id.strip():
            raise ValueError('SEQUENCE_ID_REQUIRED')
        if previous is not None and at <= previous.eod:
            raise ValueError('SNAPSHOT_TIME_ORDER')
        if previous is None or snapshot.sequence_id != previous.sequence_id:
            if snapshot.sequence_id in seen:
                raise ValueError('SEQUENCE_ID_REUSED')
            seen.add(snapshot.sequence_id)
            starts.append(index)
        elif previous.eod != previous_eligible_eod(partition.benchmark_exchange, at - timedelta(microseconds=1)):
            raise ValueError('SEQUENCE_GAP: declare a new sequence_id')
        # Reuse Task8 canonical schema/PIT checks; these consume no numeric values.
        rows.append(InterpretableRegimeModel._snapshot(snapshot.features, at, partition.region))
        previous = snapshot
    # Validate ALL row metadata before reading the first numeric cell.
    matrix = np.array([[ _number({r.feature: r for r in row}[name].value)
                         for name in SIGNAL_UNITS] for row in rows], dtype=float)
    lengths = tuple(b - a for a, b in zip(starts, (*starts[1:], len(snapshots))))
    return matrix, tuple(s.eod for s in snapshots), tuple(starts), lengths, tuple(r for row in rows for r in row)


def forward_filter_unvalidated(log_emissions, start_probability, transition, lengths):
    """Pure numeric helper; establishes NO dates, fit scope, units or PIT evidence.

    Returns causal filtered probabilities and sequence log likelihood. Explicit
    lengths reset the prior. Inputs may have -inf log emission for zero mass.
    """
    emissions = np.asarray(log_emissions, dtype=float)
    start = np.asarray(start_probability, dtype=float)
    trans = np.asarray(transition, dtype=float)
    if emissions.ndim != 2 or not emissions.shape[0] or not emissions.shape[1]:
        raise ValueError('FILTER_EMISSION_SHAPE')
    n, k = emissions.shape
    if start.shape != (k,) or trans.shape != (k, k):
        raise ValueError('FILTER_PROBABILITY_SHAPE')
    if (not np.isfinite(start).all() or not np.isfinite(trans).all() or
            (start < 0).any() or (trans < 0).any() or
            not np.isclose(start.sum(), 1) or not np.allclose(trans.sum(axis=1), 1)):
        raise ValueError('FILTER_INVALID_PROBABILITY')
    if np.isnan(emissions).any() or np.isposinf(emissions).any():
        raise ValueError('FILTER_INVALID_EMISSION')
    lengths = tuple(lengths)
    if not lengths or any(type(v) is not int or v < 1 for v in lengths) or sum(lengths) != n:
        raise ValueError('FILTER_SEQUENCE_LENGTHS')
    with np.errstate(divide='ignore'):
        log_start, log_trans = np.log(start), np.log(trans)
    probabilities = np.empty_like(emissions)
    total, offset = 0., 0
    for length in lengths:
        alpha = log_start
        for i in range(offset, offset + length):
            if i > offset:
                alpha = logsumexp(alpha[:, None] + log_trans, axis=0)
            alpha = alpha + emissions[i]
            norm = float(logsumexp(alpha))
            if not math.isfinite(norm):
                raise ValueError('FILTER_IMPOSSIBLE_OBSERVATION')
            alpha = alpha - norm
            probabilities[i] = np.exp(alpha)
            total += norm
        offset += length
    return probabilities, total


def _fitted_state_fingerprint(estimator, family: str) -> str:
    """Bind all fitted prediction arrays, their shapes/dtypes and fit metadata.

    The retained third-party estimator is mutable. This fingerprint detects
    ordinary parameter edits/refits; it is not a security boundary against code
    that replaces the estimator methods or deliberately forges the provenance.
    """
    expected_type = GaussianHMM if family == 'hmm' else GaussianMixture
    if family not in ('hmm', 'gmm') or type(estimator) is not expected_type:
        raise ValueError('FITTED_STATE_INTEGRITY: estimator family changed')
    metadata = {'family': family, 'estimator': f'{type(estimator).__module__}.{type(estimator).__name__}',
                'parameters': estimator.get_params(deep=False)}
    if family == 'hmm':
        # covars_ is expanded from _covars_ using covariance_type, n_components
        # and n_features; preserve the source array and all those dimensions.
        arrays = ('startprob_', 'transmat_', 'means_', '_covars_')
        metadata.update(n_features=estimator.n_features,
                        monitor_iteration=estimator.monitor_.iter,
                        monitor_history=tuple(estimator.monitor_.history),
                        monitor_tolerance=estimator.monitor_.tol,
                        monitor_max_iterations=estimator.monitor_.n_iter)
    else:
        arrays = ('weights_', 'means_', 'covariances_', 'precisions_', 'precisions_cholesky_')
        metadata.update(n_features=estimator.n_features_in_, converged=bool(estimator.converged_),
                        iterations=estimator.n_iter_, lower_bound=estimator.lower_bound_,
                        lower_bounds=tuple(estimator.lower_bounds_))
    digest = hashlib.sha256(json.dumps(metadata, sort_keys=True, allow_nan=False).encode())
    for name in arrays:
        array = getattr(estimator, name)
        if not isinstance(array, np.ndarray) or not np.issubdtype(array.dtype, np.number):
            raise ValueError('FITTED_STATE_INTEGRITY: invalid fitted array')
        digest.update(json.dumps((name, array.shape, array.dtype.str)).encode())
        digest.update(array.tobytes(order='C'))
    return digest.hexdigest()


def _verify_fitted_state(model: RegimeCandidate) -> None:
    try:
        actual = _fitted_state_fingerprint(model._estimator, model.provenance.family)
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError('FITTED_STATE_INTEGRITY: fitted state or metadata changed') from exc
    if actual != model.provenance.fitted_state_fingerprint:
        raise ValueError('FITTED_STATE_INTEGRITY: fitted state or metadata changed')


def fit_regime_candidate(train: RegimePartition, family: str, n_states: int, seed: int) -> RegimeCandidate:
    _request(train, fitting=True)
    if family not in ('hmm', 'gmm') or type(n_states) is not int or not 3 <= n_states <= 8:
        raise ValueError('CANDIDATE_FAMILY_OR_STATE_COUNT')
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('CANDIDATE_SEED')
    values, timestamps, starts, lengths, evidence = _materialize(train)
    if len(values) < n_states * (values.shape[1] + 1) or len(np.unique(values, axis=0)) < n_states:
        raise ValueError('INSUFFICIENT_TRAIN_SAMPLES')
    scaler = StandardScaler().fit(values)
    scaled = scaler.transform(values)
    if not np.isfinite(scaled).all() or not np.isfinite(scaler.mean_).all() or not np.isfinite(scaler.scale_).all():
        raise ValueError('UNSAFE_SCALE_ARITHMETIC')
    # Fixed numerical configuration is a software default, not selected tuning.
    config = {'covariance_type': 'diag', 'seed': seed, 'n_states': n_states,
              'max_iter': 200, 'tol': .001, 'min_covar_initialization' if family == 'hmm' else 'reg_covar': .001, 'n_init': 1}
    with threadpool_limits(limits=1):
        if family == 'hmm':
            estimator = GaussianHMM(n_components=n_states, covariance_type='diag', random_state=seed,
                                    n_iter=200, tol=.001, min_covar=.001)
            estimator.fit(scaled, lengths=list(lengths))
            history = tuple(estimator.monitor_.history)
            converged = len(history) >= 2 and 0 <= history[-1] - history[-2] < .001
            iterations = estimator.monitor_.iter
        else:
            estimator = GaussianMixture(n_components=n_states, covariance_type='diag', random_state=seed,
                                        max_iter=200, tol=.001, reg_covar=.001, n_init=1).fit(scaled)
            converged, iterations = bool(estimator.converged_), estimator.n_iter_
    fingerprint = _fitted_state_fingerprint(estimator, family)
    versions = tuple((name, version(name)) for name in ('numpy', 'scipy', 'scikit-learn', 'hmmlearn'))
    digest = hashlib.sha256()
    digest.update(fingerprint.encode())
    digest.update(values.tobytes())
    digest.update(repr(evidence).encode())
    digest.update(json.dumps([family, config, versions, starts, train.fold_id, str(train.starts_at),
                             str(train.ends_at), train.region, train.benchmark_exchange, list(SIGNAL_UNITS.items())],
                            sort_keys=True).encode())
    provenance = FitProvenance(candidate_id=digest.hexdigest(), fitted_state_fingerprint=fingerprint, family=family, n_states=n_states, seed=seed,
        fold_id=train.fold_id, train_bounds=(train.starts_at, train.ends_at), region=train.region,
        benchmark_exchange=train.benchmark_exchange, signal_units=tuple(SIGNAL_UNITS.items()),
        scale_mean=tuple(float(v) for v in scaler.mean_), scale_std=tuple(float(v) for v in scaler.scale_),
        training_evidence=evidence, sequence_starts=starts, estimator=f'{type(estimator).__module__}.{type(estimator).__name__}',
        dependency_versions=versions, configuration=tuple(config.items()))
    model = RegimeCandidate(provenance=provenance, _estimator=estimator, converged=converged, iterations=iterations)
    _predict_values(model, values, lengths)  # Fail closed if fitted numerical parameters are unusable.
    return model


def _predict_values(model, values, lengths):
    _verify_fitted_state(model)  # Also guard mutations caused by lazy input iteration.
    mean, scale = np.asarray(model.provenance.scale_mean), np.asarray(model.provenance.scale_std)
    with np.errstate(over='ignore', invalid='ignore'):
        scaled = (values - mean) / scale
    if not np.isfinite(scaled).all():
        raise ValueError('UNSAFE_SCALE_ARITHMETIC')
    estimator = model._estimator
    with threadpool_limits(limits=1):
        if model.provenance.family == 'hmm':
            # Public fitted diagonal Gaussian parameters; do not call predict_proba,
            # score_samples or decode: hmmlearn uses backward smoothing there.
            variance = np.diagonal(estimator.covars_, axis1=1, axis2=2)
            with np.errstate(over='ignore', invalid='ignore'):
                emissions = -.5 * (np.log(2 * np.pi * variance).sum(axis=1)[None, :] +
                    (((scaled[:, None, :] - estimator.means_[None, :, :]) ** 2) / variance[None, :, :]).sum(axis=2))
            probabilities, likelihood = forward_filter_unvalidated(emissions, estimator.startprob_, estimator.transmat_, lengths)
        else:
            probabilities = estimator.predict_proba(scaled)
            likelihood = float(estimator.score_samples(scaled).sum())
    if not np.isfinite(probabilities).all() or not math.isfinite(likelihood):
        raise ValueError('NONFINITE_CANDIDATE_OUTPUT')
    raw_likelihood = likelihood - len(values) * float(np.log(scale).sum())
    if not math.isfinite(raw_likelihood):
        raise ValueError('NONFINITE_CANDIDATE_OUTPUT')
    probabilities.setflags(write=False)
    return probabilities, likelihood, raw_likelihood


def predict_state_proba(model: RegimeCandidate, X: RegimePartition) -> StateProbabilities:
    if not isinstance(model, RegimeCandidate):
        raise TypeError('RegimeCandidate required')
    _request(X, fitting=False, model=model)
    _verify_fitted_state(model)  # Reject mutation/refit before prediction data is read.
    values, times, starts, lengths, evidence = _materialize(X)
    probabilities, standardized, likelihood = _predict_values(model, values, lengths)
    return StateProbabilities(probabilities=probabilities, log_likelihood=likelihood,
        standardized_log_likelihood=standardized, candidate_id=model.provenance.candidate_id,
        timestamps=times, sequence_starts=starts, role=X.role, evidence=evidence)


def candidate_diagnostics(model: RegimeCandidate, X: RegimePartition) -> CandidateDiagnostics:
    """Descriptive within-fit diagnostics, never evidence of cross-fit alignment.

    Occupancy averages causal probabilities. Transition counts use adjacent
    argmax filtered states excluding reset edges; unsupported rows are None.
    State stability = 1 - TV(first-half occupancy, second-half occupancy).
    Transition stability uses 1 - mean row TV on rows supported in BOTH halves;
    no common supported row yields None. No financial thresholds are implied.
    """
    result = predict_state_proba(model, X)
    p = result.probabilities
    n, k = p.shape
    hard = p.argmax(axis=1)
    split = n // 2
    counts, left, right = (np.zeros((k, k), dtype=int) for _ in range(3))
    for i in range(1, n):
        if i in result.sequence_starts:
            continue
        counts[hard[i-1], hard[i]] += 1
        if i < split:
            left[hard[i-1], hard[i]] += 1
        elif i > split:
            right[hard[i-1], hard[i]] += 1
    occupancy = tuple(float(v) for v in p.mean(axis=0))
    state_stability = None if n < 2 else float(1 - np.abs(p[:split].mean(axis=0) - p[split:].mean(axis=0)).sum()/2)
    supported = (left.sum(axis=1) > 0) & (right.sum(axis=1) > 0)
    transition_stability = None
    if supported.any():
        a, b = left[supported], right[supported]
        transition_stability = float(1 - np.abs(a/a.sum(axis=1)[:, None] - b/b.sum(axis=1)[:, None]).sum(axis=1).mean()/2)
    matrix = tuple(tuple(float(v/row.sum()) for v in row) if row.sum() else (None,) * k for row in counts)
    return CandidateDiagnostics(candidate_id=result.candidate_id, role=X.role, log_likelihood=result.log_likelihood,
        mean_log_likelihood=result.log_likelihood/n, occupancy=occupancy, transition_matrix=matrix,
        transition_count=int(counts.sum()), temporal_state_stability=state_stability,
        transition_stability=transition_stability, converged=model.converged, iterations=model.iterations,
        sequence_starts=result.sequence_starts)
