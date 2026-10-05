# Copyright 2026 Gautham Anil
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""P03D search invariants at the mission/perception boundary."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import mission_states as ms  # noqa: E402
from test_mission_states import Harness, run_to_climb  # noqa: E402


def search_harness(colour='red'):
    plan = ms.MissionPlan(colour, autonomous_search=True)
    harness = Harness(plan=plan)
    harness.colour = colour
    run_to_climb(harness, lane=plan.lane)
    assert harness.state == ms.SEARCH_TARGET
    return harness


def answer(harness, validity, *, point=None, reach='REACHABLE',
           frame='base_footprint', stamp=None, point_stamp=None,
           selected=None):
    stamp = harness.now if stamp is None else stamp
    harness.target_pose = point
    harness.target_stamp = (stamp if point_stamp is None else point_stamp
                            ) if point is not None else None
    harness.publish('pose_status',
                    f'sel={selected or harness.colour} validity={validity} '
                    f'stamp_ns={round(stamp * 1e9)} frame={frame} '
                    f'reach_appr={reach}')
    harness.tick()


@pytest.mark.parametrize('colour', ['red', 'green', 'blue', 'yellow'])
def test_search_order_is_colour_independent_and_ignores_episode_map(colour):
    plan = ms.MissionPlan(colour, autonomous_search=True,
                          region_map={'red': 'lane_4'})
    assert plan.search_regions == ('lane_1', 'lane_2', 'lane_3', 'lane_4')
    assert plan.region == 'lane_1'
    assert plan.lane == ms.lane_for_region('lane_1')


def test_first_region_acquires_only_a_matching_perceived_pose():
    harness = search_harness()
    answer(harness, 'VALID', point=(0.88, 0.002, 0.079))
    assert harness.state == ms.STOW_ARM
    assert harness.machine.acquired[0] == 'lane_1'
    assert harness.machine.acquired[1] == (0.88, 0.002, 0.079)
    assert ms.GRASP not in harness.states()
    assert 'TARGET_ACQUIRED' in harness.reasons()
    harness.worker('grasp', 'phase', 'stow', 'done', extra='lifted=0')
    assert harness.state == ms.APPROACH_TARGET
    assert harness.requests[-1] == (ms.CALL_SERVICE, '/approach/run')
    assert harness.machine.acquired[1] == (0.88, 0.002, 0.079)


@pytest.mark.parametrize('validity,reach,frame', [
    ('DEPTH_INVALID', 'REACHABLE', 'base_footprint'),
    ('NO_TRANSFORM', 'REACHABLE', 'base_footprint'),
    ('VALID', 'OFF_ARM_PLANE', 'base_footprint'),
    ('VALID', 'REACHABLE', 'map'),
])
def test_invalid_observation_cannot_trigger_approach_or_grasp(
        validity, reach, frame):
    harness = search_harness()
    point = (0.88, 0.30 if reach == 'OFF_ARM_PLANE' else 0.002, 0.079)
    answer(harness, validity, point=point,
           reach=reach, frame=frame)
    assert harness.state == ms.SEARCH_TARGET
    assert harness.machine.acquired is None
    assert ms.APPROACH_TARGET not in harness.states()
    assert ms.GRASP not in harness.states()


def test_old_frame_and_point_from_different_frames_are_rejected():
    harness = search_harness()
    answer(harness, 'VALID', point=(0.88, 0.002, 0.079),
           stamp=harness.machine.entered_at)
    assert harness.state == ms.SEARCH_TARGET
    answer(harness, 'VALID', point=(0.88, 0.002, 0.079),
           stamp=harness.now + 0.1, point_stamp=harness.now)
    assert harness.state == ms.SEARCH_TARGET


@pytest.mark.parametrize(
    'point', [(0.8, 0.26, 0.079), (-0.1, 0.0, 0.079)])
def test_pose_outside_candidate_corridor_is_rejected(point):
    harness = search_harness()
    answer(harness, 'VALID', point=point, reach='OFF_ARM_PLANE')
    assert harness.state == ms.SEARCH_TARGET
    assert harness.machine.last_search_rejection == ms.SEARCH_REJECTED_GEOMETRY


def test_region_corridor_uses_world_lateral_pose_after_off_centre_climb():
    harness = search_harness()
    # Live position seed 6: the lane_4 climb was +0.235 m off centre,
    # making the valid red point -0.272 m in base_footprint. Its WORLD
    # lateral coordinate still lies near the selected region centre.
    harness.pose = (ms.CLIMB_END_X, harness.machine.plan.lane + 0.235, 0.0)
    answer(harness, 'VALID', point=(0.9057, -0.272, 0.0808),
           reach='OFF_ARM_PLANE')
    assert harness.state == ms.STOW_ARM
    assert harness.machine.acquired[1] == (0.9057, -0.272, 0.0808)


def test_neighbouring_lane_is_rejected_even_if_point_is_robot_centred():
    harness = search_harness()
    harness.pose = (ms.CLIMB_END_X, harness.machine.plan.lane + 0.235, 0.0)
    answer(harness, 'VALID', point=(0.9057, 0.10, 0.0808),
           reach='OFF_ARM_PLANE')
    assert harness.state == ms.SEARCH_TARGET
    assert harness.machine.last_search_rejection == ms.SEARCH_REJECTED_GEOMETRY


def test_region_corridor_accounts_for_robot_heading():
    harness = search_harness()
    harness.pose = (ms.CLIMB_END_X, harness.machine.plan.lane, 0.30)
    answer(harness, 'VALID', point=(1.0, 0.0, 0.0808),
           reach='OFF_ARM_PLANE')
    assert harness.state == ms.SEARCH_TARGET
    assert harness.machine.last_search_rejection == ms.SEARCH_REJECTED_GEOMETRY


def test_absent_first_region_retreats_and_reaches_second():
    harness = search_harness()
    answer(harness, 'NOT_DETECTED')
    harness.dt = 5.0
    harness.tick(4)
    assert harness.state == ms.RECOVERY
    harness.recover()
    assert harness.state == ms.RETREAT
    expected = [('lane_1', ms.TARGET_NOT_FOUND)]
    assert harness.machine.search_rejections == expected
    harness.dt = 0.1
    harness.worker('ramp', 'segment', 'retreat', 'goal',
                   pose=(ms.RAMP_FOOT_X - 0.35, harness.machine.plan.lane, 0.0))
    assert ms.BYPASS_RAMP not in harness.states()
    assert ms.RETURN_HOME not in harness.states()
    assert harness.state == ms.NAVIGATE_TO_RAMP
    # Localization handoff is at the old lane, not the new goal's lane.
    assert harness.machine.plan.search_exit == (ms.RAMP_FOOT_X - 0.35, -0.75)
    assert harness.machine.plan.region == 'lane_2'
    assert harness.machine.plan.lane == ms.lane_for_region('lane_2')
    assert harness.requests[-1] == (ms.NAV_GOAL,
                                    harness.machine.plan.pre_ramp)

    harness.nav_arrives(*harness.machine.plan.pre_ramp)
    harness.tick(2)
    harness.worker('ramp', 'segment', 'climb', 'goal',
                   extra='lateral=0.0',
                   pose=(ms.CLIMB_END_X, harness.machine.plan.lane, 0.0))
    harness.tick(2)
    assert harness.state == ms.SEARCH_TARGET
    answer(harness, 'VALID', point=(0.84, 0.001, 0.079))
    assert harness.state == ms.STOW_ARM
    assert harness.machine.acquired[0] == 'lane_2'
    assert harness.machine.search_rejections[0][0] == 'lane_1'


def test_perception_unavailable_times_out_with_explicit_reason():
    harness = search_harness()
    harness.dt = 5.0
    harness.tick(4)
    assert harness.state == ms.RECOVERY
    assert harness.machine.reason == ms.SEARCH_PERCEPTION_UNAVAILABLE


def test_invalid_depth_times_out_as_rejected_depth():
    harness = search_harness()
    answer(harness, 'DEPTH_INVALID')
    harness.dt = 5.0
    harness.tick(4)
    assert harness.state == ms.RECOVERY
    assert harness.machine.reason == ms.SEARCH_REJECTED_DEPTH


def test_search_exhaustion_records_failure_and_retreats():
    harness = search_harness()
    harness.machine.search_index = 3
    harness.machine.plan.region = 'lane_4'
    harness.machine.plan.lane = ms.lane_for_region('lane_4')
    answer(harness, 'NOT_DETECTED')
    harness.dt = 5.0
    harness.tick(4)
    harness.recover()
    assert harness.machine.search_exhausted
    assert harness.machine.degraded_reason == ms.SEARCH_FAILED
    assert harness.state == ms.RETREAT


def test_all_four_regions_are_tried_before_search_failure():
    harness = search_harness()
    visited = []
    for candidate in ('lane_1', 'lane_2', 'lane_3', 'lane_4'):
        assert harness.machine.plan.region == candidate
        visited.append(candidate)
        answer(harness, 'NOT_DETECTED')
        harness.dt = 5.0
        harness.tick(4)
        harness.recover()
        assert harness.state == ms.RETREAT
        harness.dt = 0.1
        harness.worker('ramp', 'segment', 'retreat', 'goal',
                   pose=(ms.RAMP_FOOT_X - 0.35, harness.machine.plan.lane, 0.0))
        if candidate == 'lane_4':
            assert harness.state == ms.RETURN_HOME
            break
        assert harness.state == ms.NAVIGATE_TO_RAMP
        harness.nav_arrives(*harness.machine.plan.pre_ramp)
        harness.tick(2)
        harness.worker('ramp', 'segment', 'climb', 'goal',
                       extra='lateral=0.0',
                       pose=(ms.CLIMB_END_X,
                             harness.machine.plan.lane, 0.0))
        harness.tick(2)
        assert harness.state == ms.SEARCH_TARGET
    assert visited == list(harness.machine.plan.search_regions)
    assert harness.machine.search_exhausted
    assert harness.machine.degraded_reason == ms.SEARCH_FAILED
    assert harness.state == ms.RETURN_HOME
    assert ms.GRASP not in harness.states()


@pytest.mark.parametrize('pose', [(4.50, -0.75, 0.0),
                                  (0.65, 0.75, 0.0)])
def test_retreat_worker_success_requires_near_exit_pose(pose):
    harness = search_harness()
    harness.dt = 5.0
    harness.tick(4)
    harness.recover()
    assert harness.state == ms.RETREAT
    harness.dt = 0.1
    harness.worker('ramp', 'segment', 'retreat', 'goal', pose=pose)
    assert ms.RECOVERY in harness.states()
    assert harness.machine.reason == ms.RETREAT_POSE_UNVERIFIED
    assert ms.RETURN_HOME not in harness.states()
    harness.recover()
    assert harness.state == ms.ABORT


def test_retreat_failure_cannot_continue_search_or_grasp():
    harness = search_harness()
    harness.dt = 5.0
    harness.tick(4)
    harness.recover()
    harness.dt = 0.1
    harness.worker('ramp', 'segment', 'retreat', 'timeout')
    assert ms.RECOVERY in harness.states()
    assert harness.machine.reason == ms.RETREAT_TIMEOUT
    harness.recover()
    assert harness.state == ms.ABORT
    assert ms.APPROACH_TARGET not in harness.states()
    assert ms.GRASP not in harness.states()
