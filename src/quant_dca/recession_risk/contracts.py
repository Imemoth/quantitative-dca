"""Immutable diagnostic output, including the evidence behind every usable measure."""
from dataclasses import dataclass
from datetime import datetime
from quant_dca.types import QualityTier,Region
from quant_dca.snapshot_contracts import evidence_frame
from quant_dca.storage.snapshots import snapshot_hash


@dataclass(frozen=True,slots=True)
class EvidenceReference:
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
class InputMeasure:
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
class PillarState:
    name: str
    state: str
    evidence_state: str
    reason: str


@dataclass(frozen=True,slots=True)
class Driver:
    pillar: str
    rule: str
    polarity: str
    description: str
    input_name: str
    value: float
    evidence: EvidenceReference


@dataclass(frozen=True,slots=True)
class MacroRiskSnapshot:
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

    @property
    def sha256(self):
        return snapshot_hash(evidence_frame(self))
