"""Configured deterministic diagnostic rules. Default configuration has no rules."""
from bisect import bisect_right
from dataclasses import replace
from .contracts import Driver


def evaluate_rules(pillars,measures,critical_completeness,config):
    """Bands are [lower,upper); ordered scenario conjunctions are not probabilities."""
    by_name={m.name:m for m in measures}
    states={p.name:p for p in pillars}
    drivers=[]
    for rule in config.rules:
        measure=by_name.get(rule.input_name)
        if measure is None or measure.status!='ADMITTED':continue
        pillar=states[measure.pillar]
        if pillar.evidence_state!='COMPLETE_EVIDENCE':continue
        band=bisect_right(rule.bounds,measure.value)
        state=rule.states[band]
        states[pillar.name]=replace(pillar,state=state,reason=rule.name)
        if state!='UNKNOWN':
            drivers.append(Driver(pillar.name,rule.name,rule.polarities[band],rule.descriptions[band],
                                  measure.name,measure.value,measure.evidence))
    matched=[]
    if critical_completeness==1.0:
        for rule in config.scenario_rules:
            if all(states[p].state==s for p,s in rule.when):matched.append(rule.scenario)
    dominant=matched[0] if matched else 'INSUFFICIENT_EVIDENCE'
    secondary=matched[1] if len(matched)>1 else None
    return tuple(states[p.name] for p in pillars),tuple(drivers),dominant,secondary
