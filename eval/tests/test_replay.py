import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from replay import check_dev,run
from evidence import file_hash


def test_replay_rejects_held_out_before_creating_output(tmp_path):
    source=tmp_path/'source';source.mkdir()
    (source/'manifest.json').write_text(json.dumps(dict(seed=1000000)))
    with pytest.raises(ValueError,match='Dev'):
        run(source,tmp_path/'output','historical')
    assert not (tmp_path/'output').exists()


def test_historical_command_uses_oracle_and_preserves_source_and_unknowns(tmp_path):
    source=Path(__file__).resolve().parents[2]/'docs/data/isaac_fetch/coco23/gazebo_seed6'
    before={p.name:file_hash(p) for p in source.iterdir() if p.is_file()}
    result=run(source,tmp_path/'replay','historical')
    assert result['qualified'] is False
    assert result['oracle_verdict']=='FAIL' and result['mission_verdict']=='ABORT'
    assert result['mission_oracle_disagreement'] is False
    assert result['first_violated_invariant']=='UNCLASSIFIED'
    assert result['first_supported_violation']['invariant']=='I19'
    assert result['first_supported_violation']['sim_s']==61.726
    assert before=={p.name:file_hash(p) for p in source.iterdir() if p.is_file()}
    analysis=json.loads((tmp_path/'replay/analysis.json').read_text())
    assert analysis['context_window']['end_sim_s']-analysis['context_window']['start_sim_s']==10
    assert analysis['earliest_cause_verified'] is False
    with pytest.raises(FileExistsError):run(source,tmp_path/'replay','historical')
