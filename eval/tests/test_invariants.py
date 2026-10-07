import copy
import pytest
from analyzer import analyze
from invariants import RULES,evaluate,threshold_keys
from calibration import derive


def fixture(invariant):
    thresholds={k:1. for k in threshold_keys()}
    values={'stage_budget_sim_s':1.}
    for key,op,source in RULES[invariant]:
        limit=values[source[1:]] if isinstance(source,str) and source.startswith('$') else thresholds[source] if isinstance(source,str) else source
        values[key]=limit if op=='eq' else limit/2 if op=='le' else limit*2
    return values,thresholds


@pytest.mark.parametrize('invariant',list(RULES))
def test_passing_fixture_every_catalog_invariant(invariant):
    values,thresholds=fixture(invariant)
    assert evaluate(invariant,values,thresholds)['holds'] is True


@pytest.mark.parametrize('invariant',list(RULES))
def test_failing_fixture_every_catalog_invariant(invariant):
    values,thresholds=fixture(invariant)
    field,op,source=RULES[invariant][0]
    limit=values[source[1:]] if isinstance(source,str) and source.startswith('$') else thresholds[source] if isinstance(source,str) else source
    values[field]=not limit if op=='eq' else limit*2 if op=='le' else limit/2
    assert evaluate(invariant,values,thresholds)['holds'] is False


@pytest.mark.parametrize('invariant',list(RULES))
def test_missing_evidence_is_never_a_pass(invariant):
    assert evaluate(invariant,{}, {})['holds'] is None


def test_first_divergence_time_order_context_and_unknown_preserved():
    events=[dict(sim_s=20,mission_stage='GRASP',measurements={'lift_height_m':0},invariants=['I21']),
            dict(sim_s=10,mission_stage='NAVIGATION',measurements={'planner_active':False},invariants=['I08']),
            dict(sim_s=4,measurements={}),dict(sim_s=15,measurements={})]
    result=analyze(events,{},'ABORT','FAIL')
    assert result['first_violated_invariant']=='I08'
    assert result['simulation_timestamp']==10
    assert result['context_window']['start_sim_s']==5 and result['context_window']['end_sim_s']==15
    assert len(result['context_window']['events'])==2
    assert analyze([],{},'ABORT','FAIL')['first_violated_invariant']=='UNCLASSIFIED'


def test_calibration_rejects_held_out_and_unqualified(tmp_path):
    import json
    (tmp_path/'manifest.json').write_text(json.dumps({'seed_group':'test_a','qualified':True}))
    (tmp_path/'oracle.json').write_text(json.dumps({'oracle_verdict':'PASS'}))
    with pytest.raises(ValueError,match='Dev'):derive([tmp_path],{})


def test_raw_incomplete_catalog_keeps_supported_breach_unclassified():
    events=[dict(sim_s=10,mission_stage='GRASP',measurements={'nonrequested_displacement_m':.01},invariants=['I19'])]
    result=analyze(events,{},'ABORT','FAIL',require_catalog_coverage=True)
    assert result['first_violated_invariant']=='UNCLASSIFIED'
    assert result['first_supported_violation']['invariant']=='I19'
    assert not result['earliest_cause_verified'] and result['first_violation'] is None


def test_catalog_coverage_tracks_each_rule_not_one_supported_fragment():
    result=analyze([dict(sim_s=1,measurements={'moveit_execution_succeeded':True},invariants=['I20'])],{})
    assert 'I20' in result['analyzer_work_items']
    assert result['coverage']['I20']['measured_fields']==['moveit_execution_succeeded']
