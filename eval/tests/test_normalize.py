import json
from normalize import normalized,oracle_facts
from oracle import score


def event(topic,sim,value):
    return dict(topic=topic,sim_s=sim,wall_s=sim,data={'data':json.dumps(value) if not isinstance(value,str) else value})


def test_truth_displacement_first_time_and_oracle_failure():
    manifest=dict(requested_colour='red',home_xy_m=[-2,0],targets=[dict(model='target_red',height=.158),dict(model='target_blue',height=.158)])
    events=[event('/mission/state',1,'state=LOCALIZE')]
    for t,x in [(1,0),(2,0),(3,.01)]:
        objects={n:dict(xyz_m=[x if n.endswith('blue') else 2,0,.079],quaternion_wxyz=[1,0,0,0],attached=False) for n in ('target_red','target_blue')}
        events.append(event('/eval/ground_truth/state',t,dict(sim_s=t,robot={'xyz_m':[-2,0,0]},objects=objects)))
    events.append(event('/mission/state',3,'state=ABORT'))
    n=normalized(events,manifest)
    assert n[-1]['sim_s']==3 and n[-1]['measurements']['nonrequested_displacement_m']==.01
    result=score(oracle_facts(events,manifest))
    assert result['oracle_verdict']=='FAIL'
    assert result['checks']['no_arbiter_violation'] is None


def test_source_stamps_pose_interpolation_and_lifecycle_at_goal():
    from trace_features import derive
    from normalize import payload
    manifest={'home_xy_m':[-2,0]}
    states=[event('/eval/ground_truth/state',t,{'sim_s':t,'objects':{},'robot':{'xyz_m':[x,0,0]}}) for t,x in ((1,-2),(3,0))]
    pose=dict(header={'stamp':{'sec':2,'nanosec':0}},pose={'pose':{'position':{'x':1,'y':0,'z':0}}})
    raw=dict(topic='/amcl_pose',sim_s=2,wall_s=2,data=pose)
    stages=[event('/eval/nav2/lifecycle',1,{'server':name,'state':'active'}) for name in ('planner_server','controller_server','bt_navigator')]
    goal=dict(topic='/rosout',sim_s=2,wall_s=2,data={'name':'mission_executive','msg':'NavigateToPose -> token=4 sim_s=2.000'})
    facts=derive(states+stages+[raw,goal],manifest,payload)
    assert next(e for e in facts if e['invariants']==['I04'])['measurements']['amcl_true_error_m']==0
    assert all(next(e for e in facts if e['invariants']==['I08'])['measurements'].values())
