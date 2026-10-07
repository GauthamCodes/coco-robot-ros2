import json
from pathlib import Path
from unittest.mock import patch
from collections import Counter
from evidence import atomic_json,bag_hash,file_hash
from validate import validate_smoke,REQUIRED
from invariants import RULES


def synthetic_smoke(root):
    base=Path(__file__).resolve().parents[1];rows=[]
    atomic_json(root/'batch.json',{'runtime_fingerprint':{}})
    for backend in ('gazebo','isaac'):
        for seed in (5,8):
            name=f'run-{backend}-{seed}';run=root/name;run.mkdir();(run/'logs').mkdir();(run/'bag').mkdir()
            # Explicit placeholder tests rejection; not a simulated/MCAP run.
            (run/'bag/placeholder').write_text('synthetic, not MCAP')
            atomic_json(run/'manifest.json',dict(qualified=True,state='COMPLETE',seed_group='dev',seed=seed,
                        job={'repeat':0},topics_sha256=file_hash(base/'topics.py'),bag_hash=bag_hash(run/'bag')))
            graph={'topics':{'/diff_drive_controller/cmd_vel':{'publishers':[{'name':'cmd_vel_arbiter','namespace':'/'}]}}}
            events=[dict(topic=t,data=graph if t=='/eval/graph' else {}) for t in REQUIRED]
            (run/'logs/events.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
            atomic_json(run/'logs/preflight.json',{'verdict':{'qualified':True}})
            atomic_json(run/'logs/teardown.json',{'errors':[],'qualification':{'qualified':True}})
            atomic_json(run/'oracle.json',{'oracle_verdict':'FAIL','mission_oracle_disagreement':False})
            atomic_json(run/'analysis.json',{'analyzer_work_items':[]})
            (run/'host_metrics.csv').write_text('qualified,rtf\nTrue,0.5\n')
            rows.append(dict(run_id=name,state='COMPLETE',backend=backend))
    atomic_json(root/'summary.json',{'runs':rows})
    return rows


def test_hash_of_placeholder_cannot_validate_smoke(tmp_path):
    synthetic_smoke(tmp_path)
    with patch('validate.runtime_fingerprint',return_value={}):result=validate_smoke(tmp_path)
    assert not result['validated']
    assert any('MCAP replay failed' in reason for reason in result['reasons'])


def test_smoke_rejects_disagreement_bad_teardown_and_missing_registered_job(tmp_path):
    rows=synthetic_smoke(tmp_path)
    run=tmp_path/rows[0]['run_id']
    atomic_json(run/'oracle.json',{'oracle_verdict':'FAIL','mission_oracle_disagreement':True})
    atomic_json(run/'logs/teardown.json',{'errors':['OWNED_PROCESSES_SURVIVED'],'qualification':{'qualified':False}})
    rows[-1]['state']='BLOCKED';atomic_json(tmp_path/'summary.json',{'runs':rows})
    with patch('validate.runtime_fingerprint',return_value={}),patch('validate.inspect_bag',return_value=dict(Counter(REQUIRED))):result=validate_smoke(tmp_path)
    assert any('oracle/mission disagreement' in r for r in result['reasons'])
    assert any('teardown failed' in r for r in result['reasons'])
    assert 'ALL_FOUR_REGISTERED_SMOKE_JOBS_REQUIRED' in result['reasons']
