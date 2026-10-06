from graph import violations
from truth import gazebo_packet


def test_truth_every_object_dimension_and_world_stamp():
    packet=gazebo_packet({'header':{'stamp':{'sec':'4','nsec':'500000000'}},'pose':[
        {'name':'coco','position':{'x':-2},'orientation':{'w':1}},
        {'name':'target_red','position':{'z':.079},'orientation':{'w':1}}]},
        {'target_red':[.02,.02,.158]},{'target_red':False})
    assert packet['sim_s']==4.5
    assert packet['objects']['target_red']['dimensions_m']==[.02,.02,.158]
    assert packet['robot']['xyz_m']==[-2,0,0]


def test_graph_namespace_boundary_and_final_publisher():
    g={'topics':{'/eval/ground_truth/state':{'subscriptions':[{'name':'recorder','namespace':'/eval'}]},
                 '/diff_drive_controller/cmd_vel':{'publishers':[{'name':'cmd_vel_arbiter','namespace':'/'}]}}}
    assert violations(g)==[]
    g['topics']['/eval/ground_truth/state']['subscriptions'].append({'name':'rogue','namespace':'/eval_disguised'})
    assert violations(g)[0]['invariant']=='GROUND_TRUTH_ISOLATION'
    g['topics']['/diff_drive_controller/cmd_vel']['publishers'].append({'name':'bypass','namespace':'/'})
    assert violations(g)[1]['invariant']=='I06'
