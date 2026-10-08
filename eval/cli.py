"""COCO evaluator CLI; no action occurs before registration/qualification gates."""
import argparse
import json
import os
from pathlib import Path
import sys
import subprocess
import yaml
from batch import run_batch
from evidence import atomic_json,file_hash,runtime_fingerprint
from qualification import inventory,qualify,load_policy
from seed_policy import expand

BASE=Path(__file__).resolve().parent


def load_campaign(path):
    value=yaml.safe_load(Path(path).read_text())
    seeds=yaml.safe_load((BASE/'seeds.yaml').read_text())
    pools={k:expand(seeds[k]) for k in ('dev','test_a','reserve_m4')}
    jobs=[]
    for part in value['parts']:
        if part['seed_group']=='reserve_m4':raise ValueError('M4 reserve cannot run in M1')
        if not set(part['seeds'])<=pools[part['seed_group']]:raise ValueError('Campaign violates seed governance')
        for backend in part['backends']:
            for seed in part['seeds']:
                for repeat in range(part['repeats']):jobs.append(dict(backend=backend,seed=seed,repeat=repeat,seed_group=part['seed_group']))
    if len(jobs)!=value['run_count']:raise ValueError('Registered run count mismatch')
    return value,jobs


def main():
    parser=argparse.ArgumentParser(prog='eval');sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('preflight');p.add_argument('--backend',choices=['gazebo','isaac'],required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('bootstrap',help='NON_QUALIFYING bounded engineering episode; never M1/Test A')
    p.add_argument('--backend',choices=['gazebo','isaac'],required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--domain',type=int,default=82)
    p.add_argument('--seconds',type=int,default=120);p.add_argument('--preflight-only',action='store_true')
    p.add_argument('--profile',choices=['full','rgbd_observation'],default='full')
    p.add_argument('--fixture',choices=['acquisition','grasp_original','grasp_flank'],default='acquisition')
    p=sub.add_parser('validate-smoke');p.add_argument('batch',type=Path);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('analyze');p.add_argument('run',type=Path)
    p=sub.add_parser('replay');p.add_argument('source',type=Path)
    p.add_argument('--source-format',choices=['historical','mcap'],required=True)
    p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('run');p.add_argument('--backend',choices=['gazebo','isaac'],required=True)
    p.add_argument('--seeds',choices=['dev','testA','list'],required=True);p.add_argument('--seed-list')
    p.add_argument('--repeats',type=int,required=True);p.add_argument('--campaign',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--domain',type=int,default=82)
    p=sub.add_parser('campaign');p.add_argument('campaign',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--domain',type=int,default=82)
    args=parser.parse_args()
    if args.command=='bootstrap':
        from bootstrap import run_bootstrap
        return run_bootstrap(args.output,args.backend,args.domain,args.seconds,args.preflight_only,args.profile,args.fixture)
    if args.command=='preflight':
        snap=inventory();verdict=qualify(snap,load_policy(),args.backend)
        with args.output.open('x') as f:json.dump({'inventory':snap,'verdict':verdict},f,indent=2)
        print(json.dumps(verdict,indent=2));return 0 if verdict['qualified'] else 3
    if args.command=='validate-smoke':
        from validate import validate_smoke
        value=validate_smoke(args.batch)
        with args.output.open('x') as f:json.dump(value,f,indent=2)
        print(json.dumps(value,indent=2));return 0 if value['validated'] else 3
    if args.command=='analyze':
        from analyzer import run
        run(args.run,BASE/'thresholds.json');return 0
    if args.command=='replay':
        from replay import run
        print(json.dumps(run(args.source,args.output,args.source_format),indent=2));return 0
    os.environ['ROS_DOMAIN_ID']=str(args.domain)
    os.environ['ROS2CLI_NO_DAEMON']='1'
    if subprocess.check_output(['git','status','--porcelain=v1'],cwd=BASE.parent,text=True).strip():
        print('BLOCKED: commit the M1 checkpoint before simulation; worktree is dirty',file=sys.stderr);return 3
    if args.command=='run':
        if args.repeats<1:parser.error('repeats must be positive')
        campaign=args.campaign or BASE/'campaigns'/('m1_breadth.yaml' if args.seeds=='dev' else 'm1_test_a.yaml' if args.seeds=='testA' else 'm1_smoke.yaml')
        definition,jobs=load_campaign(campaign)
        selected=(set(range(10000,10030)) if args.seeds=='dev' else set(range(1000000,1000030)) if args.seeds=='testA' else
                  set(map(int,args.seed_list.split(','))) if args.seed_list else None)
        if selected is None:parser.error('list requires --seed-list')
        jobs=[j for j in jobs if j['backend']==args.backend and j['seed'] in selected]
        if {j['seed'] for j in jobs}!=selected or any(sum(j['seed']==s for j in jobs)!=args.repeats for s in selected):
            parser.error('Requested seeds/repeats must exactly match committed campaign subset')
    else:
        campaign=args.campaign;definition,jobs=load_campaign(campaign)
    if definition['kind']!='smoke':
        validation_path=BASE/'runtime_validation.json'
        if not validation_path.exists():
            print('BLOCKED: qualified smoke/runtime capture and analyzer calibration not yet validated',file=sys.stderr);return 3
        validation=json.loads(validation_path.read_text())
        if validation.get('validated') is not True or any(validation.get(k)!=file_hash(BASE/f) for k,f in
              [('host_policy_sha256','host_policy.json'),('thresholds_sha256','thresholds.json'),('topics_sha256','topics.py')]) or validation.get('runtime_fingerprint')!=runtime_fingerprint():
            print('BLOCKED: stale/incomplete runtime validation',file=sys.stderr);return 3
    return run_batch(args.output,jobs,campaign)

if __name__=='__main__':raise SystemExit(main())
