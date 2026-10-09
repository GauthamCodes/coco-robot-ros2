"""Offline exact-time gripper reconstruction from recorded TF and world base truth.

No latest-TF substitution, interpolation, or stale transforms. Missing exact-time
joints keep the result unknown. Ground truth never leaves this evaluator.
"""
from copy import deepcopy
from normalize import payload
from oracle import xyz, quaternion, finite
from spatial import rotate


def multiply(a,b):
    w,x,y,z=a;v,i,j,k=b
    return [w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v]


def enrich(events, gripper_frame='m_link3'):
    static={};dynamic={}
    for e in events:
        if e.get('topic') not in ('/tf','/tf_static'):continue
        d=payload(e)
        if not isinstance(d,dict):continue
        for tf in d.get('transforms',[]):
            try:
                stamp=tf['header']['stamp'];ns=stamp['sec']*10**9+stamp['nanosec']
                key=(tf['child_frame_id'],ns) if e['topic']=='/tf' else tf['child_frame_id']
                table=dynamic if e['topic']=='/tf' else static
                if key in table and table[key]!=tf:table[key]=None
                else:table[key]=tf
            except (KeyError,TypeError):continue
    output=[]
    for e in events:
        if e.get('topic')!='/eval/ground_truth/state':output.append(e);continue
        d=deepcopy(payload(e));grip=None
        if not isinstance(d,dict):output.append(e);continue
        robot=d.get('robot')
        if finite(d.get('sim_s')) and d.get('gripper') is None and isinstance(robot,dict) and d.get('frame')=='world' and d.get('robot_frame')=='base_footprint' and xyz(robot.get('xyz_m')) and quaternion(robot.get('quaternion_wxyz')):
            ns=round(d['sim_s']*1e9);frame=gripper_frame;point=[0.,0.,0.];q=[1.,0.,0.,0.];seen=set();refs=[]
            while frame!='base_footprint' and frame not in seen:
                seen.add(frame);tf=dynamic.get((frame,ns),static.get(frame))
                if not tf:break
                try:
                    t=tf['transform'];p=[t['translation'][k] for k in ('x','y','z')];r=[t['rotation'][k] for k in ('w','x','y','z')]
                    if not xyz(p) or not quaternion(r):break
                    point=[a+b for a,b in zip(rotate(r,point),p)];q=multiply(r,q)
                    refs.append(dict(child=frame,header=tf['header']));frame=tf['header']['frame_id']
                except (KeyError,TypeError):break
            if frame=='base_footprint':
                grip=dict(xyz_m=[a+b for a,b in zip(rotate(robot['quaternion_wxyz'],point),robot['xyz_m'])],
                          quaternion_wxyz=multiply(robot['quaternion_wxyz'],q),frame='world',source_sim_s=d['sim_s'],
                          provenance='exact_recorded_tf_and_world_base',tf_chain=refs,tf_age_sim_s=0.)
            if grip:d['gripper']=grip
        output.append(dict(e,data=d))
    return output
