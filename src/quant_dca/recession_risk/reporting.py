"""Deterministic diagnostic artifacts in a separate root, never a model feature store."""
import csv
from dataclasses import asdict
from pathlib import Path
from quant_dca.snapshot_contracts import evidence_frame
from quant_dca.storage.snapshots import write_snapshot
from .contracts import MacroRiskSnapshot
from .engine import build_snapshot


def write_diagnostic(snapshot: MacroRiskSnapshot,*,config,evidence,root='data/recession_risk'):
    """Replay canonical evidence before any write; hashes alone do not grant admission."""
    if type(snapshot) is not MacroRiskSnapshot:
        raise TypeError('DIAGNOSTIC_SNAPSHOT_REQUIRED')
    replayed = build_snapshot(as_of=snapshot.as_of, region=snapshot.region,
        monetary_jurisdiction=snapshot.monetary_jurisdiction, config=config, evidence=evidence)
    if snapshot != replayed:
        raise ValueError('DIAGNOSTIC_REPLAY_MISMATCH')
    return write_snapshot(evidence_frame(snapshot),'point_in_time',snapshot.as_of,root=root,
        source_hashes=snapshot.source_snapshot_hashes,schema_version='recession-core-v1')


def write_dictionary(config,path):
    rows=[{**asdict(i),'config_version':config.version,'config_hash':config.sha256,
           'availability_rule':'canonical available_at and publication/revision <= regional eligible EOD',
           'admission_rule':'content-bound reviewed Admission required; no automatic provider tier',
           'missing_rule':'UNKNOWN; never healthy; no backward fill'} for i in config.inputs]
    destination=Path(path);destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=tuple(rows[0]));writer.writeheader();writer.writerows(rows)
