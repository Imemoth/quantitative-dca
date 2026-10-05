import csv
from pathlib import Path
import subprocess
import sys

import pytest
from quant_dca.features.registry import FeatureRegistry


def test_dictionaries_are_deterministic_complete_and_describe_actual_target_windows(tmp_path):
    try:
        from quant_dca.dictionaries import generate_dictionaries
    except ImportError:
        pytest.fail('dictionary generator missing')
    generate_dictionaries(tmp_path)
    feature_path=tmp_path/'feature-dictionary.csv'
    target_path=tmp_path/'target-dictionary.csv'
    first=(feature_path.read_bytes(),target_path.read_bytes())
    generate_dictionaries(tmp_path)
    assert first==(feature_path.read_bytes(),target_path.read_bytes())
    features=list(csv.DictReader(feature_path.open()))
    active=[r for r in features if r['status']=='registered_base']
    assert {r['name'] for r in active}==set(FeatureRegistry.v1().names())
    assert len(active)==81 and len(features)==94
    assert sum(r['status']=='reserved_candidate_slot' for r in features)==13
    assert {r['quality_floor'] for r in features if r['status']=='reserved_candidate_slot'}=={'C'}
    assert all(r['producer'] and r['availability_rule'] for r in features)
    targets={r['name']:r for r in csv.DictReader(target_path.open())}
    assert len(targets)==20
    assert targets['return_5d_local']['reference_execution']=='O0 -> O5'
    assert targets['return_60d_huf']['reference_execution']=='O0 -> O60'
    assert targets['better_entry_5d_local']['reference_execution']=='O0; wait O0..O4'
    assert targets['better_entry_20d_huf']['reference_execution']=='O0; wait O0..O19'
    assert 'payable' in targets['return_20d_huf']['currency_basis']
    assert all('per-horizon' in r['target_end_rule'] for r in targets.values())
    result=subprocess.run([sys.executable,'-m','quant_dca.dictionaries','--output',str(tmp_path/'cli')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert (tmp_path/'cli'/'feature-dictionary.csv').read_bytes()==first[0]
