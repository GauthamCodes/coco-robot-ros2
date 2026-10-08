import copy
from pathlib import Path
import cv2
import numpy as np
import pytest
from coco_perception.object_height import estimate_object_height,guarded_height
from coco_perception.target_finder import colour_mask


def fixture():
    f=np.load(Path(__file__).parent/'data/real_rgbd_target.npz')
    return dict(mask=colour_mask(cv2.cvtColor(f['rgb'],cv2.COLOR_BGR2HSV),'red')>0,
        depth=f['depth'],k=f['k'],transform=f['transform'],stamp_ns=int(f['stamp_ns']),
        depth_stamp_ns=int(f['depth_stamp_ns']),now_ns=int(f['stamp_ns']),colour='red',
        source_frame='camera_optical_frame',depth_frame='camera_optical_frame',
        track_id='sensor-track-1',reference_id='observed-support-1')


def test_real_target_geometry_without_height_prior():
    args=fixture();o=estimate_object_height(**args)
    assert o['valid'],o['reason']
    # Evaluator/test-only physical SDF expectation; not an estimator argument.
    assert o['center_height_above_support_m']==pytest.approx(.079,abs=.003)
    assert o['measured_upright_extent_m']==pytest.approx(.158,abs=.004)
    assert o['center_m'][0]==pytest.approx(.35,abs=.003)
    assert guarded_height(o,now_ns=args['now_ns'],colour='red')==o['center_height_above_support_m']


@pytest.mark.parametrize('case',[ 'nan','no_depth','near','sparse','stale','future','tf','frame','association','partial','truncated','impossible_tf'])
def test_invalid_measurements_fail_closed(case):
    a=fixture()
    if case=='nan':a['depth']=np.full_like(a['depth'],np.nan)
    if case=='no_depth':a['depth']=np.zeros_like(a['depth'])
    if case=='near':a['depth'][a['mask']]=.05
    if case=='sparse':
        indices=np.argwhere(a['mask']);a['depth'][a['mask']]=np.nan
        for v,u in indices[:5]:a['depth'][v,u]=.216
    if case=='stale':a['now_ns']+=300_000_000
    if case=='future':a['now_ns']-=1
    if case=='tf':a['transform']=None
    if case=='frame':a['depth_frame']='wrong'
    if case=='association':a['track_id']=''
    if case=='partial':a['mask'][:120]=False
    if case=='truncated':a['mask'][0,160]=True
    if case=='impossible_tf':a['transform'][0,0]=float('nan')
    o=estimate_object_height(**a)
    assert not o['valid'],(case,o)
    assert guarded_height(o,now_ns=a['now_ns'],colour='red') is None


def test_outliers_do_not_create_false_lift():
    a=fixture();indices=np.argwhere(a['mask'])
    for v,u in indices[::20]:a['depth'][v,u]=1.8
    o=estimate_object_height(**a)
    assert o['valid'],o['reason']
    assert abs(o['center_height_above_support_m']-.079)<o['uncertainty_m']


def test_consumer_rechecks_frame_identity_age_and_geometry():
    a=fixture();o=estimate_object_height(**a)
    for key,value in [('frame_id','world'),('colour','blue'),('center_height_above_support_m',float('nan')),
                      ('transform_valid',False),('uncertainty_m',.1),('center_m',[0,0,99]),('units','mm')]:
        changed=dict(o);changed[key]=value
        assert guarded_height(changed,now_ns=a['now_ns'],colour='red') is None
    assert guarded_height(o,now_ns=a['now_ns']+300_000_000,colour='red') is None
