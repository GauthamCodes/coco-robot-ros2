from manipulation_tf import enrich

def tf(child,parent,t,x):
    return dict(child_frame_id=child,header=dict(frame_id=parent,stamp=dict(sec=t,nanosec=0)),
                transform=dict(translation=dict(x=x,y=0,z=0),rotation=dict(w=1,x=0,y=0,z=0)))

def events(t=2):
    return [dict(topic='/tf',data=dict(transforms=[tf('m_link3','base_footprint',t,.2)])),
            dict(topic='/eval/ground_truth/state',sim_s=2,data=dict(sim_s=2,frame='world',robot_frame='base_footprint',
            robot=dict(xyz_m=[1,0,0],quaternion_wxyz=[1,0,0,0]),objects={}))]

def test_exact_source_tf_world_composition():
    assert enrich(events())[-1]['data']['gripper']['xyz_m']==[1.2,0,0]

def test_stale_tf_not_latest_substitution():
    assert 'gripper' not in enrich(events(1))[-1]['data']

def test_conflicting_tf_rejected():
    e=events();e[0]['data']['transforms'].append(tf('m_link3','base_footprint',2,.3))
    assert 'gripper' not in enrich(e)[-1]['data']
