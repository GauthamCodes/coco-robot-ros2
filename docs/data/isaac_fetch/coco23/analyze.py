"""Evaluate saved episodes only; no robot inputs or simulator commands."""
import gzip
import importlib.util
import json
from pathlib import Path
import re
import statistics
import math
import hashlib
import sys

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('measure_fetch', ROOT.parent / 'coco22/measure_fetch.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def read_text(path):
    if path.exists():
        return path.read_text()
    zipped = Path(str(path) + '.gz')
    return gzip.open(zipped, 'rt').read() if zipped.exists() else ''


def stats(values):
    values = [v for v in values if v is not None]
    return {'n': len(values), 'mean': statistics.mean(values), 'min': min(values),
            'max': max(values), 'median': statistics.median(values)} if values else {'n': 0}


def episode(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    raw = json.loads((folder / 'result.json').read_text()) if (folder / 'result.json').exists() else {}
    try:
        measured = legacy.measure(folder)
    except Exception as exc:
        measured = {'evaluation_error': repr(exc)}
    log = read_text(folder / 'mission.log')
    lifts = re.findall(r'Target lifted ([\d.]+) mm', log)
    measured['first_verified_lift_mm'] = float(lifts[0]) if lifts else None
    measured['navigation_arrival_error_m'] = {
        k: float(v) for k, v in re.findall(r'(\w+) arrived: ground truth ([\d.]+) m', log)}
    states = raw.get('states', [])
    observations = list(legacy.lines(legacy.source(folder, 'observations.jsonl'))) if (folder / 'observations.jsonl.gz').exists() or (folder / 'observations.jsonl').exists() else []
    accepted_search = next((t for t in measured.get('transitions', []) if t['state'] == 'STOW_ARM'), None)
    fixes = [r for r in observations if r['topic'] == '/perception/target' and accepted_search and r['sim_s'] <= accepted_search['sim_s']]
    measured['last_detection_before_accepted_search'] = fixes[-1] if fixes else None
    measured['navigation_arrival_samples'] = [{'state': k, 'error_m': float(v)} for k, v in re.findall(r'(\w+) arrived: ground truth ([\d.]+) m', log)]
    transitions = measured.get('transitions', [])
    failures = [t for t in transitions if t['state'] == 'RECOVERY' or t['state'] == 'ABORT']
    terminal_fields = dict(v.split('=', 1) for v in transitions[-1]['status'].split() if '=' in v) if transitions else {}
    failure_state = terminal_fields.get('prev')
    if failure_state == 'RECOVERY':
        failure_state = next((dict(v.split('=', 1) for v in t['status'].split() if '=' in v).get('prev') for t in reversed(failures) if t['state'] == 'RECOVERY'), None)
    attachment = any(e['event'] == 'attached' for e in measured.get('attachment_events', []))
    release = any(e['event'] == 'detached' for e in measured.get('attachment_events', []))
    xyz = measured.get('final_target_world_xyz_m')
    up = measured.get('final_target_up_world', [None, None, None])[2]
    distance = measured.get('final_target_distance_from_home_xy_m')
    # Report observed physical components, alongside existing mission gates.
    placed = bool(release and xyz and abs(xyz[2] - .079) <= .02 and up is not None and up > .99)
    physical = bool(attachment and lifts and measured.get('retention', {}).get('samples', 0) >= 2
                    and placed and distance is not None and distance <= .50)
    mission = raw.get('mission', 'NOT_STARTED')
    complete = mission == 'COMPLETE' and physical
    protocol_passed = complete and raw.get('passed') is True and all(v == 0 for v in json.loads((folder / 'exits.json').read_text()).values())
    graph = json.loads((folder / 'command_graph.json').read_text()) if (folder / 'command_graph.json').exists() else {}
    measured['grasp_relative_error_definition'] = 'measured object centre x minus existing red approach_stop_x; y minus zero; z is not the grasp-band handoff'
    from coco_config.robot import approach_stop_x
    rel = measured.get('grasp_entry_measured_relative_xyz_m')
    measured['grasp_relative_error_xy_m'] = [rel[0] - approach_stop_x('red'), rel[1]] if rel else None
    target_spec = next(t for t in manifest['targets'] if t['colour'] == 'red')
    sim_rows = legacy.gazebo_telemetry(folder, observations, 'target_red') if manifest['backend'] == 'gazebo' else list(legacy.lines(legacy.source(folder, 'isaac.log')))
    localize = next((t for t in transitions if t['state'] == 'LOCALIZE'), None)
    initial = next((r for r in sim_rows if r.get('event') == 'state' and r.get('time_sim_s', 0) >= (localize['sim_s'] if localize else 0) and 'target_red' in r.get('targets_world_m', {})), None)
    measured['initial_target_world_xyz_m'] = initial['targets_world_m']['target_red'] if initial else None
    measured['initial_target_manifest_error_xyz_m'] = [x - target_spec[k] for x, k in zip(measured['initial_target_world_xyz_m'], ('x', 'y', 'z'))] if initial else None
    measured['grasp_relative_error_xy_norm_m'] = math.hypot(*measured['grasp_relative_error_xy_m']) if rel else None
    stages = {}
    for name, active, success in (
        ('navigation', 'NAVIGATE_TO_RAMP', 'ALIGN_FOR_CLIMB'),
        ('approach', 'APPROACH_TARGET', 'GRASP'),
        ('return', 'RETURN_HOME', 'PLACE')):
        stages[name] = 'succeeded' if success in states else ('not_reached' if active not in states else 'not_completed')
    stages.update(detection='observed' if measured.get('first_detection_after_search_entry') else 'not_observed',
                  grasp='attached' if attachment else ('not_reached' if 'GRASP' not in states else 'not_attached'),
                  lift='verified' if lifts else 'not_verified',
                  retention='sampled' if measured.get('retention', {}).get('samples', 0) >= 2 else 'not_verified',
                  release='detached' if release else 'not_verified',
                  placement='upright_floor_pose' if placed else 'not_verified')
    return {'seed': manifest['seed'], 'backend': manifest['backend'], 'requested_colour': manifest['requested_colour'],
            'target': next(t for t in manifest['targets'] if t['colour'] == 'red'),
            'mission': mission, 'physically_verified_complete': complete, 'protocol_passed': protocol_passed, 'stages': stages,
            'detection_success': 'STOW_ARM' in states,
            'failure_state': failure_state if not complete else None,
            'failure_transitions': failures, 'final_state': raw.get('final', {}).get('/mission/state'),
            'native_process_failures': [line for line in log.splitlines() if 'process has died' in line] + [line for line in read_text(folder / ('gazebo.log' if manifest['backend'] == 'gazebo' else 'isaac.log')).splitlines() if 'ODE INTERNAL ERROR' in line or 'process has died' in line],
            'infrastructure_error': raw.get('error') or read_text(folder / 'runner_failure.txt') or None,
            'recovery_count': states.count('RECOVERY'), 'measurements': measured,
            'wheel_publishers': graph.get('/diff_drive_controller/cmd_vel'),
            'runtime_sim_s': raw.get('mission_sim_s'), 'runtime_wall_s': raw.get('mission_wall_s'),
            'exits': json.loads((folder / 'exits.json').read_text()), 'evidence': str(folder.relative_to(ROOT))}


def main():
    episodes = [episode(ROOT / f'{backend}_seed{seed}') for backend in ('isaac', 'gazebo') for seed in range(5, 10)]
    matched = []
    for seed in range(5, 10):
        a, b = [json.loads((ROOT / f'{backend}_seed{seed}/manifest.json').read_text()) for backend in ('isaac', 'gazebo')]
        assert {k: v for k, v in a.items() if k not in ('backend', 'episode_id')} == {k: v for k, v in b.items() if k not in ('backend', 'episode_id')}
        matched.append(seed)
    aggregates = {}
    scalar = ('mission_sim_s', 'mission_wall_s', 'first_verified_lift_mm', 'final_target_distance_from_home_xy_m', 'maximum_target_rise_before_descent_m')
    for backend in ('isaac', 'gazebo'):
        runs = [e for e in episodes if e['backend'] == backend]
        counts = {}
        by_state = {}
        for e in runs:
            if not e['physically_verified_complete']:
                state = e['failure_state'] or 'INFRASTRUCTURE_OR_UNFINISHED'
                by_state[state] = by_state.get(state, 0) + 1
                terminal = e['failure_transitions'][-1]['status'] if e['failure_transitions'] else e['final_state']
                key = terminal or e['infrastructure_error'] or e['mission']
                counts[key] = counts.get(key, 0) + 1
        aggregates[backend] = {'attempted': 5, 'completed': sum(e['physically_verified_complete'] for e in runs),
                               'mission_complete': sum(e['mission'] == 'COMPLETE' for e in runs),
                               'protocol_passed': sum(e['protocol_passed'] for e in runs),
                               'protocol_pass_rate': sum(e['protocol_passed'] for e in runs) / 5,
                               'sampled_idle_wheel_flags': sum(e['measurements'].get('stop_breaches') or 0 for e in runs),
                               'success_rate': sum(e['physically_verified_complete'] for e in runs) / 5,
                               'recoveries': sum(e['recovery_count'] for e in runs), 'failure_terminal_status_counts': counts, 'failures_by_state': by_state,
                               'metrics_all_available': {k: stats([e['measurements'].get(k) for e in runs]) for k in scalar},
                               'retention_max_axis_span_m': stats([max(e['measurements']['retention']['palm_relative_position_span_m']) for e in runs if e['measurements'].get('retention')]),
                               'carry_displacement_m': stats([e['measurements']['retention']['maximum_displacement_from_carry_start_m'] for e in runs if e['measurements'].get('retention')]),
                               'navigation_arrival_error_m': stats([v['error_m'] for e in runs for v in e['measurements'].get('navigation_arrival_samples', [])]),
                               'placement_error_completed_m': stats([e['measurements'].get('final_target_distance_from_home_xy_m') for e in runs if e['physically_verified_complete']]),
                               'grasp_relative_error_xy_norm_m': stats([e['measurements'].get('grasp_relative_error_xy_norm_m') for e in runs]),
                               'grasp_relative_error_xy_m': [stats([e['measurements']['grasp_relative_error_xy_m'][i] for e in runs if e['measurements'].get('grasp_relative_error_xy_m')]) for i in range(2)]}
    differences = []
    for seed in range(5, 10):
        a, b = [next(e for e in episodes if e['seed'] == seed and e['backend'] == backend) for backend in ('isaac', 'gazebo')]
        delta = {}
        for k in scalar:
            av, bv = a['measurements'].get(k), b['measurements'].get(k)
            if k == 'final_target_distance_from_home_xy_m' and not (a['physically_verified_complete'] and b['physically_verified_complete']):
                continue
            if av is not None and bv is not None:
                delta[k] = av - bv
        for name in ('grasp_entry_measured_relative_xyz_m', 'grasp_relative_error_xy_m'):
            av, bv = a['measurements'].get(name), b['measurements'].get(name)
            if av is not None and bv is not None:
                delta[name] = [x - y for x, y in zip(av, bv)]
        differences.append({'seed': seed, 'isaac_minus_gazebo': delta, 'both_completed': a['physically_verified_complete'] and b['physically_verified_complete']})
    result = {'starting_sha': json.loads((ROOT / 'starting_state.json').read_text())['sha'],
              'sample_size_per_backend': 5, 'level': 'positions', 'requested_colour': 'red',
              'methodology': {'generator': 'coco_sim/coco_sim/episode.py generate_episode(seed, level=positions, backend, requested_colour=red)',
                              'randomization': 'One random.Random(seed); shuffle colours first; sample each region x then y, rejecting invalid separation/corridors. x from nominal row to 85% of remaining far bound; y within lane +/-0.030 m.',
                              'world': 'coco_world; canonical robot start, ramp, no additional obstacles',
                              'runner': 'scripts/isaac_fetch.py; 1200 wall seconds per mission; private domain82; sequential fresh processes; no parameters overridden; Isaac measured profile vs canonical Gazebo profile',
                              'physical_completion_gate': 'Mission COMPLETE plus recorded attachment, logged lift, >=2 retained palm-relative samples, detach, floor height within existing +/-20mm gate, up-axis z>0.99, final target within 0.50m of home. Offline confirmation only, no robot inputs.',
                              'protocol_gate': 'Original observer passed and all wrapper exit codes zero; native process crashes also extracted because wrapper exits may hide them.',
                              'grasp_metric': 'Object-centre base x minus existing red approach_stop_x; y minus zero. Simulator snapshots sampled about every2s and ROS reception times can differ; this is an approximate grasp-entry metric.',
                              'placement_metric': 'Target XY distance from robot_start/home; aggregate and paired placement deltas only for completed releases.',
                              'evaluator_reuse': '../coco22/measure_fetch.py (unchanged); coco23/analyze.py adds outcome classification, log-derived lift/navigation metrics and aggregates.',
                              'legacy_evaluator_sha256': hashlib.sha256((ROOT.parent / 'coco22/measure_fetch.py').read_bytes()).hexdigest(),
                              'replicates': 'One trial per seed per backend; no reruns; all attempts retained; no fixes or tuning.'},
              'matched_manifest_seeds': matched, 'episodes': episodes, 'aggregate': aggregates,
              'cross_simulator_differences': differences,
              'cross_simulator_runtime_differences_both_complete': {k: stats([d['isaac_minus_gazebo'].get(k) for d in differences if d['both_completed']]) for k in ('mission_sim_s', 'mission_wall_s')},
              'verdict': 'B. Partial repeatability demonstrated, with specific remaining failure modes',
              'cross_simulator_mean_differences_available_pairs': {k: stats([d['isaac_minus_gazebo'].get(k) for d in differences]) for k in scalar},
              'limitations': ['Five distinct seeded layouts, one trial each per backend; no within-seed repeatability or statistical reliability estimate.',
                              'Fixed-joint magnet approximation; ideal pose odometry in Isaac versus wheel odometry in Gazebo.',
                              'Runtime budget is 1200 wall seconds; backend simulation rates differ.',
                              'Physical fetch completion and original observer/exit-code protocol pass are reported separately; raw idle-mode flags are preserved.',
                              'Unavailable measurements are null/unverified, never counted as success.',
                              'Final target distance is placement error only for completed releases; failed-run final poses are diagnostic.']}
    for e in episodes:
        (ROOT / e['evidence'] / 'measurements.json').write_text(json.dumps(e['measurements'], indent=2) + '\n')
    (ROOT / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(aggregates, indent=2))


if __name__ == '__main__':
    main()
