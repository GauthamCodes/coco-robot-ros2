"""Shared sensor-observation contract; no simulator, target-height prior or ROS."""
import math
HEIGHT_SCHEMA='coco.object_height.v1'
HEIGHT_MAX_AGE_S=.2  # existing image-time TF age convention; no widening
HEIGHT_MAX_UNCERTAINTY_M=.02/4  # <=1/4 existing release tolerance sensing budget

def validated_height(observation,*,now_ns,colour):
    """Independent consumer validation: malformed/unknown never becomes height."""
    if not isinstance(observation,dict):return None
    if observation.get('schema')!=HEIGHT_SCHEMA or observation.get('valid') is not True or observation.get('reason')!='VALID':return None
    if observation.get('frame_id')!='base_footprint' or observation.get('source_frame')!='camera_optical_frame' or observation.get('units')!='m':return None
    if observation.get('colour')!=colour or observation.get('transform_valid') is not True:return None
    if not all(isinstance(observation.get(key),str) and observation[key] for key in ('track_id','reference_id')):return None
    stamp=observation.get('stamp_ns');depth_stamp=observation.get('depth_stamp_ns')
    if not isinstance(stamp,int) or stamp!=depth_stamp or not 0<stamp<=now_ns:return None
    if (now_ns-stamp)/1e9>HEIGHT_MAX_AGE_S:return None
    h=observation.get('center_height_above_support_m');unc=observation.get('uncertainty_m')
    center=observation.get('center_m');support=observation.get('support_height_m')
    def number(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
    if not number(h) or not number(unc) or not 0<=unc<=HEIGHT_MAX_UNCERTAINTY_M or h<=0:return None
    if not number(support) or not isinstance(center,list) or len(center)!=3 or not all(number(v) for v in center):return None
    if not math.isclose(center[2]-support,h,abs_tol=1e-9):return None
    count=observation.get('depth_sample_count');inliers=observation.get('inlier_count')
    fraction=observation.get('valid_fraction');radius=observation.get('measured_radius_m');extent=observation.get('measured_axis_extent_m')
    if not isinstance(count,int) or not isinstance(inliers,int) or min(count,inliers)<6:return None
    if not number(fraction) or not .5<fraction<=1:return None
    if not number(radius) or not number(extent) or not 0<2*radius<extent:return None
    return float(h)
