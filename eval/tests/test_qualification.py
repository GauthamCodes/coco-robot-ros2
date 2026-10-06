import copy
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qualification import qualify, robotics_process, cpu_percent, inventory


def clean():
    return dict(errors=[], processes=[], dds_segments=[], load1=2.,
                ram_available_bytes=8000, gpu={'free_bytes':5000}, cpu_ticks=[1]*8)


def policy():
    # Synthetic resource units/limits: not production qualification thresholds.
    return {'backends':{b:{p:dict(max_load1=12,min_ram_available_bytes=7000,
                               min_vram_free_bytes=4000) for p in ('preflight','runtime')}
                        for b in ('gazebo','isaac')}}


def test_clean_and_no_simulator_launch():
    with patch('subprocess.Popen', side_effect=AssertionError('unexpected process launch')):
        assert qualify(clean(),policy(),'isaac')['qualified']
        dirty=clean(); dirty['dds_segments']=[{'name':'fastrtps_orphan'}]
        assert not qualify(dirty,policy(),'isaac')['qualified']


@pytest.mark.parametrize('argv,comm,exe,maps',[
    (['gz sim server'],'ruby','/usr/bin/ruby',''),
    (['python','-m','coco_sim.isaac.runtime'],'python','/usr/bin/python',''),
    (['python','my_robot.py'],'python','/usr/bin/python','librclpy'),
    (['node','--ros-args'],'node','/tmp/node',''),
    (['ros2','launch'],'python','/usr/bin/python',''),
])
def test_foreign_process_signatures(argv,comm,exe,maps):
    assert robotics_process(argv,comm,exe,maps)


@pytest.mark.parametrize('field,value',[('load1',13),('ram_available_bytes',6999),('gpu',{'free_bytes':3999}),('gpu',None),('errors',['inventory denied'])])
def test_resource_and_inventory_fail_closed(field,value):
    s=clean(); s[field]=value
    assert not qualify(s,policy(),'gazebo')['qualified']


def test_owned_allowlist_rejects_pid_reuse():
    s=clean(); s['processes']=[dict(pid=2,start_ticks=99,robotics=True,argv=['gz sim server'])]
    assert qualify(s,policy(),'isaac',owned=[dict(pid=2,start_ticks=99)])['qualified']
    assert not qualify(s,policy(),'isaac',owned=[dict(pid=2,start_ticks=98)])['qualified']


def test_uncalibrated_is_blocked_and_runtime_violation_is_preserved():
    p=policy(); p['backends']['isaac']['preflight']['min_ram_available_bytes']=None
    assert not qualify(clean(),p,'isaac')['qualified']
    s=clean(); s['load1']=13
    assert not qualify(s,p,'isaac',phase='runtime')['qualified']


def test_cpu_percentage():
    assert cpu_percent({'cpu_ticks':[0]*8},{'cpu_ticks':[1,0,0,1,0,0,0,0]})==50


def test_explicit_background_allowlist_does_not_imply_process_ownership():
    from qualification import allowed_background
    rules=[dict(comm='systemd',uid=0,argv_prefix=['/sbin/init'])]
    assert allowed_background(dict(comm='systemd',uid=0,argv=['/sbin/init','splash']),rules)
    assert not allowed_background(dict(comm='systemd',uid=1000,argv=['/sbin/init']),rules)
    assert not allowed_background(dict(comm='python',uid=0,argv=['python','robot.py']),rules)
