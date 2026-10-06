#!/usr/bin/env python3
"""Append-only M2.3/M2.4 rescoring from saved facts; no historical writes."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from oracle import score, REST_WINDOW_SIM_S

REPO = Path(__file__).resolve().parents[1]


def rows(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as f:
        for line in f:
            try:
                value = json.loads(line)
            except ValueError:
                continue  # Isaac log contains ROS/simulator text too.
            if isinstance(value, dict):
                yield value


def normalized(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    raw = json.loads((folder / 'result.json').read_text())
    requested = 'target_' + manifest['requested_colour']
    names = [t['model'] for t in manifest['targets'] if t['model'] != requested]
    obs = list(rows(folder / 'observations.jsonl.gz'))
    transitions = [r for r in obs if r.get('topic') == '/mission/state']
    terminal = next((r for r in reversed(transitions)
                     if 'state=COMPLETE ' in r['data'] + ' ' or 'state=ABORT ' in r['data'] + ' '), None)
    end = terminal['sim_s'] if terminal else max((r['sim_s'] for r in obs), default=0)
    start = next((r['sim_s'] for r in transitions if 'state=LOCALIZE ' in r['data'] + ' '), None)
    attached = None
    magnets = iter(r for r in obs if r.get('topic') == '/magnet/' + requested + '/state')
    event = next(magnets, None)
    states = []
    source = folder / ('isaac.log.gz' if manifest['backend'] == 'isaac' else 'physical.jsonl.gz')
    initial, maxima = {}, {}
    for row in rows(source):
        if manifest['backend'] == 'isaac':
            if row.get('event') != 'state':
                continue
            now, targets = row['time_sim_s'], row.get('targets_world_m', {})
            # Historical raw-world odometry is evaluator data here only.
            robot = None
            quaternions = row.get('targets_world_quaternion_wxyz', {})
            is_attached = row.get('magnet_attached') == requested
        else:
            stamp = (row.get('header') or {}).get('stamp', {})
            now = float(stamp.get('sec', 0)) + float(stamp.get('nsec', 0)) * 1e-9
            poses = {p['name']: p for p in row.get('pose', [])}
            targets = {n: [p.get('position', {}).get(k, 0.0) for k in ('x', 'y', 'z')]
                       for n, p in poses.items() if n.startswith('target_')}
            quaternions = {n: [p.get('orientation', {}).get(k, 0.0) for k in ('w','x','y','z')]
                           for n,p in poses.items() if n.startswith('target_')}
            robot = [poses['coco'].get('position', {}).get(k, 0.0) for k in ('x', 'y', 'z')] if 'coco' in poses else None
            while event and event['sim_s'] <= now:
                attached = event['data']
                event = next(magnets, None)
            is_attached = (attached == 'attached') if attached in ('attached', 'detached') else None
        if start is None or now < start or now > end:
            continue
        for name in names:
            if name in targets:
                initial.setdefault(name, targets[name])
                maxima[name] = max(maxima.get(name, 0), math.dist(initial[name], targets[name]))
        if requested in targets:
            # Retain only terminal samples; disturbance maxima use every packet.
            if now >= end - 3 * REST_WINDOW_SIM_S:
                states.append({'sim_s': now, 'xyz_m': targets[requested],
                               'attached': is_attached, 'quaternion_wxyz': quaternions.get(requested),
                               'robot': robot})
    covered = bool(states and end - states[-1]['sim_s'] <= REST_WINDOW_SIM_S)
    window = []
    if states:
        stop = states[-1]['sim_s']
        anchor = next((i for i in reversed(range(len(states)))
                       if states[i]['sim_s'] <= stop - REST_WINDOW_SIM_S), None)
        if anchor is not None:
            window = states[anchor:]
    if manifest['backend'] == 'isaac':
        # Historical normal topic was simulator truth (now prohibited for robot).
        candidates = [r for r in obs if r.get('topic') == '/model/coco/odometry' and r['sim_s'] <= end]
        robot = candidates[-1]['data']['xyz'] if candidates and end-candidates[-1]['sim_s'] <= REST_WINDOW_SIM_S else None
    else:
        robot = states[-1]['robot'] if states else None
    graph = json.loads((folder/'command_graph.json').read_text())
    flags = raw.get('stop_breaches')
    safety_covered = flags == 0 and graph.get('/diff_drive_controller/cmd_vel') == ['cmd_vel_arbiter']
    # Existing nonzero flags include unresolved cross-topic ordering; they are
    # unknown, not asserted arbiter violations or silently cleared.
    return {
        'home_xy_m': [manifest['robot_start']['x'], manifest['robot_start']['y']],
        'target_height_m': next(t['height'] for t in manifest['targets'] if t['model'] == requested),
        'target_final_xyz_m': states[-1]['xyz_m'] if states else None,
        'target_rest_samples': [{k: s[k] for k in ('sim_s','xyz_m','attached','quaternion_wxyz')} for s in window],
        'terminal_truth_covered': covered,
        'robot_final_xyz_m': robot,
        'nonrequested_models': names,
        'nonrequested_max_displacement_m': maxima,
        'disturbance_truth_covered': start is not None and set(maxima) == set(names),
        'arbiter_violations': [] if safety_covered else None,
        'arbiter_evidence_covered': safety_covered,
        'historical_observer_stop_breaches': flags,
        'episode_wall_s': raw.get('mission_wall_s'),
        'episode_finished': terminal is not None,
        'mission_verdict': raw.get('mission', 'UNOBSERVED'),
        'sampling_limit': 'Finite saved samples only; no continuous contact/velocity or qualification claim',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    summary = []
    for campaign in ('coco23', 'coco24'):
        for folder in sorted((REPO / 'docs/data/isaac_fetch' / campaign).glob('*_seed*')):
            if not folder.is_dir() or not (folder/'result.json').exists():
                continue
            facts = normalized(folder)
            result = score(facts)
            hashes = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(folder.iterdir()) if p.is_file()}
            record = {'run_id': campaign + '/' + folder.name, 'source_sha256': hashes,
                      'facts': facts, 'score': result}
            with (args.output_dir / (campaign + '_' + folder.name + '.json')).open('x') as f:
                json.dump(record, f, indent=2, allow_nan=False); f.write('\n')
            summary.append({'run_id': record['run_id'], **result})
    with (args.output_dir/'summary.json').open('x') as f:
        json.dump(summary, f, indent=2, allow_nan=False); f.write('\n')
    for r in summary:
        print(r['run_id'], r['mission_verdict'], r['oracle_verdict'],
              r['mission_oracle_disagreement'], r['failed_conditions'], r['missing_evidence'])


if __name__ == '__main__':
    main()
