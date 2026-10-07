"""Evaluator-only frame arithmetic; no transform or pose is sent to autonomy."""
import math


def rotate(q,p):
    if not isinstance(q,list) or len(q)!=4 or len(p)!=3:return None
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in q+p):return None
    norm=math.sqrt(sum(v*v for v in q))
    if not norm:return None
    w,x,y,z=[v/norm for v in q]
    return [(1-2*(y*y+z*z))*p[0]+2*(x*y-w*z)*p[1]+2*(x*z+w*y)*p[2],
            2*(x*y+w*z)*p[0]+(1-2*(x*x+z*z))*p[1]+2*(y*z-w*x)*p[2],
            2*(x*z-w*y)*p[0]+2*(y*z+w*x)*p[1]+(1-2*(x*x+y*y))*p[2]]


def world_point(frame,point,packet,static):
    if frame=='world':return point
    if packet.get('robot_frame')!='base_footprint' or not packet.get('robot'):return None
    visited=set()
    while frame!='base_footprint':
        if frame in visited or frame not in static:return None
        visited.add(frame);tf=static[frame];transform=tf['transform'];q=transform['rotation'];p=transform['translation']
        point=rotate([q[k] for k in ('w','x','y','z')],point)
        if point is None:return None
        point=[v+p[k] for v,k in zip(point,('x','y','z'))];frame=tf['header']['frame_id']
    robot=packet['robot'];point=rotate(robot.get('quaternion_wxyz'),point)
    return [v+b for v,b in zip(point,robot['xyz_m'])] if point is not None else None
