"""Synthetic software contracts only; no financial comparison or market data."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import importlib

import numpy as np
import pytest

from quant_dca.calendars.service import eligible_session_close
from quant_dca.features.normalize import PartitionRole
from quant_dca.types import FeatureValue, QualityTier, Region

NAMES = ('broad_market_momentum_20d_raw', 'vix_level_raw', 'high_yield_spread_raw')
UNITS = dict(zip(NAMES, ('fractional_return', 'index_points', 'percentage_points')))


def api():
    try:
        return importlib.import_module('quant_dca.regimes.unsupervised')
    except ModuleNotFoundError:
        pytest.fail('unsupervised candidate framework is not implemented')


def selection():
    try:
        return importlib.import_module('quant_dca.regimes.selection')
    except ModuleNotFoundError:
        pytest.fail('candidate selection framework is not implemented')


def partition(role=PartitionRole.TRAIN, n=90, start=date(2020, 1, 2)):
    module = api()
    times = []
    while len(times) < n:
        close = eligible_session_close('XNYS', start)
        if close is not None:
            times.append(close)
        start += timedelta(days=1)
    rng = np.random.default_rng(19)
    rows = []
    for index, at in enumerate(times):
        state = (index // 10) % 3
        values = np.array([-.04 + .04 * state, 35 - 10 * state, 8 - 2 * state])
        values += rng.normal(size=3) * [.003, .8, .15]
        features = tuple(FeatureValue(feature=name, entity_id=None,
            observation_date=at.date().isoformat(), as_of=at, value=float(value),
            max_input_available_at=at, available_at=at, published_at=at,
            quality=QualityTier.B, source='synthetic', revision_id='v1', region=Region.US)
            for name, value in zip(NAMES, values))
        rows.append(module.RegimeSnapshot(eod=at, sequence_id='first', features=features))
    return module.RegimePartition(snapshots=tuple(rows), role=role, fold_id='synthetic-fold',
        starts_at=times[0], ends_at=times[-1], region=Region.US,
        benchmark_exchange='XNYS', feature_units=UNITS)


def unreadable():
    raise AssertionError('forbidden iteration')
    yield


class UnreadableFloat(float):
    def __float__(self):
        raise AssertionError('value consumed before metadata validated')


@pytest.mark.parametrize('family', ['hmm', 'gmm'])
def test_regime_grid_is_exactly_three_to_eight_states(family):
    assert [c.n_states for c in selection().candidate_grid(family)] == [3, 4, 5, 6, 7, 8]


@pytest.mark.parametrize('family', ['hmm', 'gmm'])
def test_real_estimators_repeat_seed_and_preserve_train_scale_and_lineage(family):
    m = api()
    train = partition()
    first = m.fit_regime_candidate(train, family, 3, 42)
    second = m.fit_regime_candidate(train, family, 3, 42)
    p = m.predict_state_proba(first, train)
    np.testing.assert_allclose(p.probabilities, m.predict_state_proba(second, train).probabilities)
    np.testing.assert_allclose(p.probabilities.sum(axis=1), 1)
    assert p.probabilities.shape == (90, 3)
    assert p.pit_validated and p.role is PartitionRole.TRAIN
    assert p.parameter_scope == 'full_training_partition_not_walk_forward'
    assert p.sequence_policy == 'independent_reset_at_request_and_sequence_start'
    assert p.sequence_starts == (0,)
    assert first.provenance.training_evidence == tuple(row for s in train.snapshots for row in s.features)
    assert first.provenance.family == family
    assert first.provenance.candidate_id == second.provenance.candidate_id
    assert 'hmmlearn' in first.provenance.estimator if family == 'hmm' else 'sklearn' in first.provenance.estimator
    means = tuple(first.provenance.scale_mean)
    validation = partition(PartitionRole.VALIDATION, 20, date(2021, 1, 4))
    m.predict_state_proba(first, validation)
    assert tuple(first.provenance.scale_mean) == means
    raw = np.array([[f.value for f in s.features] for s in train.snapshots])
    np.testing.assert_allclose(means, raw.mean(axis=0))
    assert np.isfinite(p.log_likelihood)


@pytest.mark.parametrize('role', [PartitionRole.VALIDATION, PartitionRole.OUTER_OOS, PartitionRole.HOLDOUT])
def test_fit_rejects_nontrain_before_iteration(role):
    train = replace(partition(), role=role, snapshots=unreadable())
    with pytest.raises(ValueError, match='TRAIN_PARTITION'):
        api().fit_regime_candidate(train, 'hmm', 3, 42)


@pytest.mark.parametrize('year', [2009, 2024, 2026])
def test_fit_rejects_request_bounds_before_iteration(year):
    train = replace(partition(), snapshots=unreadable(), ends_at=datetime(year, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match='DEVELOPMENT_BOUNDARY'):
        api().fit_regime_candidate(train, 'gmm', 3, 42)


@pytest.mark.parametrize('role', [PartitionRole.OUTER_OOS, PartitionRole.HOLDOUT])
def test_prediction_rejects_role_before_iteration(role):
    train = partition()
    fitted = api().fit_regime_candidate(train, 'gmm', 3, 42)
    with pytest.raises(ValueError, match='PARTITION'):
        api().predict_state_proba(fitted, replace(train, role=role, snapshots=unreadable()))


@pytest.mark.parametrize('change,match', [
    ({'fold_id': 'other'}, 'FOLD'),
    ({'role': PartitionRole.VALIDATION}, 'OVERLAP'),
    ({'ends_at': datetime(2024, 1, 1, tzinfo=timezone.utc)}, 'DEVELOPMENT_BOUNDARY'),
    ({'feature_units': {**UNITS, 'vix_level_raw': 'zscore'}}, 'UNITS'),
    ({'region': Region.EU}, 'REGION'),
])
def test_prediction_rejects_request_metadata_before_iteration(change, match):
    train = partition()
    fitted = api().fit_regime_candidate(train, 'gmm', 3, 42)
    with pytest.raises(ValueError, match=match):
        api().predict_state_proba(fitted, replace(train, snapshots=unreadable(), **change))


@pytest.mark.parametrize('change,match', [
    ({'entity_id': 'SECURITY'}, 'identity'),
    ({'feature': 'return_20d'}, 'SCHEMA'),
    ({'source': ''}, 'PROVENANCE'),
    ({'revision_id': ''}, 'PROVENANCE'),
    ({'region': Region.EU}, 'REGION'),
    ({'max_input_available_at': datetime(2023, 1, 1, tzinfo=timezone.utc)}, 'PIT'),
    ({'available_at': datetime(2024, 1, 1, tzinfo=timezone.utc)}, 'DEVELOPMENT_BOUNDARY'),
])
def test_all_snapshot_metadata_checked_before_any_values(change, match):
    train = partition(n=30)
    snapshots = list(train.snapshots)
    first = list(snapshots[0].features)
    first[0] = replace(first[0], value=UnreadableFloat(1))
    snapshots[0] = replace(snapshots[0], features=tuple(first))
    last = list(snapshots[-1].features)
    last[0] = replace(last[0], **change)
    snapshots[-1] = replace(snapshots[-1], features=tuple(last))
    with pytest.raises(ValueError, match=match):
        api().fit_regime_candidate(replace(train, snapshots=tuple(snapshots)), 'hmm', 3, 42)


@pytest.mark.parametrize('bad', [None, True, float('nan'), float('inf'), '2'])
def test_missing_and_invalid_values_fail_without_imputation(bad):
    train = partition(n=30)
    row = train.snapshots[0]
    row = replace(row, features=(replace(row.features[0], value=bad), *row.features[1:]))
    with pytest.raises((TypeError, ValueError), match='NUMERIC'):
        api().fit_regime_candidate(replace(train, snapshots=(row, *train.snapshots[1:])), 'gmm', 3, 42)


@pytest.mark.parametrize('family,n_states,seed', [('bad', 3, 1), ('gmm', 2, 1), ('hmm', 9, 1), ('gmm', True, 1), ('gmm', 3, True)])
def test_invalid_candidate_configuration_rejected_before_rows(family, n_states, seed):
    with pytest.raises(ValueError):
        api().fit_regime_candidate(replace(partition(), snapshots=unreadable()), family, n_states, seed)


def test_hmm_prefix_and_future_mutation_cannot_change_earlier_probabilities():
    m = api()
    train = partition()
    model = m.fit_regime_candidate(train, 'hmm', 3, 42)
    validation = partition(PartitionRole.VALIDATION, 40, date(2021, 1, 4))
    full = m.predict_state_proba(model, validation)
    prefix = replace(validation, ends_at=validation.snapshots[14].eod, snapshots=validation.snapshots[:15])
    np.testing.assert_allclose(full.probabilities[:15], m.predict_state_proba(model, prefix).probabilities)
    mutated = tuple(replace(s, features=tuple(replace(f, value=f.value * 3) for f in s.features))
                    if i >= 15 else s for i, s in enumerate(validation.snapshots))
    np.testing.assert_allclose(full.probabilities[:15], m.predict_state_proba(model, replace(validation, snapshots=mutated)).probabilities[:15])
    # The same forward-only contract applies to training outputs, conditional on fitted parameters.
    train_prefix = replace(train, ends_at=train.snapshots[14].eod, snapshots=train.snapshots[:15])
    np.testing.assert_allclose(m.predict_state_proba(model, train).probabilities[:15],
                               m.predict_state_proba(model, train_prefix).probabilities)


def test_hmm_filter_matches_hand_derived_forward_result_not_smoothing():
    result = api().forward_filter_unvalidated(
        np.log([[.8, .2], [.1, .9]]), np.array([.5, .5]), np.array([[.75, .25], [.25, .75]]), (2,))
    np.testing.assert_allclose(result[0], [[.8, .2], [.065/.38, .315/.38]])
    assert result[1] == pytest.approx(np.log(.5) + np.log(.38))


def test_missing_sessions_require_explicit_sequence_reset_and_no_cross_gap_transition():
    m = api()
    train = partition()
    gap = (*train.snapshots[:30], *train.snapshots[35:])
    with pytest.raises(ValueError, match='SEQUENCE_GAP'):
        m.fit_regime_candidate(replace(train, snapshots=gap), 'hmm', 3, 42)
    reset = (*gap[:30], *(replace(s, sequence_id='second') for s in gap[30:]))
    model = m.fit_regime_candidate(replace(train, snapshots=reset), 'hmm', 3, 42)
    combined = m.predict_state_proba(model, replace(train, snapshots=reset))
    separate = replace(train, starts_at=reset[30].eod, snapshots=reset[30:])
    np.testing.assert_allclose(combined.probabilities[30:], m.predict_state_proba(model, separate).probabilities)
    assert combined.sequence_starts == (0, 30)
    assert m.candidate_diagnostics(model, replace(train, snapshots=reset)).transition_count == len(reset) - 2


def test_duplicate_time_reused_sequence_and_row_outside_bounds_fail():
    m = api()
    train = partition(n=30)
    bad_sequences = (train.snapshots[0], replace(train.snapshots[1], sequence_id='other'), *train.snapshots[2:])
    for rows, match in [((train.snapshots[0], *train.snapshots), 'ORDER'), (bad_sequences, 'SEQUENCE'),
                         ((replace(train.snapshots[0], eod=train.starts_at-timedelta(days=1)), *train.snapshots[1:]), 'BOUND')]:
        with pytest.raises(ValueError, match=match):
            m.fit_regime_candidate(replace(train, snapshots=rows), 'gmm', 3, 42)


@pytest.mark.parametrize('family', ['hmm', 'gmm'])
def test_diagnostics_and_comparison_never_choose_by_training_likelihood(family):
    m, s = api(), selection()
    train = partition()
    model = m.fit_regime_candidate(train, family, 3, 42)
    validation = partition(PartitionRole.VALIDATION, 40, date(2021, 1, 4))
    diag = m.candidate_diagnostics(model, validation)
    assert diag.role is PartitionRole.VALIDATION
    assert sum(diag.occupancy) == pytest.approx(1)
    assert diag.transition_count == 39
    assert 0 <= diag.temporal_state_stability <= 1
    assert diag.transition_stability is None or 0 <= diag.transition_stability <= 1
    assert diag.mean_log_likelihood == pytest.approx(diag.log_likelihood/40)
    report = s.comparison_report(model, validation)
    assert not report.complete
    assert set(report.missing_evidence) == {'economic_interpretability', 'downstream_incremental_value', 'cross_fit_stability'}
    assert report.selected_candidate is None
    complete = s.comparison_report(model, validation,
        economic_annotations={0: 'synthetic A', 1: 'synthetic B', 2: 'synthetic C'},
        downstream_incremental_value={5: .01, 20: -.01, 60: .02}, evidence_note='synthetic contract only',
        cross_fit_stability=s.CrossFitStability(state_stability=.9, transition_stability=.8, alignment_note='synthetic explicitly aligned fixture'))
    assert complete.complete and complete.selected_candidate is None
    assert complete.evaluation_scope == 'inner_validation_only_not_financial_comparison'
    with pytest.raises(ValueError, match='VALIDATION'):
        s.comparison_report(model, train)


def test_raw_unit_likelihood_has_train_scale_jacobian_correction():
    m = api()
    train = partition()
    model = m.fit_regime_candidate(train, 'gmm', 3, 42)
    prediction = m.predict_state_proba(model, train)
    assert prediction.likelihood_units == 'log_density_in_declared_raw_signal_units'
    assert prediction.log_likelihood == pytest.approx(prediction.standardized_log_likelihood -
        90 * sum(np.log(model.provenance.scale_std)))


def test_short_diagnostics_do_not_fabricate_transition_or_state_stability():
    m = api()
    model = m.fit_regime_candidate(partition(), 'gmm', 3, 42)
    p = partition(PartitionRole.VALIDATION, 1, date(2021, 1, 4))
    d = m.candidate_diagnostics(model, p)
    assert d.transition_count == 0 and d.transition_stability is None
    assert d.temporal_state_stability is None
    assert d.state_alignment_scope == 'within_fitted_candidate_only_cross_fit_alignment_not_performed'


@pytest.mark.parametrize('changes', [
    {'economic_annotations': {0: 'A'}},
    {'downstream_incremental_value': {5: .1}},
    {'downstream_incremental_value': {5: .1, 20: float('nan'), 60: .2}},
    {'economic_annotations': {0: 'A', 1: 'B', 2: 'C'}},
])
def test_supplied_comparison_evidence_requires_complete_contract_and_note(changes):
    m = api()
    fitted = m.fit_regime_candidate(partition(), 'gmm', 3, 42)
    with pytest.raises(ValueError):
        selection().comparison_report(fitted, partition(PartitionRole.VALIDATION, 20, date(2021, 1, 4)), **changes)


def test_comparison_request_bounds_checked_before_external_numeric_evidence():
    m = api()
    model = m.fit_regime_candidate(partition(), 'gmm', 3, 42)
    validation = partition(PartitionRole.VALIDATION, 20, date(2021, 1, 4))
    forbidden = replace(validation, ends_at=datetime(2024, 1, 1, tzinfo=timezone.utc), snapshots=unreadable())
    with pytest.raises(ValueError, match='DEVELOPMENT_BOUNDARY'):
        selection().comparison_report(model, forbidden, evidence_note='synthetic',
            downstream_incremental_value={5: UnreadableFloat(.1), 20: .1, 60: .1})


@pytest.mark.parametrize('family,attribute', [
    ('hmm', 'startprob_'), ('hmm', 'transmat_'), ('hmm', 'means_'), ('hmm', '_covars_'),
    ('gmm', 'weights_'), ('gmm', 'means_'), ('gmm', 'covariances_'),
    ('gmm', 'precisions_'), ('gmm', 'precisions_cholesky_'),
])
def test_fitted_parameter_mutation_rejected_before_prediction_data_read(family, attribute):
    m = api()
    train = partition()
    model = m.fit_regime_candidate(train, family, 3, 42)
    getattr(model._estimator, attribute).flat[0] += .25
    with pytest.raises(ValueError, match='FITTED_STATE_INTEGRITY'):
        m.predict_state_proba(model, replace(train, snapshots=unreadable()))


@pytest.mark.parametrize('family', ['hmm', 'gmm'])
@pytest.mark.parametrize('mutation', ['shape', 'covariance_type', 'n_components', 'convergence', 'missing'])
def test_fitted_structure_and_metadata_mutation_rejected(family, mutation):
    m = api()
    train = partition()
    model = m.fit_regime_candidate(train, family, 3, 42)
    estimator = model._estimator
    if mutation == 'shape':
        estimator.means_ = estimator.means_.reshape(1, -1)
    elif mutation == 'covariance_type':
        estimator.covariance_type = 'full'
    elif mutation == 'n_components':
        estimator.n_components = 4
    elif mutation == 'convergence':
        if family == 'hmm':
            estimator.monitor_.iter += 1
        else:
            estimator.converged_ = not estimator.converged_
    else:
        del estimator.means_
    with pytest.raises(ValueError, match='FITTED_STATE_INTEGRITY'):
        m.predict_state_proba(model, replace(train, snapshots=unreadable()))


@pytest.mark.parametrize('family', ['hmm', 'gmm'])
def test_refitted_estimator_cannot_reuse_original_candidate_identity(family):
    m = api()
    train = partition()
    model = m.fit_regime_candidate(train, family, 3, 42)
    original_id = model.provenance.candidate_id
    # Real estimator refit on independent synthetic numbers, with no data access.
    shifted = np.random.default_rng(71).normal(loc=10., size=(90, 3))
    model._estimator.fit(shifted)
    with pytest.raises(ValueError, match='FITTED_STATE_INTEGRITY'):
        m.predict_state_proba(model, replace(train, snapshots=unreadable()))
    assert model.provenance.candidate_id == original_id


@pytest.mark.parametrize('family', ['hmm', 'gmm'])
def test_fitted_fingerprint_is_stable_and_bound_to_candidate_identity(family):
    m = api()
    train = partition()
    first = m.fit_regime_candidate(train, family, 3, 42)
    second = m.fit_regime_candidate(train, family, 3, 42)
    assert len(first.provenance.fitted_state_fingerprint) == 64
    assert first.provenance.fitted_state_fingerprint == second.provenance.fitted_state_fingerprint
    assert first.provenance.candidate_id == second.provenance.candidate_id
    before = m.predict_state_proba(first, train)
    after = m.predict_state_proba(first, train)
    np.testing.assert_array_equal(before.probabilities, after.probabilities)
    tampered = replace(first, provenance=replace(first.provenance, fitted_state_fingerprint='0' * 64))
    with pytest.raises(ValueError, match='FITTED_STATE_INTEGRITY'):
        m.predict_state_proba(tampered, replace(train, snapshots=unreadable()))


@pytest.mark.parametrize('family', ['hmm', 'gmm'])
def test_mutation_during_lazy_input_iteration_cannot_bypass_integrity_check(family):
    m = api()
    train = partition()
    model = m.fit_regime_candidate(train, family, 3, 42)
    def mutate_then_yield():
        model._estimator.means_[0, 0] += 1.
        yield from train.snapshots
    with pytest.raises(ValueError, match='FITTED_STATE_INTEGRITY'):
        m.predict_state_proba(model, replace(train, snapshots=mutate_then_yield()))
