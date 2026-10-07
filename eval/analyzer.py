#!/usr/bin/env python3
"""Offline first-violation analyzer. Missing evidence remains UNCLASSIFIED."""
import argparse
import json
from pathlib import Path
from evidence import atomic_json
from invariants import RULES,evaluate


def analyze(events,thresholds,mission_verdict='UNOBSERVED',oracle_verdict='UNSCORABLE',require_catalog_coverage=False):
    # Source simulation timestamp, then receive sequence, then catalog order.
    ordered=sorted(enumerate(events),key=lambda p:(p[1]['sim_s'],p[0]))
    violations=[];coverage={i:{'pass':0,'fail':0,'unknown':0,'missing':set(),'measured_fields':set()} for i in RULES}
    for sequence,event in ordered:
        if 'measurements' not in event:continue
        selected=event.get('invariants',list(RULES))
        for invariant in selected:
            result=evaluate(invariant,event['measurements'],thresholds)
            key='pass' if result['holds'] is True else 'fail' if result['holds'] is False else 'unknown'
            coverage[invariant][key]+=1;coverage[invariant]['missing'].update(result['missing'])
            coverage[invariant]['measured_fields'].update(result['observed_fields'])
            if result['holds'] is False:
                violations.append(dict(invariant=invariant,mission_stage=event.get('mission_stage','UNKNOWN'),
                                       sim_s=event['sim_s'],sequence=sequence,details=result['failures']))
    first=violations[0] if violations else None
    work_items=[i for i,v in coverage.items() if not {field for field,_,_ in RULES[i]}<=v['measured_fields']]
    complete=not work_items
    verified_first=first if not require_catalog_coverage or complete else None
    label=verified_first['invariant'] if verified_first else 'NONE' if (oracle_verdict=='PASS' and mission_verdict=='COMPLETE' and complete and not first) else 'UNCLASSIFIED'
    window=None
    if first:
        # Exactly ten simulation seconds, centered on first divergence.
        begin=first['sim_s']-5;end=first['sim_s']+5
        window={'start_sim_s':begin,'end_sim_s':end,
                'events':[dict(event,receive_sequence=sequence) for sequence,event in ordered if begin<=event['sim_s']<=end]}
    for data in coverage.values():
        data['missing']=sorted(data['missing']);data['measured_fields']=sorted(data['measured_fields'])
    return {'schema_version':1,'first_violated_invariant':label,'first_violation':verified_first,
            'first_supported_violation':first,'catalog_measurements_complete':complete,
            'earliest_cause_verified':bool(first and complete),'require_catalog_coverage':require_catalog_coverage,
            'mission_stage':verified_first['mission_stage'] if verified_first else None,'simulation_timestamp':verified_first['sim_s'] if verified_first else None,
            'context_window':window,'violations':violations,'coverage':coverage,
            'analyzer_work_items':work_items,
            'qualification_exclusion_separate':True}


def run(directory,threshold_file):
    directory=Path(directory)
    events=[json.loads(line) for line in (directory/'logs/normalized.jsonl').read_text().splitlines() if line.strip()]
    oracle=json.loads((directory/'oracle.json').read_text())
    result=analyze(events,json.loads(Path(threshold_file).read_text())['thresholds'],oracle.get('mission_verdict'),oracle.get('oracle_verdict'),require_catalog_coverage=True)
    atomic_json(directory/'analysis.json',result);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--thresholds',type=Path,default=Path(__file__).with_name('thresholds.json'))
    args=p.parse_args();run(args.run,args.thresholds)

if __name__=='__main__':main()
