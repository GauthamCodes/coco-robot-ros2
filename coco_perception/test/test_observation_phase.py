from coco_config.observation_phase import PhaseValidator
from test_object_height import fixture
from coco_perception.object_height import estimate_object_height

def test_phase_boundary_needs_new_live_sample():
    a=fixture();o=estimate_object_height(**a);t=o["stamp_ns"]
    v=PhaseValidator("red");v.transition("baseline",t-1)
    assert v.record(o,t)["contract_valid"]
    v.transition("lift",t)
    assert v.record(o,t)["rejection_reason"]=="PRE_TRANSITION_SAMPLE"
    fresh=dict(o,stamp_ns=t+1,depth_stamp_ns=t+1)
    assert v.record(fresh,t+1)["contract_valid"]
    assert v.record(fresh,t+1)["rejection_reason"]=="NON_MONOTONIC_SAMPLE"
    assert not v.record(fresh,t+300_000_001)["contract_valid"]

def test_changed_identity_cannot_prove_lift():
    a=fixture();o=estimate_object_height(**a);t=o["stamp_ns"]
    v=PhaseValidator("red");v.transition("baseline",t-1);v.record(o,t)
    v.transition("lift",t)
    fresh=dict(o,stamp_ns=t+1,depth_stamp_ns=t+1,track_id="another")
    assert v.record(fresh,t+1)["rejection_reason"]=="ASSOCIATION_OR_REFERENCE_CHANGED"
    v.reacquire("red");v.transition("baseline",t)
    assert v.record(fresh,t+1)["contract_valid"]
