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

"""Write a map derived from the foundation fixture geometry."""
import argparse
from pathlib import Path
import numpy as np
import yaml
from coco_config import robot as r
from coco_sim.isaac.config import FIXTURES


def write_map(output):
    output.mkdir(parents=True, exist_ok=True)
    resolution = 0.05
    width, height = 240, 200
    origin_world = (-6.0, -5.0)
    x = origin_world[0] + (np.arange(width) + 0.5) * resolution
    y = origin_world[1] + (np.arange(height) + 0.5) * resolution
    image = np.full((height, width), 254, dtype=np.uint8)
    for _, (cx, cy, _), (sx, sy, _), _ in FIXTURES:
        mask = (np.abs(x[None, :] - cx) <= sx / 2) & (
            np.abs(y[:, None] - cy) <= sy / 2
        )
        image[mask] = 0
    (output / "fixture.pgm").write_bytes(
        f"P5\n{width} {height}\n255\n".encode() + image[::-1].tobytes()
    )
    (output / "fixture.yaml").write_text(
        yaml.safe_dump(
            dict(
                image="fixture.pgm",
                mode="trinary",
                resolution=resolution,
                origin=[
                    origin_world[0] - r.SPAWN_XY[0],
                    origin_world[1] - r.SPAWN_XY[1],
                    0.0,
                ],
                negate=0,
                occupied_thresh=0.65,
                free_thresh=0.196,
            )
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    write_map(p.parse_args().output)
