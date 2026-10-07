"""Reject raw captures that could otherwise masquerade as clean vintage evidence."""
from copy import deepcopy

import pytest


def sample():
    return {
        'observation_start': '2010-01-01', 'observation_end': '2010-12-31',
        'realtime_start': '2010-01-01', 'realtime_end': '2011-12-31',
        'count': 3, 'offset': 0, 'output_type': 1, 'units': 'lin',
        'observations': [
            {'date': '2010-01-01', 'realtime_start': '2010-02-01', 'realtime_end': '2010-02-28', 'value': '100'},
            {'date': '2010-01-01', 'realtime_start': '2010-03-01', 'realtime_end': '2011-12-31', 'value': '101'},
            {'date': '2010-02-01', 'realtime_start': '2010-03-01', 'realtime_end': '2011-12-31', 'value': '.'},
        ],
    }


def profile(document):
    from quant_dca.admission.profile import profile_fred
    return profile_fred(document, request_bounds={
        'observation_start': '2010-01-01', 'observation_end': '2010-12-31',
        'realtime_start': '2010-01-01', 'realtime_end': '2011-12-31',
    })


def test_vintage_rows_are_not_unique_observations_or_coverage_proof():
    result = profile(sample())
    assert result['rows'] == 3
    assert result['distinct_observation_dates'] == 2
    assert result['missing_value_rows'] == 1
    assert result['right_boundary_intervals'] == 2
    assert result['complete_history_proven'] is False
    assert result['admission'] == 'RAW_ONLY'
    assert result['quality_tier'] is None
    assert '100' not in str(result)  # no financial values in public aggregates


@pytest.mark.parametrize('value', ['NaN', 'inf', '-Infinity', '', None, True, 'bad'])
def test_invalid_values_fail_closed(value):
    d = sample(); d['observations'][0]['value'] = value
    with pytest.raises(ValueError, match='value'):
        profile(d)


@pytest.mark.parametrize('changed_value', ['100', '999'])
def test_duplicate_keys_fail_even_if_values_identical(changed_value):
    d = sample(); row = deepcopy(d['observations'][0]); row['value'] = changed_value
    d['observations'].append(row); d['count'] += 1
    with pytest.raises(ValueError, match='duplicate'):
        profile(d)


def test_overlapping_inclusive_revision_intervals_fail():
    d = sample(); d['observations'][1]['realtime_start'] = '2010-02-28'
    with pytest.raises(ValueError, match='overlap'):
        profile(d)


@pytest.mark.parametrize('field,value', [
    ('count', 4), ('count', True), ('offset', 1), ('offset', False),
    ('output_type', 2), ('units', 'pc1'),
    ('observation_end', '2011-12-31'), ('realtime_end', '2024-01-01'),
])
def test_bad_envelope_or_partial_payload_is_not_a_clean_capture(field, value):
    d = sample(); d[field] = value
    with pytest.raises(ValueError):
        profile(d)


@pytest.mark.parametrize('field,value', [
    ('date', '2009-12-31'), ('date', '20100101'),
    ('realtime_start', '2009-12-31'), ('realtime_end', '9999-12-31'),
    ('realtime_end', '2010-01-01'),
])
def test_row_dates_must_be_canonical_and_inside_both_request_windows(field, value):
    d = sample(); d['observations'][0][field] = value
    with pytest.raises(ValueError):
        profile(d)


def test_negative_values_are_not_automatically_invalid_for_rates():
    d = sample(); d['observations'][0]['value'] = '-0.5'
    assert profile(d)['rows'] == 3


def test_unordered_rows_do_not_change_profile_or_mutate_capture():
    d = sample(); d['observations'].reverse(); before = deepcopy(d)
    assert profile(d) == profile(sample())
    assert d == before


def test_empty_response_does_not_prove_no_missing_history():
    d = sample(); d['observations'] = []; d['count'] = 0
    p = profile(d)
    assert p['rows'] == 0 and p['observation_start'] is None
    assert p['complete_history_proven'] is False
