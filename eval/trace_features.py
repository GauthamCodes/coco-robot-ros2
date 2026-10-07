"""Supported raw ROS trace derivations; unavailable observations remain absent."""
import bisect
import math
import re


def source_time(data,fallback):
    stamp=data.get('header',{}).get('stamp',{})
    return stamp.get('sec',0)+stamp.get('nanosec',0)/1e9 if stamp else fallback


def ros_xyz(pose):
    position=pose.get('position',{})
    return [position.get(k,0) for k in ('x','y','z')]


def at_time(states,sim):
    """Interpolate translation only between bracketing ground-truth snapshots."""
    times=[s['sim_s'] for s in states];i=bisect.bisect_left(times,sim)
    if i<len(states) and times[i]==sim:return states[i]
    if i==0 or i==len(states):return None
    a,b=states[i-1:i+1];fraction=(sim-a['sim_s'])/(b['sim_s']-a['sim_s'])
    def xyz(x,y):return [v+fraction*(w-v) for v,w in zip(x,y)]
    objects={name:dict(value,xyz_m=xyz(value['xyz_m'],b['objects'][name]['xyz_m'])) for name,value in a['objects'].items() if name in b['objects']}
    robot=None
    if a.get('robot') and b.get('robot'):
        robot=dict(a['robot'],xyz_m=xyz(a['robot']['xyz_m'],b['robot']['xyz_m']))
        if a['robot'].get('quaternion_wxyz')!=b['robot'].get('quaternion_wxyz'):robot.pop('quaternion_wxyz',None)
    # Rotation interpolation is not assumed. Only translation measurements use this packet.
    return dict(sim_s=sim,objects=objects,robot=robot,robot_frame=a.get('robot_frame'),interpolated_translation=True)


def derive(events,manifest,decode):
    states=sorted([decode(e) for e in events if e['topic']=='/eval/ground_truth/state'],key=lambda s:s['sim_s'])
    stages='UNKNOWN';result=[];lifecycle={};sent={};received=set();acks={};odom0=None;truth0=None
    previous_clock=None;last_advance_wall=None
    def append(event,measurements,ids):
        result.append(dict(sim_s=event['sim_s'],mission_stage=stages,measurements=measurements,invariants=ids,
                           source_topic=event['topic'],source_wall_s=event.get('wall_s')))
    for event in events:
        topic=event['topic'];data=decode(event);now=event['sim_s'];wall=event.get('wall_s')
        if topic=='/mission/state' and isinstance(data,str):
            match=re.search(r'(?:^| )state=(\w+)',data)
            if match:stages=match[1]
        if topic=='/clock':
            clock=data.get('clock',{});value=clock.get('sec',0)+clock.get('nanosec',0)/1e9
            if previous_clock is None or value>previous_clock:last_advance_wall=wall
            append(event,dict(clock_monotonic=previous_clock is None or value>=previous_clock,
                              clock_stall_wall_s=wall-last_advance_wall if wall is not None and last_advance_wall is not None else None),['I02'])
            previous_clock=value
        if topic=='/eval/tf' and isinstance(data,dict):
            transforms=data['transforms'];present=all(v.get('available') for v in transforms.values())
            ages=[abs(now-v['stamp_s']) for v in transforms.values() if v.get('available')]
            append(event,dict(tf_chains_present=present,tf_age_sim_s=max(ages) if present and ages else None),['I03'])
        if topic=='/amcl_pose':
            packet=at_time(states,source_time(data,now))
            if packet and packet.get('robot'):
                actual=packet['robot']['xyz_m'];observed=ros_xyz(data['pose']['pose'])
                # Existing fixed map prior: mission WORLD_TO_MAP_X=-SPAWN_XY[0].
                actual_map=[actual[0]-manifest['home_xy_m'][0],actual[1]-manifest['home_xy_m'][1]]
                append(event,dict(amcl_true_error_m=math.dist(observed[:2],actual_map)),['I04'])
        if topic=='/diff_drive_controller/odom':
            packet=at_time(states,source_time(data,now))
            if packet and packet.get('robot'):
                observed=ros_xyz(data['pose']['pose']);truth=packet['robot']['xyz_m']
                if odom0 is None:odom0=observed;truth0=truth
                estimated=[a-b for a,b in zip(observed,odom0)];actual=[a-b for a,b in zip(truth,truth0)]
                append(event,dict(odom_true_displacement_error_m=math.dist(estimated[:2],actual[:2])),['I05'])
        if topic=='/eval/nav2/lifecycle' and isinstance(data,dict):lifecycle[data['server']]=data.get('state')
        if topic.endswith('/transition_event'):
            lifecycle[topic.split('/')[1]]=data.get('goal_state',{}).get('label')
        if topic=='/perception/candidates' and isinstance(data,dict):
            stamp=data['stamp_ns']/1e9;depth_stamp=data.get('depth_stamp_ns')
            append(event,dict(rgb_age_sim_s=abs(now-stamp),
                              depth_age_sim_s=abs(now-depth_stamp/1e9) if depth_stamp is not None else None,
                              rgb_depth_skew_sim_s=abs(stamp-depth_stamp/1e9) if depth_stamp is not None else None),['I15'])
            expected=data.get('expected_width_px')
            if expected and data.get('record_kind')!='frame':
                # This expected width uses the candidate's own depth and the
                # configured size prior, not an independent truth projection.
                append(event,dict(self_model_projected_extent_error_fraction=abs(data['width_px']/expected-1)),[])
        if topic.endswith('/_action/status'):
            for entry in data.get('status_list',[]):
                uuid=bytes(entry['goal_info']['goal_id']['uuid']).hex()
                if entry['status'] in (1,2,4,5,6):received.add(uuid)
                if '/execute_trajectory/' in topic and entry['status'] in (4,5,6):
                    append(event,dict(moveit_execution_succeeded=entry['status']==4),['I20'])
                if uuid in acks:
                    ack=acks[uuid];append(ack,dict(server_goal_receipt=True,goal_ack_sim_s=ack['ack_latency_sim_s']),['I09'])
                    del acks[uuid]
        if topic=='/rosout' and isinstance(data,dict) and data.get('name')=='mission_executive':
            text=data.get('msg','');token=re.search(r'token=([^ ]+)',text);stamp=re.search(r'sim_s=([0-9.]+)',text)
            sim=float(stamp[1]) if stamp else now
            if 'NavigateToPose ->' in text and token:
                sent[token[1]]=sim
                append(dict(event,sim_s=sim),dict(planner_active=None if 'planner_server' not in lifecycle else lifecycle['planner_server']=='active',
                           controller_active=None if 'controller_server' not in lifecycle else lifecycle['controller_server']=='active',
                           navigator_active=None if 'bt_navigator' not in lifecycle else lifecycle['bt_navigator']=='active'),['I08'])
            if 'NavigateToPose acknowledgement' in text and token and token[1] in sent:
                uuid=re.search(r'uuid=([0-9a-f]{32})',text)
                if uuid:
                    ack=dict(event,sim_s=sim,ack_latency_sim_s=sim-sent[token[1]])
                    if uuid[1] in received:append(ack,dict(server_goal_receipt=True,goal_ack_sim_s=ack['ack_latency_sim_s']),['I09'])
                    else:acks[uuid[1]]=ack
    return result
