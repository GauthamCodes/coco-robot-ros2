"""Correlate observed arbiter emissions with wheel messages, never infer lineage."""
from collections import Counter
import math


def twist_values(data):
    twist=data.get('twist',{})
    return [twist.get(vector,{}).get(axis,0.) for vector in ('linear','angular') for axis in ('x','y','z')]


def finite_twist(value):
    return isinstance(value,list) and len(value)==6 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in value)


def selection_matches(data):
    ages=data.get('ages_wall_s',{});limit=data.get('source_timeout_wall_s')
    if not all(k in ages for k in ('teleop','nav','rl','approach')) or data.get('mode') not in ('idle','teleop','nav','rl','approach'):return None
    if not isinstance(limit,(int,float)) or not math.isfinite(limit):return None
    def fresh(name):
        age=ages.get(name)
        return isinstance(age,(int,float)) and math.isfinite(age) and 0<=age<=limit
    expected='teleop' if fresh('teleop') else data.get('mode') if data.get('mode') in ('nav','rl','approach') and fresh(data['mode']) else None
    output=data.get('output_twist');source=data.get('source_twist')
    if not finite_twist(output):return None
    # The selection was made before the publish. A source that crosses the
    # watchdog timeout while publishing is ambiguous, not a proven bad decision.
    selected=data.get('selected')
    if selected!=expected:return None
    if selected is None:return output==[0.]*6
    return source==output if finite_twist(source) else None


def authority(events,decode,start,end,graph_check):
    """Require contiguous emission diagnostics, exact wire matches, graph coverage."""
    if start is None or end is None:return {'covered':False,'violations':[],'reason':'episode boundaries missing'}
    begin,finish=start['wall_s'],end['wall_s']
    graphs=[e for e in events if e['topic']=='/eval/graph' and begin<=e['wall_s']<=finish]
    errors=[v for e in graphs for v in graph_check(decode(e)) if v['invariant']=='I06']
    graph_covered=bool(graphs and graphs[0]['wall_s']-begin<=2 and finish-graphs[-1]['wall_s']<=2
                       and all(b['wall_s']-a['wall_s']<=2 for a,b in zip(graphs,graphs[1:])))
    diagnostics=[decode(e) for e in events if e['topic']=='/diagnostics/arbiter_commands']
    wheels=[e for e in events if e['topic']=='/diff_drive_controller/cmd_vel' and begin<=e['wall_s']<=finish]
    available=Counter()
    for d in diagnostics:
        if finite_twist(d.get('output_twist')):available[(d['stamp_ns'],tuple(d['output_twist']))]+=1
    matched=True
    for e in wheels:
        data=decode(e);stamp=data.get('header',{}).get('stamp',{})
        key=(stamp.get('sec',0)*10**9+stamp.get('nanosec',0),tuple(twist_values(data)))
        if available[key]<=0:matched=False
        else:available[key]-=1
    selected=[decode(e) for e in events if e['topic']=='/diagnostics/arbiter_commands' and begin<=e['wall_s']<=finish]
    sequence=[d.get('sequence') for d in selected]
    continuous=bool(sequence and all(isinstance(v,int) for v in sequence) and all(b==a+1 for a,b in zip(sequence,sequence[1:])))
    decisions=[selection_matches(d) for d in selected]
    for d,match in zip(selected,decisions):
        if match is False:errors.append({'invariant':'I06','sequence':d['sequence'],'reason':'selected source/output mismatch'})
    covered=bool(not errors and graph_covered and wheels and len(wheels)==len(selected) and continuous and matched and decisions and all(v is True for v in decisions))
    return {'covered':covered,'violations':errors,'graph_covered':graph_covered,
            'wheel_messages':len(wheels),'emission_records':len(selected),'continuous':continuous,
            'wire_matched':matched,'reason':None if covered else 'incomplete/ambiguous command or graph evidence'}
