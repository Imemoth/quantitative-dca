"""Immutable diagnostic output, including the evidence behind every usable measure."""
from dataclasses import dataclass, fields
from datetime import datetime
import math
from types import UnionType
from typing import get_args, get_origin, get_type_hints
from quant_dca.types import QualityTier,Region
from quant_dca.snapshot_contracts import evidence_frame
from quant_dca.storage.snapshots import snapshot_hash
from quant_dca.snapshot_contracts import development_request, assert_selected_evidence_pit


def _matches(value, annotation):
    """Exact contract types exclude mutable lookalikes and mutable subclasses."""
    origin = get_origin(annotation)
    if origin is UnionType:
        return any(_matches(value, member) for member in get_args(annotation))
    if origin is tuple:
        member, ellipsis = get_args(annotation)
        return type(value) is tuple and all(_matches(v, member) for v in value)
    if annotation is float:
        return type(value) in (int, float) and math.isfinite(value)
    return type(value) is annotation


class _ImmutableOutput:
    __slots__ = ()

    def __post_init__(self):
        hints = get_type_hints(type(self))
        for field in fields(self):
            if not _matches(getattr(self, field.name), hints[field.name]):
                raise TypeError('IMMUTABLE_OUTPUT_CONTRACT:' + field.name)


@dataclass(frozen=True,slots=True)
class EvidenceReference(_ImmutableOutput):
    input_name: str
    source: str
    revision_id: str
    observation_date: str
    available_at: datetime
    published_at: datetime | None
    revised_at: datetime | None
    source_snapshot_hash: str
    admission_hash: str
    admission_evidence_refs: tuple[str,...]


@dataclass(frozen=True,slots=True)
class InputMeasure(_ImmutableOutput):
    name: str
    pillar: str
    value: float | None
    unit: str
    status: str
    quality: QualityTier | None
    freshness: float
    publication_certainty: float
    evidence: EvidenceReference | None


@dataclass(frozen=True,slots=True)
class PillarState(_ImmutableOutput):
    name: str
    state: str
    evidence_state: str
    reason: str


@dataclass(frozen=True,slots=True)
class Driver(_ImmutableOutput):
    pillar: str
    rule: str
    polarity: str
    description: str
    input_name: str
    value: float
    evidence: EvidenceReference


@dataclass(frozen=True,slots=True)
class MacroRiskSnapshot(_ImmutableOutput):
    as_of: datetime
    effective_eod: datetime | None
    region: Region
    monetary_jurisdiction: str
    pillars: tuple[PillarState,...]
    input_measures: tuple[InputMeasure,...]
    evidence_references: tuple[EvidenceReference,...]
    admission_state: str
    quality: QualityTier | None
    dominant_scenario: str
    secondary_scenario: str | None
    evidence_completeness: float
    critical_input_completeness: float
    data_confidence: float
    drivers: tuple[Driver,...]
    max_input_available_at: datetime | None
    publication_timestamps: tuple[datetime,...]
    config_hash: str
    source_snapshot_hashes: tuple[str,...]
    reason_codes: tuple[str,...]

    def __post_init__(self):
        _ImmutableOutput.__post_init__(self)
        development_request(self.as_of, self.as_of, 'train')
        if self.effective_eod is not None:
            development_request(self.effective_eod, self.effective_eod, 'train')
            if self.effective_eod > self.as_of:
                raise ValueError('EOD_AFTER_PREDICTION')
        assert_selected_evidence_pit(self, self.effective_eod or self.as_of)
        for value in (self.evidence_completeness, self.critical_input_completeness, self.data_confidence):
            if not 0 <= value <= 1:
                raise ValueError('OUTPUT_FRACTION_RANGE')
        if not self.evidence_references and (self.data_confidence or self.evidence_completeness
                or self.critical_input_completeness or self.dominant_scenario != 'INSUFFICIENT_EVIDENCE'
                or self.secondary_scenario is not None or self.drivers):
            raise ValueError('EVIDENCE_REQUIRED_FOR_DIAGNOSTIC_STATE')

    @property
    def sha256(self):
        return snapshot_hash(evidence_frame(self))
