from dataclasses import replace
from datetime import datetime, timezone
import pytest
from quant_dca.recession_risk.registry import load_config
from quant_dca.recession_risk.evidence import Admission,AdmissionStatus,InputEvidence
from quant_dca.types import Observation,QualityTier
from quant_dca.snapshot_contracts import evidence_frame
from quant_dca.storage.snapshots import write_snapshot


def ts(day='2020-06-15',hour=21):
    return datetime.fromisoformat(day).replace(hour=hour,tzinfo=timezone.utc)


@pytest.fixture
def cfg(): return load_config()


@pytest.fixture
def make_evidence(tmp_path,cfg):
    def make(name='us_gdp_growth', *, date='2020-06-01', available=None, value=2.0,
             published='default', revised=None, quality=QualityTier.B,
             status=AdmissionStatus.ADMITTED, observation_changes=None, admission_changes=None):
        definition=next(i for i in cfg.inputs if i.name==name)
        available=available or ts('2020-06-10',12)
        row=Observation(series=definition.series,entity_id=None,observation_date=date,value=value,
            available_at=available,published_at=available if published=='default' else published,
            revised_at=revised,source='fixture',revision_id=available.isoformat(),quality=quality,
            region=definition.region,unit=definition.unit,currency=definition.currency)
        if observation_changes:row=replace(row,**observation_changes)
        ref=write_snapshot(evidence_frame(row),'canonical',row.available_at,root=tmp_path)
        a=Admission(status=status,source=row.source,series=row.series,region=definition.region,
            monetary_jurisdiction=definition.monetary_jurisdiction,unit=definition.unit,currency=definition.currency,
            start='2010-01-01',end='2023-12-31',source_snapshot_hash=ref.sha256,
            quality=quality if status is AdmissionStatus.ADMITTED else None,
            evidence_refs=('synthetic admission test',),availability_rule='explicit synthetic release clock')
        if admission_changes:a=replace(a,**admission_changes)
        return InputEvidence(row,a,ref)
    return make
