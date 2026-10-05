"""Offline search-exit evidence. Reads all targets only for evaluation."""
import argparse
import bisect
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('legacy', ROOT.parent / 'coco22/measure_fetch.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def trace(folder):
    rows = list(legacy.lines(legacy.source(folder, 'observations.jsonl')))
    manifest = json.loads((folder / 'manifest.json').read_text())
    topics = {}
    for row in rows:
        topics.setdefault(row['topic'], []).append(row)
    def near(topic, wall):
        seq = topics.get(topic, [])
        if not seq:
            return None
        ix = bisect.bisect_left([r['wall_s'] for r in seq], wall)
        return min(seq[max(0, ix-1):ix+1], key=lambda r: abs(r['wall_s']-wall))
    transitions = []
    for r in topics.get('/mission/state', []):
        state = r['data'].split()[0].split('=')[-1]
        if not transitions or state != transitions[-1]['state']:
            transitions.append(dict(state=state, sim_s=r['sim_s'], wall_s=r['wall_s'], status=r['data']))
    physical = (legacy.gazebo_telemetry(folder, rows, 'target_red') if manifest['backend'] == 'gazebo'
                else list(legacy.lines(legacy.source(folder, 'isaac.log'))))
    physical = [r for r in physical if r.get('event') == 'state']
    out = []
    for i, entry in enumerate(transitions):
        if entry['state'] not in ('DESCEND', 'RETREAT'):
            continue
        end = transitions[i+1] if i+1 < len(transitions) else rows[-1]
        samples = []
        for wall in np.arange(entry['wall_s'], end['wall_s'] + .01, 2):
            odom = near('/model/coco/odometry', wall)
            xyz = odom['data']['xyz']; q = odom['data']['quaternion_xyzw']
            rpy = Rotation.from_quat(q).as_euler('xyz').tolist()
            before = near('/model/coco/odometry', wall-.5)
            after = near('/model/coco/odometry', wall+.5)
            dt = after['sim_s']-before['sim_s']
            velocity = ((np.array(after['data']['xyz'])-before['data']['xyz']) / dt).tolist() if dt > 0 else None
            body = min(physical, key=lambda r: abs(r['time_sim_s']-odom['sim_s']))
            data = dict(wall_s=float(wall), sim_s=odom['sim_s'], world_xyz_m=xyz, rpy_rad=rpy,
                        lateral_m=None,
                        world_velocity_m_s=velocity,
                        physical_sample_sim_s=body['time_sim_s'], targets_world_m=body['targets_world_m'],
                        targets_quaternion_wxyz=body['targets_world_quaternion_wxyz'])
            for topic, label in [('/diff_drive_controller/odom','wheel_odom'),('/diff_drive_controller/cmd_vel','final_command'),('/cmd_vel_rl','rl_command'),('/ramp/status','ramp'),('/cmd_vel_arbiter/status','arbiter'),('/mission/search_region','region'),('amcl','amcl'),('/joint_states','joints')]:
                r=near(topic,wall);data[label]=r if r else None
            if data['region']:
                from coco_config.robot import lane_for_region
                data['lateral_m']=xyz[1]-lane_for_region(data['region']['data'])
            for key in ('command_age_sim_s','measured_wheels_rad_s','measured_body_yaw_rad_s'):
                data[key]=body.get(key)
            samples.append(data)
        out.append(dict(entry=entry,end=end,samples=samples))
    return dict(folder=str(folder),backend=manifest['backend'],seed=manifest['seed'],transitions=transitions,segments=out,
                limitations='No contact-force/pair telemetry in historical traces; object displacement and wheel/body disagreement show interaction, exact solver contact chain is inferred. IMU historical observer stores only sample presence; body rpy from ground-truth quaternion. Velocity from finite differences.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    results=[trace(p) for p in sorted(args.root.iterdir()) if p.is_dir() and (p/'manifest.json').exists() and ((p/'observations.jsonl').exists() or (p/'observations.jsonl.gz').exists())]
    args.output.write_text(json.dumps(results,indent=2)+'\n')
