"""Curate and compare COCO 2.4 runs; no ROS or control side effects."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('coco23', ROOT.parent / 'coco23/analyze.py')
coco23 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coco23)
coco23.ROOT = ROOT


def curate(runtime):
    for source in sorted(runtime.iterdir()):
        if not source.is_dir() or not (source / 'exits.json').exists():
            continue
        dest = ROOT / source.name
        dest.mkdir(exist_ok=True)
        for path in source.iterdir():
            if not path.is_file():
                continue
            if path.suffix in ('.json', '.yaml', '.txt'):
                shutil.copy2(path, dest / path.name)
            elif path.suffix in ('.log', '.jsonl', '.patch'):
                with path.open('rb') as src, gzip.open(dest / (path.name + '.gz'), 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        for name in ('settled_targets.json',):
            if (source / 'sim' / name).exists():
                shutil.copy2(source / 'sim' / name, dest / name)
        (dest / 'runtime_reference.json').write_text(json.dumps(dict(
            original_directory=str(source), images=str(source/'images'),
            expanded_urdf=str(source/'robot.urdf'), simulator_generated_assets=str(source/'sim')), indent=2)+'\n')
        runner=runtime/(source.name+'_runner.log')
        if runner.exists():
            with runner.open('rb') as src, gzip.open(dest/'runner.log.gz','wb') as dst:
                shutil.copyfileobj(src,dst)


def manifest_targets(folder):
    return json.loads((folder/'manifest.json').read_text())['targets']


def evaluate():
    previous = json.loads((ROOT.parent/'coco23/comparison.json').read_text())
    episodes = []
    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir() or not (folder/'exits.json').exists():
            continue
        e = coco23.episode(folder)
        rows = list(coco23.legacy.lines(coco23.legacy.source(folder,'observations.jsonl')))
        physical = (coco23.legacy.gazebo_telemetry(folder, rows, 'target_red') if e['backend']=='gazebo'
                    else list(coco23.legacy.lines(coco23.legacy.source(folder, 'isaac.log'))))
        states=[r for r in physical if r.get('event')=='state']
        # A first Gazebo pose packet can precede the last target spawn.
        # Start each target measurement at its first available observation.
        names={t['model'] for t in manifest_targets(folder)}
        starts={name:next(r['targets_world_m'][name] for r in states
                          if name in r['targets_world_m'])
                for name in names}
        e['nonrequested_max_displacement_m']={name:max(float(np.linalg.norm(np.array(r['targets_world_m'][name])-p)) for r in states if name in r['targets_world_m']) for name,p in starts.items() if name!='target_red'}
        e['retreats']=[dict(entry=t, next_state=e['measurements']['transitions'][i+1] if i+1<len(e['measurements']['transitions']) else None)
                       for i,t in enumerate(e['measurements']['transitions']) if t['state']=='RETREAT']
        meta=json.loads((folder/'meta.json').read_text())
        manifest=json.loads((folder/'manifest.json').read_text())
        prior=next(p for p in previous['episodes'] if p['backend']==e['backend'] and p['seed']==e['seed'])
        oldmanifest=json.loads((ROOT.parent/'coco23'/prior['evidence']/'manifest.json').read_text())
        assert manifest==oldmanifest, folder
        assert e['wheel_publishers']==['cmd_vel_arbiter'],folder
        assert set(json.loads((folder/'robot_inputs.json').read_text()))=={'episode_id','requested_colour'}
        if (folder/'nav2_params.yaml').exists():
            assert (folder/'nav2_params.yaml').read_bytes()==(ROOT.parent/'coco23'/prior['evidence']/'nav2_params.yaml').read_bytes()
        e['matched_original_manifest']=True
        e['source_head']=meta['head']
        e['source_digests_match_current']=all(hashlib.sha256((ROOT.parents[3]/name).read_bytes()).hexdigest()==digest for name,digest in meta['source_sha256'].items())
        e['pre_fix']=dict(mission=prior['mission'],physical_complete=prior['physically_verified_complete'],failure_state=prior['failure_state'],raw_evidence='../coco23/'+prior['evidence'],recovery_count=prior['recovery_count'])
        (folder/'measurements.json').write_text(json.dumps(e['measurements'],indent=2)+'\n')
        episodes.append(e)
    result=dict(starting_sha=json.loads((ROOT/'starting_state.json').read_text())['sha'],episodes=episodes,
                aggregate={b:dict(attempted=len([e for e in episodes if e['backend']==b]), physical_complete=sum(e['physically_verified_complete'] for e in episodes if e['backend']==b), protocol_pass=sum(e['protocol_passed'] for e in episodes if e['backend']==b)) for b in ('isaac','gazebo')},
                limitations='One rerun per case; targeted sample, no statistical reliability claim; pre-fix solver contact pairs are not recorded.')
    (ROOT/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['aggregate'],indent=2))
    for e in episodes:
        print(e['backend'],e['seed'],e['mission'],'physical',e['physically_verified_complete'],'protocol',e['protocol_passed'],'nonrequested movement',e['nonrequested_max_displacement_m'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path);args=parser.parse_args()
    if args.runtime:
        curate(args.runtime)
    evaluate()
