#!/usr/bin/env python3
"""Derive P99/P1 limits from qualified successful Dev controls; no defaults."""
import argparse
import json
import math
from pathlib import Path
from evidence import file_hash
from invariants import RULES,threshold_keys


def quantile(values,q):
    values=sorted(values);position=(len(values)-1)*q;lo=int(position);hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(position-lo)


def derive(controls,margins):
    values={k:[] for k in threshold_keys()};provenance=[]
    directions={s:op for rule in RULES.values() for _,op,s in rule if s in values}
    for control in map(Path,controls):
        manifest=json.loads((control/'manifest.json').read_text());oracle=json.loads((control/'oracle.json').read_text())
        if not (manifest.get('seed_group')=='dev' and manifest.get('qualified') is True and oracle['oracle_verdict']=='PASS'):
            raise ValueError('Calibration requires qualified oracle-PASS Dev controls; no held-out/unqualified data')
        source=control/'logs/normalized.jsonl'
        provenance.append({'run':str(control),'manifest_sha256':file_hash(control/'manifest.json'),'trace_sha256':file_hash(source)})
        for line in source.read_text().splitlines():
            event=json.loads(line)
            for rule in RULES.values():
                for field,_,key in rule:
                    if key in values and field in event.get('measurements',{}):
                        value=event['measurements'][field]
                        if not isinstance(value,(float,int)) or isinstance(value,bool) or not math.isfinite(value):
                            raise ValueError('Control measurement must be finite numeric')
                        values[key].append(value)
    thresholds={};derivations={}
    for key,distribution in values.items():
        if not distribution or key not in margins:
            thresholds[key]=None;continue
        q=.01 if directions[key]=='ge' else .99
        baseline=quantile(distribution,q)
        margin=margins[key]
        if (not isinstance(margin,dict) or 'value' not in margin or not margin.get('justification')
                or not isinstance(margin['value'],(int,float)) or isinstance(margin['value'],bool)
                or not math.isfinite(margin['value']) or margin['value']<0):
            raise ValueError('Each margin needs an explicit value and justification')
        thresholds[key]=baseline-margin['value'] if directions[key]=='ge' else baseline+margin['value']
        derivations[key]={'n':len(distribution),'quantile':q,'quantile_value':baseline,'margin':margin}
    return dict(schema_version=1,thresholds=thresholds,derivations=derivations,controls=provenance)


def main():
    p=argparse.ArgumentParser();p.add_argument('controls',nargs='+',type=Path);p.add_argument('--margins',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();result=derive(args.controls,json.loads(args.margins.read_text()))
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)

if __name__=='__main__':main()
