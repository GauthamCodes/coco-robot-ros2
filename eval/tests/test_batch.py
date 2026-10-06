import json
from pathlib import Path
from unittest.mock import patch
import pytest
from batch import run_batch,reconcile
from cli import load_campaign,BASE
from evidence import atomic_json
from batch_statistics import wilson,determinism


def test_dirty_host_blocks_all_process_launches_and_is_preserved(tmp_path):
    snapshot=dict(errors=[],processes=[dict(pid=99,start_ticks=1,pgid=99,robotics=True,argv=['gz sim server'])],
                  dds_segments=[],load1=0,ram_available_bytes=100,gpu={'free_bytes':100})
    policy={'backends':{'isaac':{'preflight':dict(max_load1=1,min_ram_available_bytes=1,min_vram_free_bytes=1)}}}
    job=dict(backend='isaac',seed=5,seed_group='dev',repeat=0)
    with patch('batch.capture',return_value={'synthetic':True}),patch('batch.subprocess.check_output',return_value='synthetic-sha'),patch('batch.subprocess.Popen',side_effect=AssertionError('preflight launched a process')):
        rc=run_batch(tmp_path,[job],BASE/'campaigns/m1_smoke.yaml',collect=lambda:snapshot,policy=policy,
                     storage=dict(max_batch_bytes=10**8,max_run_bytes=1000,reserve_free_bytes=1000,controls_per_batch=2))
    assert rc==3
    run=next(tmp_path.glob('run-*'))
    assert all((run/f).exists() for f in ('manifest.json','env.json','host_metrics.csv','logs','bag','oracle.json','analysis.json'))
    assert json.loads((run/'manifest.json').read_text())['state']=='BLOCKED'
    assert json.loads((tmp_path/'summary.json').read_text())['blocked_count']==1


def test_crash_reconciliation_preserves_failed_evidence_and_rejects_live_ownership(tmp_path):
    run=tmp_path/'run-0';run.mkdir()
    atomic_json(run/'manifest.json',dict(state='RUNNING',owned_processes=[dict(pid=9999999,start_ticks=1,pgid=9999999)],qualified=True,qualification_reasons=[]))
    with patch('batch.group_alive',return_value=False):assert reconcile(tmp_path)==[run]
    assert json.loads((run/'manifest.json').read_text())['state']=='INTERRUPTED'
    atomic_json(run/'manifest.json',dict(state='RUNNING',owned_processes=[dict(pid=9999999,start_ticks=1,pgid=9999999)]))
    with patch('batch.group_alive',return_value=True),pytest.raises(RuntimeError,match='reconciliation'):reconcile(tmp_path)


def test_campaign_counts_disjoint_pools_and_reserve_untouched():
    sizes={name:len(load_campaign(BASE/'campaigns'/name)[1]) for name in ('m1_smoke.yaml','m1_determinism.yaml','m1_breadth.yaml','m1_test_a.yaml')}
    assert list(sizes.values())==[4,20,60,60]
    _,jobs=load_campaign(BASE/'campaigns/m1_test_a.yaml')
    assert {r['seed'] for r in jobs}==set(range(1000000,1000030))


def test_wilson_and_determinism_do_not_count_unqualified():
    assert wilson(0,0) is None
    assert wilson(30,30)[0]==pytest.approx(.88648,abs=.0001)
    rows=[dict(backend='isaac',seed=6,qualified=True,oracle_verdict='FAIL',invariant_label='I09')]*3
    assert determinism(rows)[0]['verdict']=='deterministic'
    assert determinism([dict(rows[0],qualified=False)])[0:] == []


def test_mid_run_resource_violation_unqualifies_and_preserves_evidence(tmp_path):
    from batch import initialize,execute
    root=tmp_path/'batch';root.mkdir();run=root/'run-0'
    job=dict(backend='isaac',seed=5,seed_group='dev',repeat=0)
    def snapshot(t,load):
        return dict(errors=[],processes=[],dds_segments=[],load1=load,ram_available_bytes=10000,
                    gpu={'free_bytes':10000},cpu_ticks=[t]*8,wall_epoch_ns=t*10**9,monotonic_s=t)
    snapshots=iter([snapshot(1,0),snapshot(2,20),snapshot(3,0)])
    policy={'backends':{'isaac':{p:dict(max_load1=12,min_ram_available_bytes=1,min_vram_free_bytes=1) for p in ('preflight','runtime')}}}
    storage=dict(max_batch_bytes=10**8,max_run_bytes=10**7,reserve_free_bytes=1000)
    class Child:
        pid=777
        returncode=None
        def poll(self):return None
    with patch('batch.capture',return_value={'synthetic':True}):manifest=initialize(run,job,'fixture',root)
    atomic_json(run/'logs/recorder_ready.json',{'synthetic':True})
    (run/'bag').mkdir();(run/'bag/fixture.mcap').write_bytes(b'preserved synthetic placeholder, not MCAP proof')
    with patch.dict('os.environ',{'ROS_DOMAIN_ID':'184'}),patch('batch.subprocess.Popen',return_value=Child()),patch('batch.identity',return_value=dict(pid=777,start_ticks=1,pgid=777)),patch('batch.stop'),patch('batch.availability',return_value={'synthetic':True}):
        assert execute(run,job,manifest,root,policy,storage,collect=lambda:next(snapshots)) is False
    value=json.loads((run/'manifest.json').read_text())
    assert not value['qualified'] and value['state']=='INTERRUPTED'
    assert any('max_load1' in r for r in value['qualification_reasons'])
    assert (run/'bag/fixture.mcap').exists()
    assert len((run/'host_metrics.csv').read_text().splitlines())==2


def test_resume_checks_owned_groups_even_after_teardown_failure(tmp_path):
    run=tmp_path/'run-interrupted';run.mkdir()
    atomic_json(run/'manifest.json',dict(state='INTERRUPTED',owned_processes=[dict(pid=9999999,start_ticks=1,pgid=9999999)],qualified=False,qualification_reasons=['TEARDOWN_FAILED']))
    with patch('batch.group_alive',return_value=True),pytest.raises(RuntimeError,match='reconciliation'):reconcile(tmp_path)


def test_corrupt_trace_is_not_silently_scored(tmp_path):
    from batch import read_events
    (tmp_path/'logs').mkdir()
    (tmp_path/'logs/events.jsonl').write_text('{"topic":"/clock"}\n{"truncated":')
    with pytest.raises(json.JSONDecodeError):read_events(tmp_path)
    assert 'truncated' in (tmp_path/'logs/events.jsonl').read_text()
