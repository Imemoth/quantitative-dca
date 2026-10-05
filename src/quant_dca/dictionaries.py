"""Deterministic software-contract dictionaries, not a research freeze.

Run: python -m quant_dca.dictionaries --output reports
"""
import argparse
import csv
from pathlib import Path

from quant_dca.features.registry import FeatureRegistry
from quant_dca.features.snapshots import PRODUCER_DOMAINS
from quant_dca.regimes.interpretable import STATES


def _write(path,rows):
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=tuple(rows[0]),lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def generate_dictionaries(output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    features=[]
    for definition in FeatureRegistry.v1():
        producer=next(kind.__name__ for kind,domains in PRODUCER_DOMAINS.items() if definition.domain in domains)
        candidate=''
        if definition.domain=='structural':
            candidate='structural-software-candidate-v1; US=0 EU=1; explicit controlled sector mapping; USD cap edges=2e9|10e9|200e9; beta edges=0.8|1.2; equality enters upper bucket; beta=252 aligned adjusted daily returns; no empirical selection'
        if definition.name=='vix_acceleration_raw':
            candidate='index-point acceleration Vt-2*Vt-20+Vt-40; requires 43 actual source sessions'
        features.append(dict(name=definition.name,domain=definition.domain,formula_transform=definition.formula+'; '+definition.transform,
            raw_source='; '.join(d.name for d in definition.raw_dependencies),lookback_sessions=definition.lookback_sessions,
            availability_rule=definition.availability_rule,normalization=definition.normalization,applicability=definition.applicability,
            missing_data_rule=definition.missing_policy,quality_floor=definition.quality_floor.value,producer=producer,
            status='registered_base',candidate_configuration=candidate,registry_version='features-v1'))
    reserved=[(f'regime_interpretable_{s.lower()}_probability','fixed uncalibrated prototype probability') for s in STATES]
    reserved += [(f'regime_state_{i}_probability',f'candidate state {i}; only active when i < fitted n_states; 3..8 states') for i in range(8)]
    for name,formula in reserved:
        features.append(dict(name=name,domain='regime',formula_transform=formula,raw_source='evidenced regional momentum; global VIX; regional high yield spread; train-fit provenance',
            lookback_sessions='candidate-specific',availability_rule='all inputs and train fit-end <= prediction; matched fold/region/source calendar',
            normalization='Task8 fixed reference or Task9 train-only standardization',applicability='explicit active candidate only',
            missing_data_rule='omit inactive slots; no probability padding',quality_floor='C',producer='RegimeFeatureSnapshot',
            status='reserved_candidate_slot',candidate_configuration='software candidate, not a retained winner or selected state count; conservative branch-specific input tier; market C permitted, high yield spread requires B; unsupervised includes training dependencies',registry_version='features-v1'))
    targets=[]
    for horizon in (5,20,60):
        prefixes=('return','direction','executable_min_return','better_entry') if horizon in (5,20) else ('return','direction')
        for prefix in prefixes:
            wait=prefix in ('executable_min_return','better_entry')
            for currency in ('local','huf'):
                targets.append(dict(name=f'{prefix}_{horizon}d_{currency}',horizon=horizon,
                    reference_execution=f'O0; wait O0..O{horizon-1}' if wait else f'O0 -> O{horizon}',
                    economic_adjustment='Foundation economic acquisition cost; split-equivalent units plus entitled unreinvested distributions; gross of transaction costs',
                    currency_basis='native listing currency' if currency=='local' else 'HUF cashflows; execution-date and distribution payable-date FX',
                    target_end_rule=f'per-horizon maximum of O{horizon} evidence, action audit, revisions, distribution payable timestamps and FX availability; censor separately; wait labels also require O{horizon} under Task7 contract',
                    formula=('minimum wait economic cost <= O0 cost * '+('0.985' if horizon==5 else '0.97')) if prefix=='better_entry' else
                        'strictly positive economic holding return' if prefix=='direction' else
                        '(minimum wait economic cost - O0 cost) / O0 cost' if prefix=='executable_min_return' else
                        '(exit economic wealth - O0 cost) / O0 cost',
                    status='software_contract_not_research_admission'))
    _write(output/'feature-dictionary.csv',features)
    _write(output/'target-dictionary.csv',targets)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('reports'))
    generate_dictionaries(parser.parse_args().output)
