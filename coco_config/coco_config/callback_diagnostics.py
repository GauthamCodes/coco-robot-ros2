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

"""Observational callback timing; preserves return values and raised exceptions."""
from functools import wraps
import json
import time


def observed(node, callback):
    @wraps(callback)
    def invoke(*args, **kwargs):
        start = time.perf_counter_ns()
        try:
            sim_start = node.get_clock().now().nanoseconds
        except Exception:
            sim_start = None
        try:
            return callback(*args, **kwargs)
        finally:
            duration = time.perf_counter_ns() - start
            # Best effort logging must never mask the callback's exception/result.
            try:
                from std_msgs.msg import String

                node._timing_pub.publish(
                    String(
                        data=json.dumps(
                            dict(  # noqa: C408
                                callback=callback.__qualname__,
                                sim_start_ns=sim_start,
                                sim_end_ns=node.get_clock().now().nanoseconds,
                                wall_duration_ns=duration,
                            )
                        )
                    )
                )
            except Exception:
                pass

    return invoke
