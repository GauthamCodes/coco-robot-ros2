"""Structural/runtime smoke gate. Does not waive qualification or analyzer gaps."""
import json
import csv
from collections import Counter
from pathlib import Path
from evidence import bag_hash,file_hash,runtime_fingerprint
from invariants import threshold_keys
from topics import TOPICS
from graph import violations
from normalize import payload

REQUIRED=('/clock','/mission/state','/amcl_pose','/tf','/diff_drive_controller/odom',
          '/cmd_vel_arbiter/status','/diff_drive_controller/cmd_vel','/perception/candidates',
          '/eval/ground_truth/state','/eval/graph','/eval/nav2/lifecycle','/diagnostics/mission_callbacks','/diagnostics/arbiter_commands')


def inspect_bag(path):
    """Read every MCAP record through rosbag2; a hash of junk is not proof."""
    import rosbag2_py
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(path),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    counts=Counter()
    while reader.has_next():
        topic,data,stamp=reader.read_next()
        if topic not in TOPICS or not data or stamp<0:raise ValueError('Invalid fixed-topic bag record')
        counts[topic]+=1
    if not counts:raise ValueError('Empty bag')
    return dict(counts)


def validate_smoke(root):
    base=Path(__file__).resolve().parent
    summary=json.loads((Path(root)/'summary.json').read_text())
    registration=json.loads((Path(root)/'batch.json').read_text())
    reasons=[];backends=set();proof=[];jobs=set()
    if registration.get('runtime_fingerprint')!=runtime_fingerprint():reasons.append('SMOKE_SOURCE_CHANGED')
    thresholds=json.loads((base/'thresholds.json').read_text())['thresholds']
    if any(thresholds.get(k) is None for k in threshold_keys()):reasons.append('ANALYZER_CALIBRATION_INCOMPLETE')
    if json.loads((base/'host_policy.json').read_text())['status']!='VALIDATED':reasons.append('HOST_RESOURCE_PROFILE_NOT_VALIDATED')
    for row in summary['runs']:
        if row['state']=='BLOCKED':continue
        run=Path(root)/row['run_id'];m=json.loads((run/'manifest.json').read_text())
        if not m['qualified'] or m['state']!='COMPLETE':reasons.append(f'{run.name}: not qualified completed');continue
        if m['seed_group']!='dev' or m['seed'] not in (5,8):reasons.append(f'{run.name}: not registered Dev control');continue
        if m.get('topics_sha256')!=file_hash(base/'topics.py'):reasons.append(f'{run.name}: stale topic contract')
        job=(row['backend'],m['seed'],m['job']['repeat'])
        if job in jobs:reasons.append(f'{run.name}: duplicate completed smoke job')
        jobs.add(job)
        events=[json.loads(s) for s in (run/'logs/events.jsonl').read_text().splitlines()]
        observed={e['topic'] for e in events}
        missing=set(REQUIRED)-observed
        if missing:reasons.append(f'{run.name}: required trace streams missing: {sorted(missing)}')
        if m.get('bag_hash')!=bag_hash(run/'bag'):reasons.append(f'{run.name}: bag hash mismatch')
        try:
            counts=inspect_bag(run/'bag')
            if counts!=dict(Counter(e['topic'] for e in events)):reasons.append(f'{run.name}: bag/decoded trace count mismatch')
        except Exception as exc:reasons.append(f'{run.name}: MCAP replay failed: {exc}')
        oracle=json.loads((run/'oracle.json').read_text())
        if oracle.get('mission_oracle_disagreement') is True:reasons.append(f'{run.name}: oracle/mission disagreement')
        if oracle.get('oracle_verdict') not in ('PASS','FAIL'):reasons.append(f'{run.name}: oracle unscorable')
        if not json.loads((run/'logs/preflight.json').read_text())['verdict']['qualified']:reasons.append(f'{run.name}: preflight rejected')
        with (run/'host_metrics.csv').open() as stream:metrics=list(csv.DictReader(stream))
        if not metrics or any(r['qualified']!='True' for r in metrics):reasons.append(f'{run.name}: absent/unqualified host sampling')
        if not any(r['rtf'] for r in metrics):reasons.append(f'{run.name}: RTF unmeasured')
        for event in events:
            if event['topic']=='/eval/graph' and any(v['invariant']=='GROUND_TRUTH_ISOLATION' for v in violations(payload(event))):
                reasons.append(f'{run.name}: autonomy /eval subscription observed');break
        analysis=json.loads((run/'analysis.json').read_text())
        if analysis['analyzer_work_items']:reasons.append(f'{run.name}: unvalidated analyzer derivations {analysis["analyzer_work_items"]}')
        if not (run/'logs/teardown.json').exists():reasons.append(f'{run.name}: teardown proof absent')
        else:
            teardown=json.loads((run/'logs/teardown.json').read_text())
            if teardown['errors'] or not teardown['qualification']['qualified'] or teardown.get('surviving_owned_processes'):
                reasons.append(f'{run.name}: teardown failed')
        proof.append({'run':str(run),'manifest_sha256':file_hash(run/'manifest.json'),'analysis_sha256':file_hash(run/'analysis.json')})
        backends.add(row['backend'])
    if backends!={'gazebo','isaac'}:reasons.append('BOTH_BACKENDS_QUALIFIED_SMOKE_REQUIRED')
    if jobs!={(b,s,0) for b in ('gazebo','isaac') for s in (5,8)}:reasons.append('ALL_FOUR_REGISTERED_SMOKE_JOBS_REQUIRED')
    return {'validated':not reasons,'reasons':reasons,'proof':proof,'runtime_fingerprint':runtime_fingerprint(),
            'host_policy_sha256':file_hash(base/'host_policy.json'),'thresholds_sha256':file_hash(base/'thresholds.json'),
            'topics_sha256':file_hash(base/'topics.py')}
