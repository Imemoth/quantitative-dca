"""Aggregate raw FRED inspection, without interpreting clocks or assigning tiers."""
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from quant_dca.providers.base import bounded_interval


def profile_fred(document: dict, *, request_bounds: dict) -> dict:
    """Validate one output_type=1 capture against its independently retained request.

    Bounds echoed in a response do not establish what was sent. The caller must
    supply the original request receipt, not infer it from response rows. Counts
    establish payload completeness only, never complete history or PIT admission.
    Different vintage chunks are inspected separately; they are not stitched here.
    """
    keys = ('observation_start', 'observation_end', 'realtime_start', 'realtime_end')
    if set(request_bounds) != set(keys):
        raise ValueError('Explicit observation and vintage request bounds required')
    for start, end in (keys[:2], keys[2:]):
        bounded_interval(request_bounds[start], request_bounds[end])
        if request_bounds[start] < '2010-01-01':
            raise ValueError('Request predates development period')
    if any(document.get(k) != request_bounds[k] for k in keys):
        raise ValueError('Response/request envelope mismatch')
    rows = document.get('observations')
    if not isinstance(rows, list):
        raise ValueError('Observation list required')
    if type(document.get('count')) is not int or document['count'] != len(rows):
        raise ValueError('Incomplete payload count')
    if type(document.get('offset')) is not int or document['offset'] != 0:
        raise ValueError('Partial payload offset')
    if type(document.get('output_type')) is not int or document['output_type'] != 1 or document.get('units') != 'lin':
        raise ValueError('Unsupported transformed response')
    seen = set()
    intervals = defaultdict(list)
    missing = left = right = 0
    for row in rows:
        if not isinstance(row, dict) or not all(k in row for k in ('date', 'realtime_start', 'realtime_end', 'value')):
            raise ValueError('Malformed observation')
        day, first, last = row['date'], row['realtime_start'], row['realtime_end']
        bounded_interval(day, day)
        bounded_interval(first, last)
        if not request_bounds['observation_start'] <= day <= request_bounds['observation_end']:
            raise ValueError('Observation outside request')
        if not request_bounds['realtime_start'] <= first <= last <= request_bounds['realtime_end']:
            raise ValueError('Vintage outside request')
        key = day, first, last
        if key in seen:
            raise ValueError('duplicate observation/vintage key')
        seen.add(key)
        intervals[day].append((first, last))
        value = row['value']
        if value == '.':
            missing += 1
        else:
            try:
                if not isinstance(value, str) or not Decimal(value).is_finite():
                    raise ValueError('Invalid numeric value')
            except InvalidOperation:
                raise ValueError('Invalid numeric value') from None
        left += first == request_bounds['realtime_start']
        right += last == request_bounds['realtime_end']
    for values in intervals.values():
        ordered = sorted(values)
        if any(b[0] <= a[1] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('overlapping vintage intervals')
    return {
        'rows': len(rows), 'distinct_observation_dates': len(intervals),
        'missing_value_rows': missing,
        'observation_start': min(intervals, default=None),
        'observation_end': max(intervals, default=None),
        'left_boundary_intervals': left, 'right_boundary_intervals': right,
        'raw_structure': 'PASS', 'complete_history_proven': False,
        'admission': 'RAW_ONLY', 'quality_tier': None,
    }
