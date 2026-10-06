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

"""Logging-only candidate geometry. Never supplies or changes a decision."""
import json
import math

import numpy as np


def candidates(
    hsv,
    depth,
    colour,
    intrinsics,
    near,
    far,
    tolerance,
    stamp_ns,
    frame,
    selected_label=None,
    selected_reason='NOT_SELECTED',
    depth_stamp_ns=None,
):
    # Imports at call time avoid a cycle with TargetFinder.
    from .target_finder import (
        colour_mask,
        blob_stats,
        robust_depth,
        surface_to_axis,
        plausible_blob,
        MIN_BLOB_PX,
    )
    from coco_config.robot import target_by_colour

    target = target_by_colour(colour)
    mask = colour_mask(hsv, colour)
    blobs, labels = blob_stats(mask, min_area=1)
    fx, fy, cx, cy = intrinsics
    paired = depth is not None and depth.shape[:2] == labels.shape
    result = []
    for area, u, v, width, height, label in blobs:
        component = labels == label
        raw = np.asarray(depth[component], dtype=float) if paired else np.array([])
        good = raw[np.isfinite(raw) & (raw > near) & (raw < far)]
        surface = robust_depth(raw, near, far) if paired else None
        rng = (
            surface_to_axis(surface, target.diameter / 2)
            if surface is not None
            else None
        )
        geometric = (
            'BLOB_TOO_SMALL'
            if area < MIN_BLOB_PX
            else (
                'DEPTH_INVALID'
                if rng is None
                else (
                    'VALID'
                    if plausible_blob(width, target.diameter, rng, fx, tolerance)
                    else 'IMPLAUSIBLE_SIZE'
                )
            )
        )
        points = None
        if paired and good.size:
            ys, xs = np.nonzero(component)
            valid = np.isfinite(raw) & (raw > near) & (raw < far)
            z = raw[valid]
            points = np.stack(
                ((xs[valid] - cx) * z / fx, (ys[valid] - cy) * z / fy, z), axis=1
            )
        centroid = points.mean(axis=0).tolist() if points is not None else None
        extents = (
            (points.max(axis=0) - points.min(axis=0)).tolist()
            if points is not None
            else None
        )
        reason = (
            selected_reason
            if label == selected_label
            else geometric if geometric != 'VALID' else 'NOT_SELECTED'
        )
        result.append(
            dict(  # noqa: C408
                schema_version=1,
                stamp_ns=stamp_ns,
                depth_stamp_ns=depth_stamp_ns,
                frame=frame,
                colour=colour,
                label=label,
                centroid=centroid,
                centroid_uv=[u, v],
                extents_m=extents,
                point_count=int(good.size),
                mask_area_px=area,
                expected_width_px=(target.diameter * fx / rng if rng else None),
                width_px=width,
                height_px=height,
                depth_statistics={
                    'finite_count': int(np.isfinite(raw).sum()),
                    'valid_count': int(good.size),
                    'median_m': float(np.median(good)) if good.size else None,
                    'min_m': float(good.min()) if good.size else None,
                    'max_m': float(good.max()) if good.size else None,
                    'mad_m': (
                        float(np.median(abs(good - np.median(good))))
                        if good.size
                        else None
                    ),
                },
                range_m=rng,
                bearing_rad=math.atan2(u - cx, fx),
                touches_image_edge=bool(
                    component[0, :].any()
                    or component[-1, :].any()
                    or component[:, 0].any()
                    or component[:, -1].any()
                ),
                accepted=label == selected_label and selected_reason == 'VALID',
                reason=reason,
                geometry_reason=geometric,
                extent_kind=('visible surface in camera optical frame; '
                             'not object-center or full-cylinder dimensions'),
            )
        )
    return result


def emit(
    node,
    hsv,
    depth,
    msg,
    selected_label=None,
    selected_reason='NOT_SELECTED',
    depth_stamp_ns=None,
):
    """Best-effort post-decision publication; diagnostics cannot fail perception."""
    from std_msgs.msg import String

    try:
        stamp = msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec
        for record in candidates(
            hsv,
            depth,
            node.selected,
            node.intrinsics,
            node.min_range,
            node.max_range,
            node.width_tolerance,
            stamp,
            msg.header.frame_id,
            selected_label,
            selected_reason,
            depth_stamp_ns,
        ):
            node._candidate_pub.publish(
                String(data=json.dumps(record, allow_nan=False))
            )
    except Exception as exc:
        node.get_logger().warn(
            f'candidate diagnostics unavailable: {exc}', throttle_duration_sec=5.0
        )
