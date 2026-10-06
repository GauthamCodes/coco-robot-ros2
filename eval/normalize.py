"""Convert captured events to evaluator facts; never infer missing safety proof."""
import json
import math
from oracle import score,REST_WINDOW_SIM_S
from graph import violations


def payload(event):
    value=event.get('data',{})
    if isinstance(value,dict) and isinstance(value.get('data'),str):
        raw=value['data']
        try:return json.loads(raw)
        except ValueError:return raw
    return value


def state_name(value):
    if not isinstance(value,str):return None
    fields=dict(s.split('=',1) for s in value.split() if '=' in s)
    return fields.get('state')


def normalized(events,manifest):
    stage='UNKNOWN';output=[];initial={};start=None
    for event in events:
        data=payload(event);topic=event['topic'];now=event['sim_s']
        if topic=='/mission/state':
            stage=state_name(data) or stage
            if stage=='LOCALIZE' and start is None:start=now
        measurements={};ids=[]
        if topic=='/eval/ground_truth/state' and isinstance(data,dict):
            now=data['sim_s'];objects=data.get('objects',{})
            positions=[v.get('xyz_m',[]) for v in objects.values()]
            if data.get('robot') is not None:positions.append(data['robot'].get('xyz_m',[]))
            measurements['physics_poses_finite']=all(len(p)==3 and all(math.isfinite(v) for v in p) for p in positions)
            ids.append('I24')
            if start is not None and now>=start:
                displaced=[]
                for name,value in objects.items():
                    if name=='target_'+manifest['requested_colour']:continue
                    initial.setdefault(name,value['xyz_m']);displaced.append(math.dist(initial[name],value['xyz_m']))
                if displaced:measurements['nonrequested_displacement_m']=max(displaced);ids.append('I19')
        if topic=='/eval/graph' and stage not in ('UNKNOWN','IDLE'):
            measurements['sole_arbiter_publisher']=not any(v['invariant']=='I06' for v in violations(data));ids.append('I06')
        if topic=='/rosout' and isinstance(data,dict):
            text=data.get('msg','')
            if data.get('name')=='planner_server' and 'Start occupied' in text:
                measurements['planner_start_occupied']=True;ids.append('I10')
            if 'solver' in text.lower() and data.get('level',0)>=40:
                measurements['solver_error']=True;ids.append('I24')
        if measurements:
            output.append(dict(sim_s=now,mission_stage=stage,measurements=measurements,
                               invariants=ids,source_topic=topic,source_wall_s=event.get('wall_s')))
    from trace_features import derive
    return output+derive(events,manifest,payload)


def oracle_facts(events,manifest):
    mission=[(e,payload(e)) for e in events if e['topic']=='/mission/state']
    start=next((e for e,d in mission if state_name(d)=='LOCALIZE'),None)
    terminal=next((e for e,d in mission if state_name(d) in ('COMPLETE','ABORT')),None)
    target='target_'+manifest['requested_colour']
    names=[t['model'] for t in manifest['targets'] if t['model']!=target]
    target_def=next(t for t in manifest['targets'] if t['model']==target)
    states=[payload(e) for e in events if e['topic']=='/eval/ground_truth/state']
    states=[s for s in states if isinstance(s,dict) and start is not None and terminal is not None
            and start['sim_s']<=s['sim_s']<=terminal['sim_s']]
    initial={};maxima={};valid=[]
    for s in states:
        objects=s.get('objects',{})
        if not all(n in objects for n in names+[target]) or s.get('robot') is None:continue
        for n in names:
            initial.setdefault(n,objects[n]['xyz_m'])
            maxima[n]=max(maxima.get(n,0),math.dist(initial[n],objects[n]['xyz_m']))
        valid.append(s)
    latest=valid[-1] if valid else None
    rest=[]
    if latest:
        lower=latest['sim_s']-REST_WINDOW_SIM_S
        predecessor=next((s for s in reversed(valid) if s['sim_s']<=lower),None)
        if predecessor:
            rest=[dict(sim_s=s['sim_s'],xyz_m=s['objects'][target]['xyz_m'],
                       quaternion_wxyz=s['objects'][target]['quaternion_wxyz'],attached=s['objects'][target].get('attached'))
                  for s in valid if s['sim_s']>=predecessor['sim_s']]
    covered=bool(valid and terminal and terminal['sim_s']-latest['sim_s']<=2)
    disturbance=bool(covered and start and valid[0]['sim_s']-start['sim_s']<=2
                     and all(b['sim_s']-a['sim_s']<=2 for a,b in zip(valid,valid[1:])) and len(valid)==len(states))
    authority_violations=[]
    for e in events:
        if e['topic']=='/eval/graph' and start and terminal and start['wall_s']<=e['wall_s']<=terminal['wall_s']:
            authority_violations.extend(v for v in violations(payload(e)) if v['invariant']=='I06')
    return dict(home_xy_m=manifest['home_xy_m'],target_height_m=target_def['height'],
                target_final_xyz_m=latest['objects'][target]['xyz_m'] if latest else None,
                robot_final_xyz_m=latest['robot']['xyz_m'] if latest else None,
                target_rest_samples=rest,nonrequested_models=names,nonrequested_max_displacement_m=maxima,
                terminal_truth_covered=covered,disturbance_truth_covered=disturbance,
                arbiter_violations=authority_violations,
                arbiter_evidence_covered=False,  # calibration/correlated command evidence not yet derived
                episode_wall_s=terminal['wall_s']-start['wall_s'] if terminal and start else None,
                episode_finished=terminal is not None,
                mission_verdict=state_name(payload(terminal)) if terminal else 'UNOBSERVED')
