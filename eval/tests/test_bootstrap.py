"""Bootstrap refusal, ownership, and denominator separation (no simulator)."""
import copy
import json
from unittest.mock import patch
import pytest
import bootstrap
from qualification import qualify
from topics import TOPICS


def snapshot():
    return dict(errors=[], processes=[], dds_segments=[], load1=2., cpu_count=12,
                ram_total_bytes=16*2**30, ram_available_bytes=12*2**30,
                gpu=dict(total_bytes=6*2**30, free_bytes=5*2**30),
                cpu_ticks=[1]*8, wall_epoch_ns=1)


def production():
    return {'backends':{b:{phase:dict(max_load1=12,min_ram_available_bytes=None,
                                    min_vram_free_bytes=None)
                           for phase in ('preflight','runtime')}
                        for b in ('gazebo','isaac')}}


def environment():
    return dict(ROS_DISTRO='jazzy', RMW_IMPLEMENTATION='rmw_cyclonedds_cpp',
                ROS2CLI_NO_DAEMON='1', GZ_IP='127.0.0.1', GZ_VERSION='harmonic',
                AMENT_PREFIX_PATH='/opt/ros/jazzy', CYCLONEDDS_URI='<NetworkInterface name="lo"/>')


def test_capacity_budget_does_not_mutate_or_qualify_production():
    original = production(); before = copy.deepcopy(original)
    policy, envelope = bootstrap.safety_policy(snapshot(), original, 65536)
    assert original == before
    assert not qualify(snapshot(), original, 'gazebo')['qualified']
    result = bootstrap.verdict(snapshot(), policy, 'gazebo', 82)
    assert result['bootstrap_safe'] and result['qualified'] is False
    assert result['m1_denominator_eligible'] is False
    assert envelope['limits']['gazebo']['runtime']['min_ram_available_bytes'] == 8*2**30
    assert envelope['limits']['gazebo']['runtime']['min_vram_free_bytes'] == 2*2**30


@pytest.mark.parametrize('change', [
    dict(errors=['unreadable exe']), dict(dds_segments=[dict(name='dds_foreign')]),
    dict(load1=13), dict(ram_available_bytes=7*2**30),
    dict(gpu=dict(total_bytes=6*2**30,free_bytes=2**30)),
    dict(processes=[dict(pid=42,start_ticks=7,ppid=1,robotics=True,
                        argv=['gz sim server'],ros_domain_id=115)]),
    dict(processes=[dict(pid=42,start_ticks=7,ppid=1,robotics=True,
                        argv=['python','-m','coco_sim.isaac.runtime'],ros_domain_id=82)]),
])
def test_safety_controls_remain_fail_closed(change):
    snap = snapshot(); policy, _ = bootstrap.safety_policy(snap, production(), 65536)
    snap.update(change)
    assert not bootstrap.verdict(snap,policy,'gazebo',82)['bootstrap_safe']


def test_stricter_production_limits_and_kernel_reserve_win():
    p = production(); p['backends']['gazebo']['runtime']['min_vram_free_bytes']=4*2**30
    policy,_ = bootstrap.safety_policy(snapshot(),p,2**20)
    assert policy['backends']['gazebo']['runtime']['min_ram_available_bytes']==16*2**30
    assert policy['backends']['gazebo']['runtime']['min_vram_free_bytes']==4*2**30


def test_ownership_rejects_reused_pid_and_same_domain():
    snap = snapshot(); snap['processes'] = [
        dict(pid=10,start_ticks=20,ppid=1), dict(pid=11,start_ticks=21,ppid=10),
        dict(pid=12,start_ticks=22,ppid=11),dict(pid=13,start_ticks=23,ppid=1)]
    assert {p['pid'] for p in bootstrap.owned_descendants(snap,[dict(pid=10,start_ticks=20)])} == {10,11,12}
    assert bootstrap.owned_descendants(snap,[dict(pid=10,start_ticks=19)]) == [dict(pid=10,start_ticks=19)]


def test_environment_missing_is_rejected():
    assert bootstrap.environment_reasons({})
    assert bootstrap.environment_reasons(environment()) == []


def test_blocked_preflight_never_launches_or_overwrites(tmp_path):
    snap=snapshot(); snap['errors']=['unreadable foreign metadata']
    with patch.object(bootstrap,'inventory',return_value=snap), \
         patch.object(bootstrap,'load_policy',return_value=production()), \
         patch.object(bootstrap.subprocess,'check_output',side_effect=['abc','']), \
         patch.object(bootstrap.subprocess,'Popen',side_effect=AssertionError('unsafe launch')), \
         patch.dict(bootstrap.os.environ,environment(),clear=True):
        assert bootstrap.run_bootstrap(tmp_path/'blocked','gazebo') == 3
    m=json.loads((tmp_path/'blocked/manifest.json').read_text())
    assert m['state']=='BLOCKED_BOOTSTRAP' and not m['qualified']
    assert not m['satisfies_m1_8'] and not m['test_a']
    with pytest.raises(FileExistsError):
        bootstrap.run_bootstrap(tmp_path/'blocked','gazebo')


def test_resource_abort_stops_only_owned_child_and_retains_samples(tmp_path):
    snap=snapshot(); runtime=copy.deepcopy(snap); runtime['ram_available_bytes']=1
    child=type('Child',(),dict(pid=900,poll=lambda self:None))()
    with patch.object(bootstrap,'inventory',side_effect=[snap,runtime,snap]), \
         patch.object(bootstrap,'load_policy',return_value=production()), \
         patch.object(bootstrap.subprocess,'check_output',side_effect=['abc','']), \
         patch.object(bootstrap.subprocess,'Popen',return_value=child), \
         patch.object(bootstrap,'identity',side_effect=[dict(pid=900,start_ticks=1), OSError()]), \
         patch.object(bootstrap,'stop') as stop, \
         patch('environment.capture',return_value={}), \
         patch.dict(bootstrap.os.environ,environment(),clear=True):
        assert bootstrap.run_bootstrap(tmp_path/'abort','gazebo')==3
    stop.assert_called_once_with('recorder',child)
    manifest=json.loads((tmp_path/'abort/manifest.json').read_text())
    assert manifest['state']=='ABORTED_BOOTSTRAP_RESOURCE_LIMIT'
    assert manifest['qualified'] is False
    assert (tmp_path/'abort/host_metrics.jsonl').exists()
    assert json.loads((tmp_path/'abort/resource_summary.json').read_text())['sample_count']==1
    assert json.loads((tmp_path/'abort/oracle.json').read_text())['oracle_verdict']=='UNSCORABLE'
    assert json.loads((tmp_path/'abort/manipulation.json').read_text())['result']=='UNSCORABLE'


def test_engineering_camera_extension_does_not_change_production_contract():
    import bootstrap_recorder
    assert '/camera/image_raw' not in TOPICS


@pytest.mark.parametrize('seconds,domain',[(0,82),(601,82),(120,233), (120,-1)])
def test_bounds_cannot_be_disabled(tmp_path,seconds,domain):
    with pytest.raises(ValueError):
        bootstrap.run_bootstrap(tmp_path/'invalid','gazebo',domain,seconds)


def test_bootstrap_pass_cannot_calibrate_production(tmp_path):
    from calibration import derive
    control=tmp_path/'control';control.mkdir()
    (control/'manifest.json').write_text(json.dumps(dict(seed_group='dev',qualified=False,
                                          execution_class='NON_QUALIFYING')))
    (control/'oracle.json').write_text(json.dumps(dict(oracle_verdict='PASS')))
    with pytest.raises(ValueError,match='qualified oracle-PASS'):
        derive([control],{})
