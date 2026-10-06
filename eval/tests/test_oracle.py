import copy
import importlib.util
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from oracle import score
from environment import dds_config, command


def fixture():
    return dict(home_xy_m=[-2., 0.], target_height_m=.158,
                target_final_xyz_m=[-1.9, 0., .079],
                target_rest_samples=[dict(sim_s=98., xyz_m=[-1.9,0.,.079], attached=False,quaternion_wxyz=[1.,0.,0.,0.]),
                                     dict(sim_s=100., xyz_m=[-1.9,0.,.079], attached=False,quaternion_wxyz=[1.,0.,0.,0.])],
                nonrequested_models=['green','blue','yellow'],
                nonrequested_max_displacement_m=dict(green=0.,blue=0.,yellow=0.),
                terminal_truth_covered=True, disturbance_truth_covered=True,
                robot_final_xyz_m=[-2.,0.,.03], arbiter_violations=[],
                arbiter_evidence_covered=True, episode_wall_s=100.,
                episode_finished=True, mission_verdict='COMPLETE')


def test_success():
    r=score(fixture()); assert r['oracle_verdict']=='PASS'
    assert r['mission_oracle_disagreement'] is False


@pytest.mark.parametrize('key,value,condition',[
    ('target_final_xyz_m',[-1.49,0.,.079],'target_in_placement_zone'),
    ('target_final_xyz_m',[-2.,0.,.158],'target_in_placement_zone'),
    ('nonrequested_max_displacement_m',dict(green=.006,blue=0.,yellow=0.),'nonrequested_undisturbed'),
    ('robot_final_xyz_m',[-1.49,0.,.03],'robot_home'),
    ('arbiter_violations',['bypass'],'no_arbiter_violation'),
    ('episode_wall_s',1200.01,'within_time_budget'),
    ('episode_finished',False,'within_time_budget'),
])
def test_each_failure(key,value,condition):
    e=fixture(); e[key]=value; r=score(e)
    assert r['oracle_verdict']=='FAIL'; assert condition in r['failed_conditions']
    assert r['mission_oracle_disagreement'] is True


def test_target_moving():
    e=fixture(); e['target_rest_samples'][0]['xyz_m'][0]-=.006
    assert score(e)['checks']['target_at_rest'] is False


@pytest.mark.parametrize('key',[
    'home_xy_m','target_final_xyz_m','target_height_m','target_rest_samples',
    'nonrequested_models','nonrequested_max_displacement_m','robot_final_xyz_m',
    'arbiter_violations','arbiter_evidence_covered','episode_wall_s','episode_finished',
    'terminal_truth_covered','disturbance_truth_covered'])
def test_missing_is_unscorable(key):
    e=fixture();del e[key];r=score(e)
    assert r['oracle_verdict']=='UNSCORABLE'; assert r['missing_evidence']
    assert r['mission_oracle_disagreement'] is None


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-float('inf'),'0',True])
def test_invalid_facts(bad):
    e=fixture();e['target_final_xyz_m'][0]=bad
    assert score(e)['oracle_verdict']=='UNSCORABLE'


def test_unknown_and_false_proves_failure():
    e=fixture();e.pop('arbiter_violations');e['robot_final_xyz_m']=[10.,0.,0.]
    assert score(e)['oracle_verdict']=='FAIL'


def test_mission_not_oracle():
    e=fixture();e['mission_verdict']='ABORT';r=score(e)
    assert r['oracle_verdict']=='PASS'; assert r['mission_oracle_disagreement'] is True
    e['mission_verdict']='UNOBSERVED';assert score(e)['oracle_verdict']=='PASS'


def test_boundaries():
    e=fixture();e['target_final_xyz_m']=[-1.5,0.,.079]
    e['robot_final_xyz_m']=[-1.5,0.,0.]
    e['nonrequested_max_displacement_m']['green']=.005
    e['episode_wall_s']=1200.
    assert score(e)['oracle_verdict']=='PASS'


@pytest.mark.parametrize('change',['short','reversed','attached','missing_attachment'])
def test_rest_evidence(change):
    e=fixture(); r=e['target_rest_samples']
    if change=='short':r[0]['sim_s']=99.
    elif change=='reversed':r.reverse()
    elif change=='attached':r[0]['attached']=True
    else:del r[0]['attached']
    assert score(e)['oracle_verdict']=='UNSCORABLE'


def test_full_rest_window_includes_middle_motion():
    e=fixture();e['target_rest_samples'].insert(1,dict(sim_s=99.,xyz_m=[-1.8,0.,.079],attached=False,quaternion_wxyz=[1.,0.,0.,0.]))
    assert score(e)['checks']['target_at_rest'] is False


def test_dds_file_inventory(tmp_path):
    p=tmp_path/'dds.xml';p.write_text('<CycloneDDS/>')
    r=dds_config('file://'+str(p));assert r['content']=='<CycloneDDS/>'
    assert len(r['sha256'])==64
    assert 'unavailable' in dds_config(str(tmp_path/'absent'))
    assert dds_config('<CycloneDDS/>')['kind']=='inline'
    assert dds_config('')['kind']=='unset'


def test_missing_command_explicit():
    assert 'unavailable' in command(['/definitely/absent/coco-program'])


def test_spinning_is_not_rest():
    e=fixture(); e['target_rest_samples'][0]['quaternion_wxyz']=[.70710678,0.,0.,.70710678]
    assert score(e)['checks']['target_at_rest'] is False


def test_quaternion_sign_equivalence():
    e=fixture(); e['target_rest_samples'][0]['quaternion_wxyz']=[-1.,0.,0.,0.]
    assert score(e)['oracle_verdict']=='PASS'


def test_historical_adapter_string_stamps_and_side_by_side(tmp_path):
    import gzip
    import json
    from backcheck import normalized
    manifest=dict(backend='gazebo',requested_colour='red',robot_start=dict(x=-2.,y=0.),
                  targets=[dict(model='target_red',height=.158),dict(model='target_green',height=.158)])
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    (tmp_path/'result.json').write_text(json.dumps(dict(mission='ABORT',mission_wall_s=10.,stop_breaches=0)))
    (tmp_path/'command_graph.json').write_text(json.dumps({'/diff_drive_controller/cmd_vel':['cmd_vel_arbiter']}))
    obs=[dict(topic='/mission/state',data='state=LOCALIZE prev=IDLE',sim_s=0.),
         dict(topic='/magnet/target_red/state',data='detached',sim_s=0.),
         dict(topic='/mission/state',data='state=ABORT prev=PLACE',sim_s=4.)]
    with gzip.open(tmp_path/'observations.jsonl.gz','wt') as f:
        f.write(''.join(json.dumps(r)+'\n' for r in obs))
    with gzip.open(tmp_path/'physical.jsonl.gz','wt') as f:
        for t in (0,2,4):
            poses=[dict(name=n,position=dict(x=x,y=0.,z=z),orientation=dict(w=1.))
                   for n,x,z in [('coco',-2.,.03),('target_red',-2.,.079),('target_green',4.,.729)]]
            f.write(json.dumps(dict(header=dict(stamp=dict(sec=str(t),nsec=0)),pose=poses))+'\n')
    result=score(normalized(tmp_path))
    assert result['oracle_verdict']=='PASS'
    assert result['mission_verdict']=='ABORT'
    assert result['mission_oracle_disagreement'] is True


def test_stale_terminal_pose_cannot_prove_placement_failure():
    e=fixture();e['target_final_xyz_m']=[10.,0.,.079];e['terminal_truth_covered']=False
    assert score(e)['checks']['target_in_placement_zone'] is None


def test_logged_violation_fails_even_with_partial_coverage():
    e=fixture();e['arbiter_violations']=['bypass'];e['arbiter_evidence_covered']=False
    assert score(e)['oracle_verdict']=='FAIL'


def test_overflowed_quaternion_invalid():
    e=fixture();e['target_rest_samples'][0]['quaternion_wxyz']=[1e308]*4
    assert score(e)['checks']['target_at_rest'] is None
