"""Verify the offline geometry instrument, not robot observation capability."""
import numpy as np
from mount_probe import box_triangles, intersects, view


def test_segment_hits_closed_box_from_either_side():
    box = box_triangles([2., 2., 2.])
    assert intersects(np.array([-2., 0., 0.]), np.array([2., 0., 0.]), box)
    assert intersects(np.array([2., 0., 0.]), np.array([-2., 0., 0.]), box)


def test_occluder_beyond_target_is_not_a_blocker():
    box = box_triangles([2., 2., 2.]) + [4., 0., 0.]
    assert not intersects(np.array([0., 0., 0.]), np.array([2., 0., 0.]), box)


def test_parallel_miss_is_not_an_occlusion():
    box = box_triangles([2., 2., 2.])
    assert not intersects(np.array([-2., 2., 0.]), np.array([2., 2., 0.]), box)


def test_frustum_rejects_near_plane_and_accepts_forward_volume():
    assert view(np.zeros(3), np.array([[.04, -.01, -.02], [.05, .01, .02]])) is None
    assert view(np.zeros(3), np.array([[.4, -.01, -.02], [.5, .01, .02]])) is not None
