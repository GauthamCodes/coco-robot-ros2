"""Structural/runtime smoke gate. Does not waive qualification or analyzer gaps."""
import json
from pathlib import Path
from evidence import bag_hash,file_hash
from invariants import threshold_keys
from topics import TOPICS

REQUIRED=('/clock','/mission/state','/amcl_pose','/tf','/diff_drive_controller/odom',
          '/cmd_vel_arbiter/status','/diff_drive_controller/cmd_vel','/perception/candidates',
          '/eval/ground_truth/state','/eval/graph','/eval/nav2/lifecycle','/diagnostics/mission_callbacks')


def validate_smoke(root):
    base=Path(__file__).resolve().parent
    summary=json.loads((Path(root)/'summary.json').read_text())
    reasons=[];backends=set();proof=[]
    thresholds=json.loads((base/'thresholds.json').read_text())['thresholds']
    if any(thresholds.get(k) is None for k in threshold_keys()):reasons.append('ANALYZER_CALIBRATION_INCOMPLETE')
    if json.loads((base/'host_policy.json').read_text())['status']!='VALIDATED':reasons.append('HOST_RESOURCE_PROFILE_NOT_VALIDATED')
    for row in summary['runs']:
        if row['state']=='BLOCKED':continue
        run=Path(root)/row['run_id'];m=json.loads((run/'manifest.json').read_text())
        if not m['qualified'] or m['state']!='COMPLETE':reasons.append(f'{run.name}: not qualified completed');continue
        if m['seed_group']!='dev' or m['seed'] not in (5,8):reasons.append(f'{run.name}: not registered Dev control');continue
        events=[json.loads(s) for s in (run/'logs/events.jsonl').read_text().splitlines()]
        observed={e['topic'] for e in events}
        missing=set(REQUIRED)-observed
        if missing:reasons.append(f'{run.name}: required trace streams missing: {sorted(missing)}')
        if m.get('bag_hash')!=bag_hash(run/'bag'):reasons.append(f'{run.name}: bag hash mismatch')
        analysis=json.loads((run/'analysis.json').read_text())
        if analysis['analyzer_work_items']:reasons.append(f'{run.name}: unvalidated analyzer derivations {analysis["analyzer_work_items"]}')
        if not (run/'logs/teardown.json').exists():reasons.append(f'{run.name}: teardown proof absent')
        proof.append({'run':str(run),'manifest_sha256':file_hash(run/'manifest.json'),'analysis_sha256':file_hash(run/'analysis.json')})
        backends.add(row['backend'])
    if backends!={'gazebo','isaac'}:reasons.append('BOTH_BACKENDS_QUALIFIED_SMOKE_REQUIRED')
    return {'validated':not reasons,'reasons':reasons,'proof':proof,
            'host_policy_sha256':file_hash(base/'host_policy.json'),'thresholds_sha256':file_hash(base/'thresholds.json'),
            'topics_sha256':file_hash(base/'topics.py')}
