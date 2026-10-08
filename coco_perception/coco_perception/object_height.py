"""Measured cylinder centre/support geometry. No configured object dimensions.

Valid only for complete, unoccluded cylinder views with observed local support.
Axis/radius/end positions are measured; ambiguous/partial geometry is unavailable.
"""
import math
import numpy as np

from coco_config.object_observation import (HEIGHT_SCHEMA as SCHEMA,
    HEIGHT_MAX_AGE_S as MAX_AGE_S, HEIGHT_MAX_UNCERTAINTY_M as MAX_UNCERTAINTY_M,
    validated_height as guarded_height)
MIN_POINTS=6  # existing depth estimator minimum; >3 parameters for plane/circle
MAX_POINTS=2048  # bounded estimator cost, not geometry acceptance threshold


def invalid(reason, stamp_ns=0, depth_stamp_ns=0, colour='', **fields):
    return dict(schema=SCHEMA,stamp_ns=int(stamp_ns),depth_stamp_ns=int(depth_stamp_ns),
        source_frame='',frame_id='base_footprint',colour=colour,track_id='',reference_id='',
        valid=False,reason=reason,center_m=None,support_height_m=None,
        center_height_above_support_m=None,uncertainty_m=None,units='m',
        transform_valid=False,observation_age_s=None,**fields)


def cloud(depth,k,transform,mask):
    v,u=np.nonzero(mask)
    d=depth[v,u]
    points=np.column_stack(((u-k[0,2])*d/k[0,0],(v-k[1,2])*d/k[1,1],d))
    return points@transform[:3,:3].T+transform[:3,3]


def estimate_object_height(mask,depth,k,transform,*,stamp_ns,depth_stamp_ns,now_ns,
                           colour,source_frame,depth_frame,track_id,reference_id):
    args=dict(stamp_ns=stamp_ns,depth_stamp_ns=depth_stamp_ns,colour=colour)
    def reject(reason):return invalid(reason,**args)
    if source_frame != depth_frame or not source_frame or source_frame != 'camera_optical_frame':return reject('FRAME_MISMATCH')
    age=(now_ns-stamp_ns)/1e9
    if not 0<=age<=MAX_AGE_S:return reject('STALE_OR_FUTURE')
    # Independent height proof requires simultaneous RGB/depth, not motion
    # interpolation from an unmeasured target velocity.
    if stamp_ns!=depth_stamp_ns:return reject('UNSYNCHRONIZED')
    if not track_id or not reference_id:return reject('ASSOCIATION_FAILURE')
    depth=np.asarray(depth,float);mask=np.asarray(mask,bool);k=np.asarray(k,float)
    if depth.shape!=mask.shape or depth.ndim!=2:return reject('IMAGE_SHAPE')
    if transform is None:return reject('TF_UNAVAILABLE')
    transform=np.asarray(transform,float)
    if transform.shape!=(4,4) or not np.isfinite(transform).all() or not np.allclose(transform[3],[0,0,0,1]):return reject('TF_INVALID')
    if not np.allclose(transform[:3,:3].T@transform[:3,:3],np.eye(3),atol=1e-6) or np.linalg.det(transform[:3,:3])<0:return reject('TF_INVALID')
    if k.shape!=(3,3) or not np.isfinite(k).all() or min(k[0,0],k[1,1])<=0:return reject('INTRINSICS_INVALID')
    v,u=np.nonzero(mask)
    if len(v)<MIN_POINTS:return reject('NO_TARGET_OR_SPARSE')
    if min(v)==0 or max(v)==depth.shape[0]-1 or min(u)==0 or max(u)==depth.shape[1]-1:return reject('TRUNCATED_MASK')
    values=depth[mask];finite=np.isfinite(values)
    if np.any(finite & (values<.15)):return reject('NEAR_PLANE_OR_MIN_RANGE')
    good=finite&(values>=.15)&(values<=2.)  # unchanged acquisition range
    if good.sum()<MIN_POINTS:return reject('INVALID_DEPTH')
    if good.mean()<=.5:return reject('SPARSE_DEPTH')  # median breakdown point
    med=float(np.median(values[good]));mad=float(np.median(np.abs(values[good]-med)))
    pixel=med/min(k[0,0],k[1,1])
    # Three MADs resist isolated depth outliers; two pixels cover raster edge
    # quantization without treating a distant background as object surface.
    usable=mask&np.isfinite(depth)&(np.abs(depth-med)<=max(3*mad,2*pixel))
    points=cloud(depth,k,transform,usable)
    if len(points)<MIN_POINTS:return reject('SPARSE_INLIERS')
    for row in (min(v),max(v)):
        if not np.any(usable[row]):return reject('MISSING_END_DEPTH')
    width=max(u)-min(u)+1
    # Foreground at either end means the physical end may be occluded.
    support=np.zeros(mask.shape,bool)
    support[max(v)+1:min(depth.shape[0],max(v)+1+2*width),max(0,min(u)-2*width):min(depth.shape[1],max(u)+1+2*width)]=True
    support &= ~mask & np.isfinite(depth) & (depth>=.15)&(depth<=2.)
    ground=cloud(depth,k,transform,support)
    if len(ground)<MIN_POINTS:return reject('SUPPORT_UNAVAILABLE')
    ground=ground[::max(1,math.ceil(len(ground)/MAX_POINTS))]
    design=np.column_stack((ground[:,:2],np.ones(len(ground))))
    if np.linalg.matrix_rank(design)<3:return reject('SUPPORT_UNOBSERVABLE')
    plane=np.linalg.lstsq(design,ground[:,2],rcond=None)[0]
    # Bounded Huber IRLS; f-scale is measured pixel quantization, not a
    # guessed physical threshold. No heavyweight optimizer runtime needed.
    for _ in range(10):
        residual=ground[:,2]-design@plane
        weights=np.minimum(1.,pixel/np.maximum(np.abs(residual),np.finfo(float).eps))
        weighted=np.sqrt(weights)
        update=np.linalg.lstsq(design*weighted[:,None],ground[:,2]*weighted,rcond=None)[0]
        if np.linalg.norm(update-plane)<np.finfo(float).eps*100:
            plane=update;break
        plane=update
    plane_residual=np.abs(ground[:,2]-np.column_stack((ground[:,:2],np.ones(len(ground))))@plane)
    plane_error=float(np.quantile(plane_residual,.95))
    for row in (min(v)-1,max(v)+1):
        adjacent_mask=np.zeros(mask.shape,bool)
        adjacent_mask[row,min(u):max(u)+1]=True
        adjacent_mask &= np.isfinite(depth)&(depth<=med+2*pixel)&(depth>=.15)
        adjacent_points=cloud(depth,k,transform,adjacent_mask)
        if len(adjacent_points):
            residual=np.abs(adjacent_points[:,2]-np.column_stack((adjacent_points[:,:2],np.ones(len(adjacent_points))))@plane)
            if np.any(residual>plane_error+2*pixel):return reject('OCCLUDED_END')
    points=points[::max(1,math.ceil(len(points)/MAX_POINTS))]
    # Estimate cylinder axis/radius from measured cross-section, no dimension
    # prior. Robust circle fit uses every visible side row, never one pixel.
    _,_,directions=np.linalg.svd(points-np.mean(points,axis=0),full_matrices=False)
    axis=directions[0]
    if axis[2]<0:axis=-axis
    basis_u=directions[1];basis_v=np.cross(axis,basis_u)
    xy=np.column_stack((points@basis_u,points@basis_v));along=points@axis
    A=np.column_stack((2*xy,np.ones(len(xy))))
    if np.linalg.matrix_rank(A)<3:return reject('UNOBSERVABLE_CROSS_SECTION')
    fitted=np.linalg.lstsq(A,np.sum(xy*xy,axis=1),rcond=None)[0]
    center_xy=fitted[:2];radius_squared=fitted[2]+center_xy@center_xy
    if radius_squared<=0:return reject('IMPOSSIBLE_GEOMETRY')
    radius=math.sqrt(radius_squared)
    circle_error=float(np.quantile(np.abs(np.linalg.norm(xy-center_xy,axis=1)-radius),.95))
    bottom,top=np.quantile(along,[.01,.99])
    height=float(top-bottom)
    if height<=2*radius or radius<=pixel/2:return reject('NON_UPRIGHT_OR_UNOBSERVABLE')
    # Cylinder centre must be stable along height; rejects tilt/merged masks.
    low=xy[along<=bottom+height/3];high=xy[along>=top-height/3]
    if not len(low) or not len(high):return reject('MISSING_END_GEOMETRY')
    axis_drift=float(np.linalg.norm(np.mean(low,axis=0)-np.mean(high,axis=0)))
    uncertainty=pixel+plane_error+circle_error+.01*height
    if axis_drift>2*uncertainty:return reject('TILTED_OR_OCCLUDED')
    if np.linalg.norm(plane[:2])*height>MAX_UNCERTAINTY_M:return reject('GRAVITY_REFERENCE_UNAVAILABLE')
    if not math.isfinite(uncertainty) or uncertainty>MAX_UNCERTAINTY_M:return reject('UNCERTAIN_GEOMETRY')
    center=(basis_u*center_xy[0]+basis_v*center_xy[1]+axis*(bottom+top)/2).tolist()
    support_z=float(plane[:2]@np.array(center[:2])+plane[2])
    h=center[2]-support_z
    if h<=0:return reject('IMPOSSIBLE_GEOMETRY')
    result=invalid('VALID',**args)
    result.update(valid=True,source_frame=source_frame,track_id=track_id,reference_id=reference_id,
        center_m=center,support_height_m=support_z,center_height_above_support_m=h,
        uncertainty_m=uncertainty,transform_valid=True,observation_age_s=age,
        depth_sample_count=int(good.sum()),inlier_count=len(points),mask_pixels=len(values),
        valid_fraction=float(good.mean()),depth_median_m=med,depth_mad_m=mad,
        measured_radius_m=radius,measured_axis_extent_m=height,
        measured_upright_extent_m=float(np.ptp(points[:,2])),measured_axis=axis.tolist(),
        support_plane=plane.tolist(),geometry_model='complete measured cylinder')
    return result



def transform_matrix(translation,quaternion):
    """REP-103 rigid transform, quaternion XYZW, no simulator frame inputs."""
    x,y,z,w=quaternion
    if not all(math.isfinite(v) for v in (*translation,x,y,z,w)) or not math.isclose(x*x+y*y+z*z+w*w,1.,abs_tol=1e-6):
        raise ValueError('Invalid transform quaternion')
    matrix=np.eye(4)
    matrix[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                  [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                  [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    matrix[:3,3]=translation
    return matrix
