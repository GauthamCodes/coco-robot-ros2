"""Additional passive raw-trace measurements. Missing gates remain unknown."""
import math
from command_evidence import selection_matches
from trace_features import at_time,source_time,ros_xyz
from spatial import world_point


def fields(value):
    return dict(s.split('=',1) for s in value.split() if '=' in s) if isinstance(value,str) else {}


def number(value):
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (TypeError,ValueError):return None


def tilt(q):
    if not isinstance(q,list) or len(q)!=4 or not all(number(v) is not None for v in q):return None
    norm=math.sqrt(sum(v*v for v in q))
    if not norm:return None
    w,x,y,z=[v/norm for v in q]
    return max(abs(math.atan2(2*(w*x+y*z),1-2*(x*x+y*y))),abs(math.asin(max(-1,min(1,2*(w*y-z*x))))))


def grid_cost(data,x,y):
    """Decode raw Nav2 or OccupancyGrid; respect rotated grid origins."""
    raw='metadata' in data;meta=data.get('metadata') if raw else data.get('info')
    if not isinstance(meta,dict):return None
    width=meta.get('size_x') if raw else meta.get('width');height=meta.get('size_y') if raw else meta.get('height')
    resolution=meta.get('resolution');origin=meta.get('origin',{});position=origin.get('position',{})
    q=origin.get('orientation',{});yaw=math.atan2(2*(q.get('w',1)*q.get('z',0)+q.get('x',0)*q.get('y',0)),1-2*(q.get('y',0)**2+q.get('z',0)**2))
    if not width or not height or not resolution or resolution<=0:return None
    dx=x-position.get('x',0);dy=y-position.get('y',0)
    ix=math.floor((math.cos(yaw)*dx+math.sin(yaw)*dy)/resolution)
    iy=math.floor((-math.sin(yaw)*dx+math.cos(yaw)*dy)/resolution)
    if not (0<=ix<width and 0<=iy<height):return None
    values=data.get('data',[]);index=iy*width+ix
    if index>=len(values):return None
    value=values[index]
    # OccupancyGrid collapses inflated raw costs: only free/lethal cells
    # establish a conclusion. Intermediate/unknown values remain ambiguous.
    return value if raw else 0 if value==0 else 254 if value==100 else None


def derive(events,manifest,decode):
    result=[];stage='UNKNOWN';target='target_'+manifest['requested_colour'];static={}
    states=sorted([decode(e) for e in events if e['topic']=='/eval/ground_truth/state'],key=lambda s:s['sim_s'])
    initial_z=None;previous_attached=None;carrying=False;last_source={};grid=None;pose=None
    def emit(event,measurements,ids,sim=None):
        result.append(dict(sim_s=event['sim_s'] if sim is None else sim,mission_stage=stage,
                           measurements=measurements,invariants=ids,source_topic=event['topic'],source_wall_s=event.get('wall_s')))
    for event in events:
        topic=event['topic'];data=decode(event);now=event['sim_s']
        if topic=='/tf_static':
            for tf in data.get('transforms',[]):static[tf['child_frame_id']]=tf
        if topic in ('/perception/target','/perception/target_pose'):
            stamp=source_time(data,now);packet=at_time(states,stamp)
            if packet and target in packet['objects']:
                detections=data.get('detections',[]) if topic.endswith('target_pose') else [{'header':data.get('header',{}),'point':data.get('point')}]
                for detection in detections:
                    position=detection.get('point') or detection.get('bbox',{}).get('center',{}).get('position')
                    if not position:continue
                    frame=detection.get('header',data.get('header',{})).get('frame_id')
                    point=world_point(frame,ros_xyz({'position':position}),packet,static)
                    if point is not None:
                        emit(event,{'accepted_target_true_error_m':math.dist(point,packet['objects'][target]['xyz_m'])},['I17'],stamp)
                    # Detection.id and class_id come from the requested colour
                    # table. They do not prove the physical object's identity.
        if topic=='/mission/state':
            status=fields(data);stage=status.get('state',stage)
            elapsed=number(status.get('elapsed'));budget=number(status.get('timeout'))
            if elapsed is not None and budget is not None:
                # Elapsed time does not prove absence of progress. Retain the
                # actual published budget but keep I25 unknown until a real
                # progress witness is available.
                emit(event,{'stage_elapsed_sim_s':elapsed,'stage_budget_sim_s':budget},['I25'])
        if topic=='/diagnostics/arbiter_commands' and isinstance(data,dict):
            stamp=number(data.get('stamp_ns'));arrival=number(data.get('source_arrival_sim_ns'))
            m={'arbiter_selected_matches':selection_matches(data)}
            # Latency is first emission for this observed input, not its age
            # when watchdog repeatedly forwards a held command.
            key=(data.get('selected'),data.get('source_arrival_monotonic_s'))
            if key not in last_source and stamp is not None and arrival is not None:
                if stamp>=arrival:m['arbiter_latency_sim_s']=(stamp-arrival)/1e9
                last_source[key]=True
            elif data.get('selected') is None:m['arbiter_latency_sim_s']=0.
            emit(event,m,['I06'],stamp/1e9 if stamp is not None else now)
        if topic in ('/global_costmap/costmap_raw','/global_costmap/costmap'):
            # Prefer lossless raw costs whenever available.
            if grid is None or 'metadata' in data or 'metadata' not in grid:grid=data
        if topic=='/amcl_pose':pose=data.get('pose',{}).get('pose',{}).get('position')
        if topic.endswith('/compute_path_to_pose/_action/send_goal/_service_event') or topic=='/compute_path_to_pose/_action/send_goal/_service_event':
            # Only server-received requests establish request-time cost tests.
            if data.get('info',{}).get('event_type')!=1:continue
            for request in data.get('request',[]):
                goal=request.get('goal',{});gpose=goal.get('goal',{})
                if grid is None or gpose.get('header',{}).get('frame_id')!='map':continue
                stamp=grid.get('header',{}).get('stamp',{}) if 'metadata' not in grid else grid.get('metadata',{}).get('update_time',{})
                grid_time=stamp.get('sec',0)+stamp.get('nanosec',0)/1e9
                emit(event,{'costmap_age_sim_s':abs(now-grid_time)},['I12'])
                # A throttled older grid is not the server's request-time
                # cell cost. It may be used for context, never a false breach.
                if grid_time!=now:continue
                point=gpose.get('pose',{}).get('position',{});cost=grid_cost(grid,point.get('x',0),point.get('y',0))
                if cost is not None:emit(event,{'planner_goal_free':cost==0},['I11'])
                start=goal.get('start',{}).get('pose',{}).get('position') if goal.get('use_start') else pose
                if start:
                    cost=grid_cost(grid,start['x'],start['y'])
                    if cost is not None and cost!=255:emit(event,{'planner_start_occupied':cost>=253},['I10'])
        if topic in ('/arm_controller/follow_joint_trajectory/_action/feedback','/gripper_controller/follow_joint_trajectory/_action/feedback'):
            feedback=data.get('feedback',{})
            # These control_msgs interfaces really contain desired/actual
            # positions; MoveIt ExecuteTrajectory has state-only feedback.
            if 'actual' in feedback and 'desired' in feedback:
                actual=feedback['actual'].get('positions',[]);desired=feedback['desired'].get('positions',[])
                if actual and len(actual)==len(desired):emit(event,{'joint_tracking_error_rad':max(abs(a-b) for a,b in zip(actual,desired))},['I20'])
        if topic=='/eval/ground_truth/state' and isinstance(data,dict):
            sim=data['sim_s'];robot=data.get('robot');objects=data.get('objects',{});obj=objects.get(target)
            if robot:
                angle=tilt(robot.get('quaternion_wxyz'))
                if angle is not None:emit(event,{'max_roll_pitch_rad':angle},['I24'],sim)
            if obj:
                attached=obj.get('attached');z=obj['xyz_m'][2]
                if initial_z is None:initial_z=z
                if stage=='VERIFY_GRASP':
                    emit(event,{'lift_height_m':z-initial_z},['I21'],sim)
                    if attached is True and z-initial_z>=.03:carrying=True
                if carrying and stage in ('RETREAT','DESCEND','BYPASS_RAMP','RETURN_HOME'):
                    emit(event,{'target_attached_during_carry':attached},['I22'],sim)
                if previous_attached is True and attached is False and stage in ('PLACE','VERIFY_PLACEMENT'):
                    # Phase strings are intention, not finger measurements.
                    emit(event,{'placed_detached':True},['I23'],sim)
                previous_attached=attached
    return result
