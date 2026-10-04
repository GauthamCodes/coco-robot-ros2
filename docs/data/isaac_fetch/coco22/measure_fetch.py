"""Offline evaluation only: consumes saved telemetry, never commands the robot."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


def lines(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except ValueError:
                pass


def source(folder, name):
    path = folder / name
    return path if path.exists() else folder / (name + '.gz')


def gazebo_telemetry(folder, observations, target):
    """Compose model-relative palm poses; read live magnet events separately."""
    events = [r for r in observations
              if r['topic'] == f'/magnet/{target}/state']
    holding, index, next_sample = None, 0, 0.0
    states = []
    for row in lines(source(folder, 'physical.jsonl')):
        stamp = (row.get('header') or {}).get('stamp', {})
        now = float(stamp.get('sec', 0)) + float(stamp.get('nsec', 0)) * 1e-9
        if now < next_sample:
            continue
        next_sample = now + 2.0
        while index < len(events) and events[index]['sim_s'] <= now:
            holding = target if events[index]['data'] == 'attached' else None
            index += 1
        poses = {p['name']: p for p in row['pose']}
        if 'coco' not in poses or target not in poses:
            continue

        def pose(name):
            p = poses[name]
            position, orientation = p.get('position', {}), p.get('orientation', {})
            return ([position.get(k, 0.0) for k in ('x', 'y', 'z')],
                    [orientation.get(k, 0.0) for k in ('x', 'y', 'z', 'w')])

        body, bq = pose('coco')
        state = dict(event='state', time_sim_s=now, magnet_attached=holding,
                     targets_world_m={}, targets_world_quaternion_wxyz={})
        for name in poses:
            if name.startswith('target_'):
                p, q = pose(name)
                state['targets_world_m'][name] = p
                state['targets_world_quaternion_wxyz'][name] = [q[3], *q[:3]]
        palm_name = next((n for n in ('m_link3', 'coco::m_link3') if n in poses), None)
        if palm_name:
            local, lq = pose(palm_name)
            rotation = Rotation.from_quat(bq)
            world = np.array(body) + rotation.apply(local)
            q = (rotation * Rotation.from_quat(lq)).as_quat()
            state['palm_world_pose'] = [world.tolist(), [q[3], *q[:3]]]
        states.append(state)
    transitions = []
    for row in events:
        if row['data'] not in ('attached', 'detached'):
            continue
        event = dict(event=row['data'], target=target, time_sim_s=row['sim_s'])
        before = [s for s in states if s['time_sim_s'] <= row['sim_s']]
        if before:
            event['target_world_m'] = before[-1]['targets_world_m'][target]
            event['pose_sample_time_sim_s'] = before[-1]['time_sim_s']
        transitions.append(event)
    return states + transitions


def measure(folder):
    observations = list(lines(source(folder, 'observations.jsonl')))
    manifest = json.loads((folder / 'manifest.json').read_text())
    target = 'target_' + manifest['requested_colour']
    simulator = (gazebo_telemetry(folder, observations, target)
                 if manifest['backend'] == 'gazebo'
                 else list(lines(source(folder, 'isaac.log'))))
    states = [r for r in simulator if r.get('event') == 'state']
    transitions = []
    for r in observations:
        if r['topic'] != '/mission/state':
            continue
        fields = dict(p.split('=', 1) for p in r['data'].split() if '=' in p)
        if not transitions or fields['state'] != transitions[-1]['state']:
            transitions.append(dict(state=fields['state'], sim_s=r['sim_s'],
                                    wall_s=r['wall_s'], status=r['data']))
    meta = json.loads((folder / 'meta.json').read_text())
    result = {'sample_size': 1, 'episode': manifest['episode_id'],
              'source_head': meta['head'], 'transitions': transitions,
              'recovery_entries': sum(t['state'] == 'RECOVERY' for t in transitions),
              'mission': transitions[-1]['state'] if transitions else 'UNOBSERVED',
              'attachment_events': [r for r in simulator if r.get('event')
                                    in ('attached', 'detached', 'attach_rejected')]}
    search = next((r for r in transitions if r['state'] == 'SEARCH_TARGET'), None)
    if search:
        result['first_detection_after_search_entry'] = next(
            (r for r in observations if r['topic'] == '/perception/target'
             and r['sim_s'] >= search['sim_s']), None)
    grasp = next((r for r in transitions if r['state'] == 'GRASP'), None)
    if grasp:
        pose = [r for r in observations if r['topic'] == '/model/coco/odometry'
                and r['sim_s'] <= grasp['sim_s']][-1]
        body = [r for r in states if r['time_sim_s'] <= grasp['sim_s']][-1]
        rel = Rotation.from_quat(pose['data']['quaternion_xyzw']).inv().apply(
            np.array(body['targets_world_m'][target]) - pose['data']['xyz'])
        result['grasp_entry_measured_relative_xyz_m'] = rel.tolist()
        fixes = [r for r in observations if r['topic'] == '/approach/target'
                 and r['sim_s'] <= grasp['sim_s']]
        if fixes:
            result['approach_estimate'] = fixes[-1]
    carry = next((r for r in transitions if r['state'] == 'DESCEND'), None)
    attachment = next((r for r in result['attachment_events']
                       if grasp and r['event'] == 'attached'
                       and r['time_sim_s'] >= grasp['sim_s']), None)
    if attachment and carry and 'target_world_m' in attachment:
        lifted = [r['targets_world_m'][target][2] for r in states
                  if attachment['time_sim_s'] <= r['time_sim_s'] <= carry['sim_s']
                  and r.get('magnet_attached') == target]
        if lifted:
            result['maximum_target_rise_before_descent_m'] = max(lifted) - attachment['target_world_m'][2]
    placement = next((r for r in transitions if r['state'] == 'PLACE'), None)
    if placement:
        home = [r for r in observations if r['topic'] == '/model/coco/odometry'
                and r['sim_s'] <= placement['sim_s']][-1]
        result['place_entry_robot_world_xyz_m'] = home['data']['xyz']
    holding = [r for r in states if carry and r['time_sim_s'] >= carry['sim_s']
               and r.get('magnet_attached') == target and r.get('palm_world_pose')]
    if holding:
        relative = []
        for r in holding:
            p, q = r['palm_world_pose']
            relative.append(Rotation.from_quat([*q[1:], q[0]]).inv().apply(
                np.array(r['targets_world_m'][target]) - p))
        result['retention'] = {
            'samples': len(holding),
            'start_sim_s': holding[0]['time_sim_s'],
            'end_sim_s': holding[-1]['time_sim_s'],
            'palm_relative_position_span_m': np.ptp(relative, axis=0).tolist(),
            'maximum_displacement_from_carry_start_m': max(
                float(np.linalg.norm(np.array(r['targets_world_m'][target]) -
                                     holding[0]['targets_world_m'][target]))
                for r in holding)}
    if states:
        result['final_target_world_xyz_m'] = states[-1]['targets_world_m'][target]
        start = manifest['robot_start']
        final = result['final_target_world_xyz_m']
        result['final_target_distance_from_home_xy_m'] = float(np.linalg.norm(
            np.array(final[:2]) - [start['x'], start['y']]))
        result['final_magnet_attached'] = states[-1].get('magnet_attached')
        q = states[-1].get('targets_world_quaternion_wxyz', {}).get(target)
        if q:
            rotation = Rotation.from_quat([*q[1:], q[0]])
            result['final_target_up_world'] = rotation.apply([0, 0, 1]).tolist()
    detached = next((r for r in result['attachment_events']
                     if attachment and r['event'] == 'detached'
                     and r['time_sim_s'] > attachment['time_sim_s']), None)
    if detached:
        released = [r for r in states
                    if r['time_sim_s'] >= detached['time_sim_s']
                    and r.get('magnet_attached') is None]
        result['post_release'] = {
            'samples': len(released),
            'sampled_height_range_m': [
                min(r['targets_world_m'][target][2] for r in released),
                max(r['targets_world_m'][target][2] for r in released)]
            if released else None}
    summary = folder / 'result.json'
    if summary.exists():
        raw = json.loads(summary.read_text())
        for key in ('mission_wall_s', 'mission_sim_s', 'stop_breaches'):
            result[key] = raw.get(key)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    measured = measure(args.run)
    args.output.write_text(json.dumps(measured, indent=2) + '\n')
    print(json.dumps({k: v for k, v in measured.items()
                      if k not in ('transitions', 'attachment_events', 'approach_estimate')},
                     indent=2))
