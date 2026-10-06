#!/usr/bin/env python3
"""Validate seed governance without generating or inspecting held-out layouts."""
import argparse
import json
from pathlib import Path
import yaml


def expand(group):
    result=set(group.get('explicit', []))
    assert all(isinstance(n,int) and not isinstance(n,bool) and n>=0 for n in result)
    for bounds in group.get('inclusive_ranges', []):
        assert len(bounds)==2 and all(isinstance(n,int) and not isinstance(n,bool) for n in bounds)
        lo,hi=bounds
        assert 0<=lo<=hi
        values=set(range(lo,hi+1))
        assert not result & values, 'Duplicated seed within a group'
        result.update(values)
    return result


def validate(policy):
    groups={name:expand(policy[name]) for name in ('dev','test_a','reserve_m4')}
    assert len(groups['test_a'])>=60
    for name in ('test_a','reserve_m4'):
        assert len(groups[name])==policy[name]['count']
        assert policy[name]['used'] is False
    for a,b in (('dev','test_a'),('dev','reserve_m4'),('test_a','reserve_m4')):
        assert not groups[a]&groups[b], f'{a}/{b} overlap'
    assert set(range(10))<=groups['dev']
    return {k:len(v) for k,v in groups.items()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('policy',nargs='?',type=Path,default=Path(__file__).with_name('seeds.yaml'))
    args=parser.parse_args()
    print(json.dumps(validate(yaml.safe_load(args.policy.read_text())),indent=2))


if __name__=='__main__':
    main()
