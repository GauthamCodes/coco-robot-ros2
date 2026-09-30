#!/usr/bin/env python3
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

"""Summarize P03D Gazebo evidence without inferring successful runs."""

import json
import math
from pathlib import Path
import re
import sys
from collections import Counter


def observed_regions(path):
    """Collapse repeated live topic samples into a traversal sequence."""
    topic = path / 'search_regions.txt'
    if not topic.exists():
        return []
    regions = re.findall(r'^lane_\d+$', topic.read_text(), re.MULTILINE)
    return [region for i, region in enumerate(regions)
            if i == 0 or region != regions[i - 1]]


def perception_counts(path):
    """Count actual RGB-D verdicts recorded from the ROS status topic."""
    topic = path / 'target_pose_status.txt'
    if not topic.exists():
        return {}
    return dict(sorted(Counter(re.findall(
        r'\bvalidity=([A-Z_]+)', topic.read_text())).items()))


def point_samples(path):
    """Count PointStamped samples expressed in the manipulation frame."""
    topic = path / 'target_points.txt'
    return (topic.read_text().count('frame_id: base_footprint')
            if topic.exists() else 0)


def summarize(path):
    manifest_path = path / 'manifest.json'
    result_path = path / 'result.json'
    if not manifest_path.exists() or not result_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text())
    requested = manifest['requested_colour']
    target = next(t for t in manifest['targets']
                  if t['colour'] == requested)
    actual = target['region_id']
    mission = (path / 'mission.log').read_text(errors='replace') if (
        path / 'mission.log').exists() else ''
    runner = (path / 'runner.log').read_text(errors='replace') if (
        path / 'runner.log').exists() else ''
    dirty = re.search(r'dirty paths: (\d+)', runner)
    result = json.loads(result_path.read_text())
    acquired = re.findall(r'TARGET_ACQUIRED\]:?[^\n]*', mission)
    region = None
    acquired_pose = None
    if acquired:
        match = re.search(r'(lane_\d+)', acquired[-1])
        if match:
            region = match.group(1)
        match = re.search(r'base_footprint=\(([^)]+)\)', acquired[-1])
        if match:
            acquired_pose = [float(value) for value in
                             match.group(1).split(',')]
    # Fixed mode uses the old SEARCH_TARGET status gate, without an
    # explicit TARGET_ACQUIRED event. It is reported separately below.
    if region:
        perception = 'acquired'
    elif (manifest['level'] == 'fixed' and
          'SEARCH_TARGET -> STOW_ARM' in mission):
        perception = 'fixed_gate'
    else:
        perception = 'none'
    grasp = 'held' if 'VERIFY_GRASP -> DESCEND' in mission else 'not_held'
    recovery = len(re.findall(r' -> RECOVERY \[', mission))
    sim_s = result.get('timings', {}).get('mission_sim_s', '--')
    if isinstance(sim_s, float) and not math.isfinite(sim_s):
        sim_s = None
    return {
        'run': path.name,
        'episode_id': manifest['episode_id'],
        'software_commit': result.get('software_commit', '--'),
        'software_dirty_paths': (int(dirty.group(1)) if dirty else None),
        'mode': manifest['level'],
        'seed': manifest['seed'],
        'requested': requested,
        'actual_region': actual,
        'evaluator_target_world': {key: target[key]
                                   for key in ('x', 'y', 'z')},
        'acquired_region': region or '--',
        'acquired_pose_base_footprint': acquired_pose,
        'search_sequence': observed_regions(path),
        'perception_validity_counts': perception_counts(path),
        'point_samples': point_samples(path),
        'nav_goals_world': re.findall(
            r'NavigateToPose -> world \(([^)]+)\)', mission),
        'detection': perception,
        'grasp': grasp,
        'mission': result.get('outcome', 'unrecorded'),
        'failure_reason': result.get('failure_reason', '--'),
        'recoveries': recovery,
        'wall_s': result.get('timings', {}).get('mission_wall_s', '--'),
        'sim_s': sim_s,
        'runner_checks_pass': result.get('measurements', {}).get(
            'runner_checks_pass'),
        'raw_evidence_directory': str(path),
    }


def main():
    root = Path(sys.argv[1])
    rows = [row for path in sorted(root.iterdir())
            if path.is_dir() and (row := summarize(path))]
    print(json.dumps(rows, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
