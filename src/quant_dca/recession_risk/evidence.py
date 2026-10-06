"""Scoped admission attestations; content integrity is never a quality decision."""
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import re
from quant_dca.types import Observation,QualityTier,Region
from quant_dca.storage.snapshots import SnapshotRef
from .registry import text,immutable_tuple


class AdmissionStatus(StrEnum):
    ADMITTED='ADMITTED'
    RAW_ONLY='RAW_ONLY'
    MISSING='MISSING'
    UNAVAILABLE='UNAVAILABLE'
    UNSUPPORTED_FOR_PIT='UNSUPPORTED_FOR_PIT'
    REQUIRES_MANUAL_REVIEW='REQUIRES_MANUAL_REVIEW'


@dataclass(frozen=True,slots=True,kw_only=True)
class Admission:
    status: AdmissionStatus
    source: str
    series: str
    region: Region
    monetary_jurisdiction: str
    unit: str
    currency: str | None
    start: str
    end: str
    source_snapshot_hash: str
    quality: QualityTier | None
    evidence_refs: tuple[str,...]
    availability_rule: str

    def __post_init__(self):
        if not isinstance(self.status,AdmissionStatus) or not isinstance(self.region,Region): raise TypeError('ADMISSION_ENUMS')
        for v in (self.source,self.series,self.monetary_jurisdiction,self.unit): text(v)
        if self.currency is not None: text(self.currency)
        if not re.fullmatch('[0-9a-f]{64}',self.source_snapshot_hash): raise ValueError('SOURCE_HASH_REQUIRED')
        if not date(2010,1,1)<=date.fromisoformat(self.start)<=date.fromisoformat(self.end)<=date(2023,12,31):
            raise ValueError('ADMISSION_DEVELOPMENT_BOUNDARY')
        immutable_tuple(self.evidence_refs)
        for v in self.evidence_refs: text(v)
        if self.status is AdmissionStatus.ADMITTED:
            if not isinstance(self.quality,QualityTier) or not self.evidence_refs: raise ValueError('ADMISSION_EVIDENCE_REQUIRED')
            text(self.availability_rule)
        elif self.quality is not None:
            raise ValueError('UNADMITTED_QUALITY_PROHIBITED')


@dataclass(frozen=True,slots=True)
class InputEvidence:
    observation: Observation
    admission: Admission
    snapshot: SnapshotRef

    def __post_init__(self):
        if not isinstance(self.observation,Observation) or not isinstance(self.admission,Admission) or not isinstance(self.snapshot,SnapshotRef):
            raise TypeError('CANONICAL_EVIDENCE_REQUIRED')
