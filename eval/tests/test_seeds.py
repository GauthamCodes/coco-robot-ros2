import copy
import json
from pathlib import Path
import sys
import pytest
import yaml

EVAL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(EVAL))
from seed_policy import validate, expand


def policy():
    return yaml.safe_load((EVAL/'seeds.yaml').read_text())


def test_disjoint_and_size():
    assert validate(policy())==dict(dev=10033,test_a=60,reserve_m4=60)


@pytest.mark.parametrize('group',['test_a','reserve_m4'])
def test_overlap_rejected(group):
    p=policy();p[group]['inclusive_ranges']=[[0,59]]
    with pytest.raises(AssertionError):validate(p)


def test_reserve_test_overlap_rejected():
    p=policy();p['reserve_m4']['inclusive_ranges']=p['test_a']['inclusive_ranges']
    with pytest.raises(AssertionError):validate(p)


def test_previously_generated_layouts_are_dev():
    p=policy();dev=expand(p['dev'])
    assert set(range(10000))|{12345,99999,2147483647} <= dev
    # Read saved historical numeric IDs only; never generate a new layout.
    def seeds(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if k=='seed' and isinstance(v,int):yield v
                yield from seeds(v)
        elif isinstance(value,list):
            for v in value:yield from seeds(v)
    for f in (EVAL.parent/'docs/data').rglob('*.json'):
        try:data=json.loads(f.read_text())
        except (ValueError,UnicodeError):continue
        assert set(seeds(data))<=dev, f


def test_used_pool_cannot_claim_untouched():
    p=policy();p['test_a']['used']=True
    with pytest.raises(AssertionError):validate(p)
