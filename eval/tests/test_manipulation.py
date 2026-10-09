"""SYNTHETIC_ONLY traces, never robot runtime evidence or calibration."""
import copy
import json
import pytest
from manipulation import verify, PHASES, run

LIMITS=dict(relative_translation_m=.005, relative_rotation_rad=.01,
            max_truth_gap_sim_s=1.1, provenance='SYNTHETIC_ONLY regression limits')
MANIFEST=dict(seed=5,requested_colour='red')
ORACLE=dict(oracle_verdict='PASS',mission_verdict='COMPLETE',checks={'target_at_rest':True})

def fixture():
    events=[]
    def add(topic,t,data):events.append(dict(topic=topic,sim_s=t,wall_s=t*2,data=data))
    def mark(name,t):add('/diagnostics/manipulation_checkpoints',t,dict(checkpoint=name,stamp_ns=round(t*1e9),observation_contract_valid=True,observation_stamp_ns=round((t-.01)*1e9)))
    mark('observation_acquired',.5);mark('approach_complete',1)
    mark('grasp_request',2);add('/magnet/target_red/attach',2,{})
    add('/magnet/target_red/state',2.1,{'data':'attached'})
    mark('release_request',6);add('/magnet/target_red/detach',6,{})
    for t,x,z,gx,gz in [(1,0,.08,0,.1),(3,0,.08,0,.1),(4,0,.12,0,.14),(5,.1,.12,.1,.14),
                         (6,.1,.08,.1,.1),(7,.1,.08,.2,.2),(8,.1,.08,.3,.3)]:
        obj=dict(xyz_m=[x,0,z],quaternion_wxyz=[1,0,0,0])
        grip=dict(xyz_m=[gx,0,gz],quaternion_wxyz=[1,0,0,0],frame='world',source_sim_s=t,provenance='simulator_link_pose')
        add('/eval/ground_truth/state',t,dict(sim_s=t,frame='world',objects={'target_red':obj},gripper=grip))
    return events

def result(events=None,oracle=None,**kw):
    return verify(fixture() if events is None else events,MANIFEST,oracle or ORACLE,limits=LIMITS,**kw)

def statuses(r):return {p['phase']:p['status'] for p in r['phases']}

def truth(events):return [e['data'] for e in events if e['topic']=='/eval/ground_truth/state']

def test_valid_sequence_and_determinism():
    r=result();assert r['result']=='PASS';assert list(statuses(r))==list(PHASES)
    assert json.dumps(r,sort_keys=True)==json.dumps(result(),sort_keys=True)
    assert r['phases'][5]['invariant_results']['I21']['holds'] is None # proximity uncalibrated

@pytest.mark.parametrize('plugin',[False,True])
def test_command_or_report_never_proves_attachment(plugin):
    e=fixture()
    if not plugin:e=[r for r in e if not r['topic'].endswith('/state') or r['topic'].startswith('/eval')]
    for d in truth(e):d['objects']['target_red']['xyz_m']=[0,0,.08]
    s=statuses(result(e));assert s['physical_attachment']=='FAIL'
    assert s['plugin_attachment_report']==('PASS' if plugin else 'UNVERIFIED')

def test_attachment_then_failed_lift():
    e=fixture()
    for d in truth(e):
        if d['sim_s'] in (4,5):
            d['objects']['target_red']['xyz_m']=[.1*(d['sim_s']-3),0,.08]
            d['gripper']['xyz_m']=[.1*(d['sim_s']-3),0,.1]
    s=statuses(result(e));assert s['physical_attachment']=='PASS';assert s['physical_lift']=='FAIL'

def test_lift_without_retention():
    e=[e for e in fixture() if not(e['topic']=='/eval/ground_truth/state' and e['data']['sim_s']==5)]
    s=statuses(result(e));assert s['physical_lift']=='PASS';assert s['retention']=='UNVERIFIED'

@pytest.mark.parametrize('continued_follow',[False,True])
def test_failed_release(continued_follow):
    e=fixture()
    for d in truth(e):
        if d['sim_s']>=6:
            if continued_follow:d['objects']['target_red']['xyz_m']=[d['gripper']['xyz_m'][0],0,d['gripper']['xyz_m'][2]-.02]
            else:d['gripper']['xyz_m']=[.1,0,.1]
    assert statuses(result(e))['physical_release']==('FAIL' if continued_follow else 'UNVERIFIED')

def test_displacement_after_release():
    e=fixture();truth(e)[-1]['objects']['target_red']['xyz_m'][0]+=.02
    assert statuses(result(e))['post_release_stability']=='FAIL'

@pytest.mark.parametrize('field',['objects','gripper'])
def test_missing_physical_signal(field):
    e=fixture()
    for d in truth(e):d.pop(field)
    assert statuses(result(e))['physical_attachment'] in ('UNVERIFIED','UNSCORABLE')

@pytest.mark.parametrize('change',['stale','frame','nonfinite','conflict'])
def test_invalid_truth_clock_and_frame(change):
    e=fixture();d=truth(e)[2]
    if change=='stale':d['gripper']['source_sim_s']=1000000
    if change=='frame':d['frame']='base_footprint'
    if change=='nonfinite':d['objects']['target_red']['xyz_m'][0]=float('nan')
    if change=='conflict':
        row=copy.deepcopy(next(r for r in e if r.get('data') is d));row['data']['objects']['target_red']['xyz_m'][0]=.2;e.append(row)
    assert result(e)['result']=='UNSCORABLE'

def test_duplicates_and_out_of_order_do_not_manufacture_motion():
    e=fixture();e.reverse();e+=copy.deepcopy(e)
    r=result(e);assert r['result']=='PASS';assert r['duplicate_events']==len(e)//2

def test_missing_calibration_is_not_pass():
    r=verify(fixture(),MANIFEST,ORACLE)
    assert r['result']=='UNVERIFIED';assert statuses(r)['physical_attachment']=='UNVERIFIED'

def test_mission_oracle_disagreement_and_physical_progress():
    oracle=dict(ORACLE,oracle_verdict='FAIL',mission_oracle_disagreement=True)
    r=result(oracle=oracle);assert r['result']!='PASS';assert r['oracle']==oracle
    oracle=dict(ORACLE,mission_verdict='ABORT',mission_oracle_disagreement=True)
    assert statuses(result(oracle=oracle))['physical_lift']=='PASS'

def test_truncated_sidecar(tmp_path):
    (tmp_path/'logs').mkdir();(tmp_path/'manifest.json').write_text(json.dumps(MANIFEST))
    (tmp_path/'logs/events.jsonl').write_text('{"topic":')
    assert run(tmp_path,tmp_path/'out.json')['result']=='UNSCORABLE'

def test_trace_loss_blocks_all_passes():
    assert result(integrity_errors=['MCAP truncated'])['result']=='UNSCORABLE'
