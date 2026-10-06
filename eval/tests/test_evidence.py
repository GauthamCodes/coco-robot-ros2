import json
from pathlib import Path
from unittest.mock import patch
import pytest
from evidence import atomic_json,bag_hash,retain_bags,disk_check,outside_git,REPO


def test_retention_preserves_failures_unqualified_interrupted_and_two_controls(tmp_path):
    paths=[]
    for i,(state,qualified,verdict) in enumerate([('COMPLETE',True,'PASS')]*3+[('COMPLETE',True,'FAIL'),('COMPLETE',False,'PASS'),('INTERRUPTED',True,'PASS')]):
        p=tmp_path/str(i);p.mkdir();(p/'bag').mkdir();(p/'bag/data.mcap').write_bytes(b'evidence')
        atomic_json(p/'manifest.json',dict(state=state,qualified=qualified,mission_verdict='COMPLETE',invariant_label='NONE'))
        atomic_json(p/'oracle.json',dict(oracle_verdict=verdict));paths.append(p)
    retain_bags(paths)
    assert [(p/'bag/data.mcap').exists() for p in paths]==[True,True,False,True,True,True]
    assert json.loads((paths[2]/'manifest.json').read_text())['bag_hash']['files']


def test_hash_detects_corruption_and_root_guard(tmp_path):
    (tmp_path/'data.mcap').write_bytes(b'a');a=bag_hash(tmp_path)
    (tmp_path/'data.mcap').write_bytes(b'b');assert bag_hash(tmp_path)!=a
    with pytest.raises(ValueError):outside_git(REPO/'runs')


def test_disk_budget_blocks_before_launch(tmp_path):
    (tmp_path/'log').write_bytes(b'12345')
    p=dict(reserve_free_bytes=2,max_batch_bytes=4,max_run_bytes=2)
    with patch('evidence.shutil.disk_usage',return_value=type('Usage',(),{'free':3})()):
        result=disk_check(tmp_path,p,starting=True)
    assert not result['ok']
    assert 'BATCH_DISK_BUDGET_EXCEEDED' in result['reasons']
