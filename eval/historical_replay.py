#!/usr/bin/env python3
"""Replay supported physical I19 facts from Dev history, never held-out data."""
import argparse
import json
from pathlib import Path
from backcheck import rows
from normalize import normalized
from analyzer import analyze


def replay(folder):
    manifest=json.loads((folder/'manifest.json').read_text())
    observations=list(rows(folder/'observations.jsonl.gz'))
    events=[{'topic':'/mission/state','sim_s':r['sim_s'],'wall_s':r.get('wall_s'),
             'data':{'data':r['data']}} for r in observations if r.get('topic')=='/mission/state']
    source=folder/('isaac.log.gz' if manifest['backend']=='isaac' else 'physical.jsonl.gz')
    from truth import gazebo_packet
    dims={t['model']:[t['diameter'],t['diameter'],t['height']] for t in manifest['targets']}
    for row in rows(source):
        if manifest['backend']=='gazebo':packet=gazebo_packet(row,dims)
        elif row.get('event')=='state':
            packet=dict(sim_s=row['time_sim_s'],robot=None,
                        objects={name:dict(xyz_m=p) for name,p in row.get('targets_world_m',{}).items()})
        else:continue
        events.append({'topic':'/eval/ground_truth/state','sim_s':packet['sim_s'],'data':{'data':json.dumps(packet)}})
    events.sort(key=lambda e:e['sim_s'])
    facts=normalized(events,manifest)
    facts=[dict(e,invariants=['I19']) for e in facts if 'nonrequested_displacement_m' in e['measurements']]
    result=analyze(facts,{},'ABORT','FAIL')
    result['historical_unqualified']=True;result['supported_checks']=['I19']
    # Robot truth absent in Isaac log: absence is UNKNOWN, not a physics breach.
    result['limitation']='Replay only displacement; timing, TF, service UUIDs, host qualification and candidate geometry unavailable'
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args()
    with args.output.open('x') as f:json.dump(replay(args.folder),f,indent=2,allow_nan=False)

if __name__=='__main__':main()
