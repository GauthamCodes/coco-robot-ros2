import copy
import json
from command_evidence import authority,selection_matches
from graph import violations
from normalize import payload,host_measurements
from trace_measurements import derive,grid_cost,tilt


def record(topic,t,data):
    return dict(topic=topic,sim_s=t,wall_s=t,data=data)


def diagnostic(sequence=1):
    return dict(sequence=sequence,stamp_ns=10**9,selected='nav',mode='nav',
                ages_wall_s=dict(nav=.01,teleop=None,rl=None,approach=None),source_timeout_wall_s=.3,
                source_arrival_sim_ns=900000000,source_arrival_monotonic_s=.9,
                source_twist=[.1,0,0,0,0,0],output_twist=[.1,0,0,0,0,0])


def episode():
    graph={'topics':{'/diff_drive_controller/cmd_vel':{'publishers':[{'name':'cmd_vel_arbiter','namespace':'/'}]}}}
    wire=dict(header={'stamp':{'sec':1,'nanosec':0}},twist={'linear':{'x':.1}})
    return [record('/eval/graph',0,graph),record('/diff_drive_controller/cmd_vel',1,wire),
            record('/diagnostics/arbiter_commands',1,diagnostic()),record('/eval/graph',2,graph)]


def check(events):return authority(events,payload,dict(wall_s=0),dict(wall_s=2),violations)


def test_authority_requires_wire_lineage_graph_and_contiguous_emissions():
    assert check(episode())['covered']
    assert not check([e for e in episode() if e['topic']!='/diagnostics/arbiter_commands'])['covered']
    bad=episode();bad[1]['data']['twist']['linear']['x']=.2
    assert not check(bad)['covered']
    lost=episode();lost.insert(3,record('/diagnostics/arbiter_commands',1.5,diagnostic(3)))
    assert not check(lost)['continuous'] and not check(lost)['covered']
    forged=episode();forged[0]['data']['topics']['/diff_drive_controller/cmd_vel']['publishers'][0]['namespace']='/foreign'
    assert check(forged)['violations'] and not check(forged)['covered']


def test_observed_selection_and_output_are_separate():
    d=diagnostic();assert selection_matches(d) is True
    d['output_twist'][0]=.2;assert selection_matches(d) is False
    d=diagnostic();d['ages_wall_s']['teleop']=.01
    assert selection_matches(d) is None  # ambiguous/raced decision; never PASS
    d=diagnostic();d['selected']=None;d['mode']='idle';d['output_twist']=[0.]*6
    assert selection_matches(d) is True


def test_raw_arbiter_first_input_latency_not_watchdog_age():
    d=diagnostic();second=dict(d,stamp_ns=1200000000)
    facts=derive([record('/diagnostics/arbiter_commands',1,d),record('/diagnostics/arbiter_commands',1.2,second)],{'requested_colour':'red'},payload)
    assert facts[0]['measurements']['arbiter_latency_sim_s']==.1
    assert 'arbiter_latency_sim_s' not in facts[1]['measurements']


def test_host_csv_stalled_sim_uses_wall_duration(tmp_path):
    path=tmp_path/'host_metrics.csv'
    path.write_text('sim_s,wall_elapsed_s,qualified,rtf\n4,10,True,0.5\n4,11,True,0\n4,12,False,0\n')
    facts=host_measurements(path)
    assert facts[-1]['measurements']['clock_stall_wall_s']==2
    assert facts[-2]['measurements']['host_qualified'] is False
    assert facts[-1]['sim_s']==4


def test_raw_grid_encoding_and_unknown_occupancy():
    data={'metadata':{'size_x':2,'size_y':1,'resolution':1,'origin':{'orientation':{'w':1}}},'data':[0,253]}
    assert grid_cost(data,.5,.5)==0 and grid_cost(data,1.5,.5)==253
    assert grid_cost(data,2.5,.5) is None
    occupancy={'info':{'width':2,'height':1,'resolution':1},'data':[50,-1]}
    assert grid_cost(occupancy,.5,.5) is None and grid_cost(occupancy,1.5,.5) is None


def test_tilt_lift_carry_and_unknown_progress():
    assert tilt([1,0,0,0])==0 and tilt([0,0,0,0]) is None
    def truth(t,z,attached):
        return record('/eval/ground_truth/state',t,{'sim_s':t,'robot':{'quaternion_wxyz':[1,0,0,0]},
                     'objects':{'target_red':{'xyz_m':[0,0,z],'attached':attached}}})
    events=[truth(0,.1,False),record('/mission/state',1,{'data':'state=VERIFY_GRASP elapsed=1 timeout=10'}),truth(1,.14,True),
            record('/mission/state',2,{'data':'state=RETURN_HOME'}),truth(2,.14,False)]
    facts=derive(events,{'requested_colour':'red'},payload)
    assert any(e['measurements'].get('lift_height_m',0)>.03 for e in facts)
    assert any(e['measurements'].get('target_attached_during_carry') is False for e in facts)
    stage=next(e for e in facts if e['invariants']==['I25'])
    assert 'stage_without_progress_sim_s' not in stage['measurements']


def test_accepted_pose_uses_stamped_truth_and_explicit_frame_provenance():
    packet={'sim_s':1,'robot_frame':'base_footprint','robot':{'xyz_m':[-2,0,0],'quaternion_wxyz':[1,0,0,0]},
            'objects':{'target_red':{'xyz_m':[-1,0,.1]}}}
    point={'header':{'stamp':{'sec':1,'nanosec':0},'frame_id':'base_footprint'},'point':{'x':1,'y':0,'z':.1}}
    events=[record('/eval/ground_truth/state',1,packet),record('/perception/target',2,point)]
    facts=derive(events,{'requested_colour':'red'},payload)
    metric=next(e for e in facts if e['invariants']==['I17'])
    assert metric['sim_s']==1 and metric['measurements']['accepted_target_true_error_m']==0
    packet.pop('robot_frame')
    assert not any(e['invariants']==['I17'] for e in derive(events,{'requested_colour':'red'},payload))


def test_unknown_raw_goal_cost_stays_unobserved():
    grid={'metadata':{'size_x':1,'size_y':1,'resolution':1.,
                      'update_time':{'sec':1},'origin':{}},'data':[255]}
    goal={'info':{'event_type':1},'request':[{'goal':{
        'goal':{'header':{'frame_id':'map'},'pose':{'position':{'x':.5,'y':.5}}}}}]}
    events=[record('/global_costmap/costmap_raw',1,grid),
            record('/compute_path_to_pose/_action/send_goal/_service_event',1,goal)]
    facts=derive(events,{'requested_colour':'red'},payload)
    assert not any('planner_goal_free' in e['measurements'] for e in facts)
