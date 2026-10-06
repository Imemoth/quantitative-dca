"""Versioned, immutable diagnostic-only definitions; no model feature mutation."""
from dataclasses import dataclass
from pathlib import Path
import math
import re
import yaml
from quant_dca.snapshot_contracts import evidence_frame
from quant_dca.storage.snapshots import snapshot_hash
from quant_dca.types import QualityTier, Region

PILLARS = frozenset({'growth','labor','inflation','policy','curve','credit','conditions','stress'})
IDENTITIES = frozenset({'ticker','security_id','entity_id','isin','cusip'})
UNITS = frozenset({'percent_yoy','percent','percentage_points','index_points','ratio_change_3m'})


def text(value):
    if type(value) is not str or not value.strip():
        raise ValueError('EXPLICIT_TEXT_REQUIRED')


def identifier(value):
    text(value)
    if not re.fullmatch('[a-z][a-z0-9_]*',value) or value in IDENTITIES:
        raise ValueError('INVALID_DIAGNOSTIC_IDENTIFIER')


def immutable_tuple(value):
    if type(value) is not tuple:
        raise TypeError('IMMUTABLE_TUPLE_REQUIRED')


@dataclass(frozen=True, slots=True)
class InputDefinition:
    name: str
    pillar: str
    series: str
    region: Region
    monetary_jurisdiction: str
    unit: str
    currency: str | None
    max_age_days: int
    critical: bool
    quality_floor: QualityTier
    measure_definition: str

    def __post_init__(self):
        identifier(self.name)
        if self.pillar not in PILLARS or not isinstance(self.region,Region) or self.region is Region.GLOBAL:
            raise ValueError('INVALID_REGION_OR_PILLAR')
        for v in (self.series,self.monetary_jurisdiction,self.measure_definition): text(v)
        if self.series.lower() in IDENTITIES or self.unit not in UNITS:
            raise ValueError('INVALID_DIAGNOSTIC_UNIT_OR_IDENTITY')
        if self.currency is not None: text(self.currency)
        if type(self.max_age_days) is not int or self.max_age_days <= 0 or type(self.critical) is not bool:
            raise ValueError('INVALID_INPUT_POLICY')
        if not isinstance(self.quality_floor,QualityTier): raise ValueError('INVALID_QUALITY')


@dataclass(frozen=True, slots=True)
class PillarDefinition:
    name: str
    states: tuple[str,...]

    def __post_init__(self):
        immutable_tuple(self.states)
        if self.name not in PILLARS or 'UNKNOWN' not in self.states or len(set(self.states))!=len(self.states):
            raise ValueError('INVALID_PILLAR_VOCABULARY')
        for s in self.states: text(s)


@dataclass(frozen=True, slots=True)
class Context:
    region: Region
    monetary_jurisdiction: str
    exchange: str

    def __post_init__(self):
        # Explicit supported V1 diagnostic contexts; EU membership is not a currency area.
        if (self.region,self.monetary_jurisdiction,self.exchange) not in (
            (Region.US,'FED','XNYS'),(Region.EU,'ECB','XETR')):
            raise ValueError('UNSUPPORTED_CONTEXT')


@dataclass(frozen=True, slots=True)
class BandRule:
    name: str
    input_name: str
    bounds: tuple[float,...]
    states: tuple[str,...]
    polarities: tuple[str,...]
    descriptions: tuple[str,...]

    def __post_init__(self):
        identifier(self.name); identifier(self.input_name)
        for values in (self.bounds,self.states,self.polarities,self.descriptions): immutable_tuple(values)
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in self.bounds):
            raise ValueError('INVALID_RULE_BOUND')
        if tuple(sorted(set(self.bounds)))!=self.bounds or not self.bounds:
            raise ValueError('ORDERED_UNIQUE_BOUNDS_REQUIRED')
        if any(len(x)!=len(self.bounds)+1 for x in (self.states,self.polarities,self.descriptions)):
            raise ValueError('RULE_ARITY')
        if any(p not in ('positive','negative','neutral') for p in self.polarities):
            raise ValueError('RULE_POLARITY')
        for s in self.states+self.descriptions: text(s)


@dataclass(frozen=True, slots=True)
class ScenarioRule:
    scenario: str
    when: tuple[tuple[str,str],...]

    def __post_init__(self):
        text(self.scenario); immutable_tuple(self.when)
        if not self.when: raise ValueError('EMPTY_SCENARIO')
        for condition in self.when:
            immutable_tuple(condition)
            if len(condition)!=2: raise ValueError('INVALID_CONDITION')
        if len({p for p,s in self.when})!=len(self.when): raise ValueError('DUPLICATE_CONDITION')


@dataclass(frozen=True, slots=True)
class DiagnosticConfig:
    version: str
    pillars: tuple[PillarDefinition,...]
    inputs: tuple[InputDefinition,...]
    contexts: tuple[Context,...]
    scenarios: tuple[str,...]
    quality_weights: tuple[tuple[str,float],...]
    rules: tuple[BandRule,...] = ()
    scenario_rules: tuple[ScenarioRule,...] = ()

    def __post_init__(self):
        text(self.version)
        for value in (self.pillars,self.inputs,self.contexts,self.scenarios,self.quality_weights,self.rules,self.scenario_rules):
            immutable_tuple(value)
        if len(self.pillars)!=8 or {p.name for p in self.pillars}!=PILLARS: raise ValueError('EIGHT_PILLARS_REQUIRED')
        if not self.inputs or len({i.name for i in self.inputs})!=len(self.inputs): raise ValueError('DUPLICATE_OR_EMPTY_INPUTS')
        keys=[(i.series,i.region,i.monetary_jurisdiction) for i in self.inputs]
        if len(set(keys))!=len(keys): raise ValueError('DUPLICATE_SERIES')
        if len(set(self.contexts))!=len(self.contexts): raise ValueError('DUPLICATE_CONTEXT')
        for i in self.inputs:
            if self.context(i.region,i.monetary_jurisdiction) is None: raise ValueError('INPUT_CONTEXT_MISSING')
        if 'INSUFFICIENT_EVIDENCE' not in self.scenarios or len(set(self.scenarios))!=len(self.scenarios):
            raise ValueError('INVALID_SCENARIOS')
        for s in self.scenarios: text(s)
        for pair in self.quality_weights: immutable_tuple(pair)
        w=dict(self.quality_weights)
        if len(self.quality_weights)!=3 or set(w)!=set('ABC') or any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1 for x in w.values()) or not w['A']>=w['B']>=w['C']:
            raise ValueError('INVALID_QUALITY_WEIGHTS')
        input_map={i.name:i for i in self.inputs}; pillar_map={p.name:p for p in self.pillars}
        used=set()
        for rule in self.rules:
            if not isinstance(rule,BandRule) or rule.input_name not in input_map: raise ValueError('UNKNOWN_RULE_INPUT')
            inp=input_map[rule.input_name]; key=(inp.region,inp.monetary_jurisdiction,inp.pillar)
            if key in used: raise ValueError('ONE_RULE_PER_PILLAR_CONTEXT')
            used.add(key)
            if not set(rule.states)<=set(pillar_map[inp.pillar].states): raise ValueError('UNKNOWN_RULE_STATE')
        if len({r.name for r in self.rules})!=len(self.rules): raise ValueError('DUPLICATE_RULE')
        for r in self.scenario_rules:
            if not isinstance(r,ScenarioRule) or r.scenario not in self.scenarios or r.scenario=='INSUFFICIENT_EVIDENCE':
                raise ValueError('UNKNOWN_SCENARIO')
            for p,s in r.when:
                if p not in pillar_map or s not in pillar_map[p].states or s=='UNKNOWN': raise ValueError('INVALID_SCENARIO_CONDITION')
        if len({r.scenario for r in self.scenario_rules})!=len(self.scenario_rules): raise ValueError('DUPLICATE_SCENARIO')

    def context(self,region,jurisdiction):
        return next((c for c in self.contexts if c.region==region and c.monetary_jurisdiction==jurisdiction),None)

    @property
    def sha256(self):
        return snapshot_hash(evidence_frame(self))


def config_from_mapping(data):
    if set(data)!={'version','pillars','inputs','contexts','scenarios','quality_weights','rules','scenario_rules'}:
        raise ValueError('CONFIG_FIELDS')
    inputs=tuple(InputDefinition(**{**i,'region':Region(i['region']),'quality_floor':QualityTier(i['quality_floor'])}) for i in data['inputs'])
    return DiagnosticConfig(
        version=data['version'],pillars=tuple(PillarDefinition(k,tuple(v)) for k,v in data['pillars'].items()),
        inputs=inputs,contexts=tuple(Context(Region(c['region']),c['monetary_jurisdiction'],c['exchange']) for c in data['contexts']),
        scenarios=tuple(data['scenarios']),quality_weights=tuple(sorted(data['quality_weights'].items())),
        rules=tuple(BandRule(**{**r,**{k:tuple(r[k]) for k in ('bounds','states','polarities','descriptions')}}) for r in data['rules']),
        scenario_rules=tuple(ScenarioRule(r['scenario'],tuple(tuple(v) for v in r['when'])) for r in data['scenario_rules']))


def load_config(path=Path('configs/recession_risk_v1.yaml')):
    return config_from_mapping(yaml.safe_load(Path(path).read_text()))
