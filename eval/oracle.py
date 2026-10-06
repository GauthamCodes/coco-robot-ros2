#!/usr/bin/env python3
"""The single offline physical-success oracle; no ROS or simulator dependencies."""
import argparse
import itertools
import json
import math
from pathlib import Path

# Frozen M0 definition: provenance and operational meaning in SUCCESS_DEFINITION.
PLACEMENT_RADIUS_M = 0.50
HOME_RADIUS_M = 0.50
DISPLACEMENT_M = 0.005
REST_POSITION_M = 0.005
REST_WINDOW_SIM_S = 2.0
FLOOR_HEIGHT_TOLERANCE_M = 0.02
EPISODE_WALL_BUDGET_S = 1200.0


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def xyz(value):
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(map(finite, value))


def quaternion(value):
    return (isinstance(value, (list, tuple)) and len(value) == 4
            and all(map(finite, value)) and sum(v*v for v in value) > 0)


def distance(a, b):
    return math.dist(a, b)


def score(episode):
    """Score normalized evaluator facts, preserving unknowns and mission verdict.

    An observed failure proves the conjunction false even if another condition is
    unknown. PASS requires all conditions true. Otherwise UNSCORABLE. Mission
    verdict affects only the comparison field, never any physical check.
    """
    checks, metrics, missing = {}, {}, []

    def check(name, value, reason=''):
        checks[name] = value
        if value is None:
            missing.append({'condition': name, 'reason': reason})

    home = episode.get('home_xy_m')
    valid_home = isinstance(home, list) and len(home) == 2 and all(map(finite, home))
    target = episode.get('target_final_xyz_m')
    height = episode.get('target_height_m')
    if valid_home and xyz(target) and finite(height) and height > 0:
        metrics['placement_distance_xy_m'] = distance(target[:2], home)
        metrics['floor_center_error_m'] = abs(target[2] - height / 2)
        check('target_in_placement_zone', metrics['placement_distance_xy_m'] <= PLACEMENT_RADIUS_M
              and metrics['floor_center_error_m'] <= FLOOR_HEIGHT_TOLERANCE_M)
    else:
        check('target_in_placement_zone', None, 'Missing finite target pose/dimensions or home definition')

    rest = episode.get('target_rest_samples', [])
    valid_rest = (isinstance(rest, list) and len(rest) >= 2
                  and all(isinstance(r, dict) and finite(r.get('sim_s'))
                          and xyz(r.get('xyz_m')) and quaternion(r.get('quaternion_wxyz'))
                          and r.get('attached') is False for r in rest) and finite(height) and height > 0)
    if valid_rest and all(a['sim_s'] < b['sim_s'] for a, b in zip(rest, rest[1:])):
        metrics['rest_window_sim_s'] = rest[-1]['sim_s'] - rest[0]['sim_s']
        metrics['rest_max_pairwise_distance_m'] = max(distance(a['xyz_m'], b['xyz_m'])
                                                     for a, b in itertools.combinations(rest, 2))
        angles = []
        for a, b in itertools.combinations(rest, 2):
            qa, qb = a['quaternion_wxyz'], b['quaternion_wxyz']
            dot = abs(sum(x*y for x,y in zip(qa,qb))) / math.sqrt(sum(x*x for x in qa)*sum(x*x for x in qb))
            angles.append(height * math.sqrt(max(0., 1. - min(1.,dot)**2)))
        metrics['rest_rotation_surface_motion_m'] = max(angles)
        # Sampling contract: evaluator supplies a terminal window, not unrelated
        # old stationary samples. Coverage is independently attested by adapter.
        if metrics['rest_window_sim_s'] >= REST_WINDOW_SIM_S and episode.get('terminal_truth_covered') is True:
            check('target_at_rest', metrics['rest_max_pairwise_distance_m'] <= REST_POSITION_M
                  and metrics['rest_rotation_surface_motion_m'] <= REST_POSITION_M)
        else:
            check('target_at_rest', None, 'No detached terminal window spanning at least 2 simulated seconds')
    else:
        check('target_at_rest', None, 'Missing valid detached terminal rest samples')

    moved = episode.get('nonrequested_max_displacement_m')
    names = episode.get('nonrequested_models')
    if (isinstance(names, list) and len(set(names)) == len(names)
            and isinstance(moved, dict) and set(moved) == set(names)
            and all(finite(v) and v >= 0 for v in moved.values())
            and episode.get('disturbance_truth_covered') is True):
        metrics['nonrequested_max_displacement_m'] = moved
        check('nonrequested_undisturbed', all(v <= DISPLACEMENT_M for v in moved.values()))
    else:
        check('nonrequested_undisturbed', None, 'Missing whole-episode displacement evidence for every non-requested cylinder')

    robot = episode.get('robot_final_xyz_m')
    if valid_home and xyz(robot) and episode.get('terminal_truth_covered') is True:
        metrics['robot_distance_home_xy_m'] = distance(robot[:2], home)
        check('robot_home', metrics['robot_distance_home_xy_m'] <= HOME_RADIUS_M)
    else:
        check('robot_home', None, 'Missing finite terminal robot truth or home')

    violations = episode.get('arbiter_violations')
    if isinstance(violations, list) and episode.get('arbiter_evidence_covered') is True:
        check('no_arbiter_violation', len(violations) == 0)
    else:
        check('no_arbiter_violation', None, 'Missing authority evidence or unresolved asynchronous observer flags')

    duration = episode.get('episode_wall_s')
    if finite(duration) and duration >= 0 and episode.get('episode_finished') is True:
        metrics['episode_wall_s'] = duration
        check('within_time_budget', duration <= EPISODE_WALL_BUDGET_S)
    elif episode.get('episode_finished') is False:
        check('within_time_budget', False)
    else:
        check('within_time_budget', None, 'Missing episode end or monotonic-wall duration')

    verdict = ('FAIL' if False in checks.values() else
               'PASS' if all(v is True for v in checks.values()) else 'UNSCORABLE')
    mission = episode.get('mission_verdict', 'UNOBSERVED')
    mission_success = True if mission == 'COMPLETE' else False if mission == 'ABORT' else None
    disagreement = (mission_success != (verdict == 'PASS')
                    if mission_success is not None and verdict != 'UNSCORABLE' else None)
    return {'definition_version': 'm0-v1', 'oracle_verdict': verdict,
            'mission_verdict': mission, 'mission_oracle_disagreement': disagreement,
            'checks': checks, 'metrics': metrics, 'missing_evidence': missing,
            'failed_conditions': [k for k, v in checks.items() if v is False]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = score(json.loads(args.input.read_text()))
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')


if __name__ == '__main__':
    main()
