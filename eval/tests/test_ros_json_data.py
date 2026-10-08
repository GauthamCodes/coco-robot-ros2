"""Actual startup joint-effort NaNs must not destroy trace capture."""
import json
import math
from evidence import ros_json_data


def test_nan_effort_preserves_unknown_without_crashing_strict_json():
    source=dict(header=dict(stamp=dict(sec=1,nanosec=23)),
                name=['joint'],position=[.25],velocity=[0.],effort=[float('nan')])
    encoded=ros_json_data(source)
    assert json.loads(json.dumps(encoded,allow_nan=False))==encoded
    assert encoded['effort']==[{'$ros_nonfinite_float':'NaN'}]
    assert encoded['position']==[.25]
    assert encoded['header']==source['header']
    assert math.isnan(source['effort'][0])


def test_replay_equality_handles_distinct_nan_objects_and_infinity_signs():
    left=ros_json_data(dict(values=[float('nan'),float('inf'),-float('inf')]))
    right=ros_json_data(dict(values=[float('nan'),float('inf'),-float('inf')]))
    assert left==right
    assert len({p['$ros_nonfinite_float'] for p in left['values']})==3
    assert left!=ros_json_data(dict(values=[0.,float('inf'),-float('inf')]))


def test_finite_ros_payload_is_unchanged():
    source=dict(header=dict(frame_id='base_footprint'),data=[1,2,3],x=1.5,valid=True)
    assert ros_json_data(source)==source
