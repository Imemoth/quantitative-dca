"""Shared development-envelope and immutable evidence contracts; no target values."""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import json
import math

import pandas as pd

from quant_dca.storage.snapshots import read_snapshot_metadata, snapshot_hash


def development_request(start, end, role):
    # This must run before any data iterable, source read or producer call.
    if role not in ('train', 'validation'):
        raise ValueError('DEVELOPMENT_PARTITION_REQUIRED')
    for value in (start, end):
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('AWARE_DEVELOPMENT_TIMESTAMP_REQUIRED')
        if not 2010 <= value.astimezone(timezone.utc).year <= 2023:
            raise ValueError('DEVELOPMENT_BOUNDARY')
    if start > end:
        raise ValueError('REQUEST_BOUNDARY_ORDER')


def evidence_value(value):
    """Strict deterministic serialization, excluding opaque objects/fetch hooks."""
    if isinstance(value, Enum):
        return value.value
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('NONFINITE_EVIDENCE')
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('AWARE_EVIDENCE_REQUIRED')
        return {'timestamp': value.astimezone(timezone.utc).isoformat()}
    if isinstance(value, date):
        return {'date': value.isoformat()}
    if isinstance(value, timedelta):
        return {'duration_seconds': value.total_seconds()}
    if is_dataclass(value) and not isinstance(value, type):
        return {'record_type': type(value).__name__, **{f.name:evidence_value(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, Mapping):
        return {str(key):evidence_value(item) for key,item in sorted(value.items(), key=lambda x:str(x[0]))}
    if type(value) in (tuple, list):
        return [evidence_value(item) for item in value]
    raise TypeError('MATERIALIZED_EVIDENCE_REQUIRED:' + type(value).__name__)


def evidence_frame(value):
    return pd.DataFrame({'evidence_json':[json.dumps(evidence_value(value), sort_keys=True, separators=(',',':'))]})


def verify_evidence(value, reference, *, as_of):
    metadata = read_snapshot_metadata(reference)
    if metadata['layer'] not in ('canonical', 'point_in_time'):
        raise ValueError('CANONICAL_SOURCE_EVIDENCE_REQUIRED')
    if datetime.fromisoformat(metadata['as_of']) > as_of:
        raise ValueError('SOURCE_SNAPSHOT_AFTER_REQUEST')
    if metadata['data_sha256'] != snapshot_hash(evidence_frame(value)):
        raise ValueError('SOURCE_EVIDENCE_CONTENT_MISMATCH')
    return metadata['sha256']


def bounded_evidence(value):
    """Check metadata clocks before computations; inception dates are descriptive."""
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            item = getattr(value, field.name)
            if isinstance(item, datetime) and field.name != 'computed_at':
                development_request(item, item, 'train')
            elif field.name in ('session_date','observation_date','period_end','ex_date','event_date','end_session','prior_session') and item is not None:
                if not 2010 <= date.fromisoformat(item).year <= 2023:
                    raise ValueError('DEVELOPMENT_DEPENDENCY_BOUNDARY')
            elif is_dataclass(item) or isinstance(item, Mapping) or type(item) in (tuple,list):
                bounded_evidence(item)
    elif isinstance(value, Mapping):
        for item in value.values():
            bounded_evidence(item)
    elif type(value) in (tuple,list):
        for item in value:
            bounded_evidence(item)


from dataclasses import dataclass
from quant_dca.universe.membership import UniverseIndex


@dataclass(frozen=True, slots=True, kw_only=True)
class UniverseEvidence:
    """Complete historical index inputs, serializable without exposing model IDs."""
    securities: tuple
    memberships: tuple
    trading_sessions: tuple
    liquidity_metrics: tuple
    fundamental_reports: tuple
    thresholds: object

    def index(self):
        for name in ('securities','memberships','trading_sessions','liquidity_metrics','fundamental_reports'):
            if type(getattr(self,name)) is not tuple:
                raise TypeError('MATERIALIZED_UNIVERSE_REQUIRED')
        bounded_evidence(self)
        return UniverseIndex(**{field.name:getattr(self,field.name) for field in fields(self)})


def assert_selected_evidence_pit(value, cutoff):
    """Selected producer evidence must be knowable; announced future events may be future."""
    if is_dataclass(value) and not isinstance(value,type):
        for field in fields(value):
            item=getattr(value,field.name)
            if field.name in ('available_at','max_input_available_at','published_at','revised_at','verified_at','fixing_at','session_close_at') and item is not None:
                if item > cutoff:
                    raise ValueError('SELECTED_EVIDENCE_AFTER_PREDICTION')
            elif is_dataclass(item) or isinstance(item,Mapping) or type(item) in (tuple,list):
                assert_selected_evidence_pit(item,cutoff)
    elif isinstance(value,Mapping):
        for item in value.values():
            assert_selected_evidence_pit(item,cutoff)
    elif type(value) in (tuple,list):
        for item in value:
            assert_selected_evidence_pit(item,cutoff)
