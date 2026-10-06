import ast
import hashlib
from pathlib import Path
import pytest

FROZEN={
 'configs/features_v1.yaml':'5cd158753edb0511778c51b023c6306abcb49568da10cc6b9b5be1f2d2634d0d',
 'configs/regimes_v1.yaml':'dd6b69349cef43cae643d6da2c74519e3ba154cb62236d47c82c04437930dcaa',
 'reports/feature-dictionary.csv':'9ae01f5b155b7639fd708462ca072f787f5c678e283544ade22f0e12d482292f',
 'reports/target-dictionary.csv':'e6c120d28c6862dd30fe7a37dcb76076822d77ffaa5d237cb1b31cef3e47e9b8'}


@pytest.mark.parametrize('path,digest',FROZEN.items())
def test_frozen_model_contract_unchanged(path,digest):
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest


def imports(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node,ast.Import):yield from (i.name for i in node.names)
        elif isinstance(node,ast.ImportFrom):yield node.module or ''


def test_diagnostic_has_no_model_target_regime_or_policy_dependency():
    for p in Path('src/quant_dca/recession_risk').glob('*.py'):
        for name in imports(p):
            assert not any(name==f'quant_dca.{d}' or name.startswith(f'quant_dca.{d}.') for d in ('targets','features','models','policy','backtest','regimes'))


def test_model_feature_regime_target_packages_do_not_import_diagnostics():
    for folder in ('features','regimes','targets'):
        for p in Path('src/quant_dca',folder).glob('*.py'):
            assert all('recession_risk' not in name for name in imports(p))
