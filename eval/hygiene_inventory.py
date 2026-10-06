#!/usr/bin/env python3
"""Reproduce tracked-source hygiene searches without executing entry points."""
import argparse
import ast
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

REPO=Path(__file__).resolve().parents[1]
PATTERNS={
    'mission_regions': r'MissionMachine|MissionPlan|TARGET_REGIONS|REGION_IDS|FIXED_REGION_MAP|class.*(Mission|Region)',
    'colour_lane': r'lane_for_colour|colour_for_lane|resolve_lane|colou?r.{0,30}lane|lane.{0,30}colou?r',
    'machine_paths': r'/home/[^\s\"\']+|/tmp/[^\s\"\']+|/opt/[^\s\"\']+|\$HOME/isaac|Path.home\(\)',
    'joint_limits': r'ARM_LIMITS|joint_limits|lower=|upper=|m_link[123]_Revolute',
    'privileged_or_command_paths': r'/eval|/model/|/world/|gz.*model|model_z|target_height|/diff_drive_controller/cmd_vel',
}


def scan():
    files=subprocess.check_output(['git','-C',str(REPO),'ls-files','-z'],text=True).split('\0')
    files=[f for f in files if f]
    results={k:[] for k in PATTERNS};launch=[];shells=[];syntax=[];hashes=defaultdict(list)
    for f in files:
        p=REPO/f
        if p.suffix not in ('.py','.sh','.yaml','.yml','.md','.xacro','.xml','.sdf','.txt') and p.name!='Dockerfile':continue
        try:content=p.read_text()
        except (UnicodeError,OSError):continue
        active=not f.startswith(('docs/data/','docs/m0/','docs/images/','experiments/legacy/'))
        for key,pattern in PATTERNS.items():
            for n,line in enumerate(content.splitlines(),1):
                if re.search(pattern,line):results[key].append(dict(path=f,line=n,text=line,active_candidate=active))
        if 'launch' in f and f.endswith('.py') and active:
            launch.append(f);hashes[hashlib.sha256(p.read_bytes()).hexdigest()].append(f)
        if p.suffix=='.sh' and active:
            result=subprocess.run(['bash','-n',str(p)],capture_output=True,text=True)
            shells.append(dict(path=f,returncode=result.returncode,stderr=result.stderr))
        if p.suffix=='.py' and active:
            try:ast.parse(content,filename=f)
            except SyntaxError as exc:syntax.append(dict(path=f,error=str(exc)))
    return dict(scope='All tracked text; raw matches are not automatically defects',
                tracked_file_count=len(files),matches=results,launch_files=launch,
                byte_identical_launch_groups=[v for v in hashes.values() if len(v)>1],
                shell_syntax=shells,python_syntax_errors=syntax)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    with args.output.open('x') as f:json.dump(scan(),f,indent=2);f.write('\n')
