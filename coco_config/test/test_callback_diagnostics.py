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

import json
from types import SimpleNamespace
import pytest
from coco_config.callback_diagnostics import observed


def node(pub):
    return SimpleNamespace(
        _timing_pub=pub,
        get_clock=lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=123)),
    )


def test_result_and_exception_preserved_with_timing():
    records = []
    n = node(SimpleNamespace(publish=lambda m: records.append(json.loads(m.data))))
    assert observed(n, lambda x: x + 1)(4) == 5
    assert records[0]['wall_duration_ns'] >= 0

    def fail():
        raise RuntimeError('original')

    with pytest.raises(RuntimeError, match='original'):
        observed(n, fail)()
    assert len(records) == 2


def test_publisher_failure_cannot_mask_callback_result():
    def fail(_):
        raise RuntimeError('logging only')

    assert observed(node(SimpleNamespace(publish=fail)), lambda: 7)() == 7
