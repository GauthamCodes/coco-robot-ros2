"""Check saved evidence consistency; does not execute or command a simulator."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
r = json.loads((ROOT / 'comparison.json').read_text())
assert len(r['episodes']) == 10
assert len({(e['backend'], e['seed']) for e in r['episodes']}) == 10
checks = []
for e in r['episodes']:
    folder = ROOT / e['evidence']
    meta = json.loads((folder / 'meta.json').read_text())
    assert meta['head'] == r['starting_sha']
    assert e['wheel_publishers'] == ['cmd_vel_arbiter']
    for name, digest in meta['source_sha256'].items():
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == digest, name
    inputs = json.loads((folder / 'robot_inputs.json').read_text())
    assert set(inputs) == {'episode_id', 'requested_colour'}, inputs
    assert inputs['requested_colour'] == 'red'
    assert max(abs(v) for v in e['measurements']['initial_target_manifest_error_xyz_m']) < .005
    assert not e['measurements'].get('evaluation_error')
    if e['physically_verified_complete']:
        assert e['mission'] == 'COMPLETE'
        assert e['stages']['placement'] == 'upright_floor_pose'
        assert e['measurements']['final_magnet_attached'] is None
        assert e['measurements']['post_release']['samples'] >= 2
    checks.append({'backend': e['backend'], 'seed': e['seed'], 'source_digests_unchanged': True,
                   'sole_arbiter': True, 'robot_inputs_task_only': True,
                   'initial_red_placement_within_5mm': True,
                   'physical_complete': e['physically_verified_complete'], 'protocol_pass': e['protocol_passed']})
for seed in range(5, 10):
    a, b = [json.loads((ROOT / f'{backend}_seed{seed}/manifest.json').read_text()) for backend in ('isaac', 'gazebo')]
    assert {k: v for k, v in a.items() if k not in ('backend', 'episode_id')} == {k: v for k, v in b.items() if k not in ('backend', 'episode_id')}
regression = json.loads((ROOT / 'tests/summary.json').read_text())
assert regression['passed'] == 1952
assert all(line.split()[1] == '0' for line in regression['exit_codes'].splitlines())
(ROOT / 'evidence_checks.json').write_text(json.dumps({'checks': checks, 'matched_seeds': list(range(5, 10)),
    'regression_passed': regression['passed'], 'implementation_changed': False}, indent=2) + '\n')
print('PASS: 10 episodes, 5 matched layouts, unchanged runtime sources, sole arbiter, task-only inputs, measured placement, physical completion evidence, 1952 regression tests')
