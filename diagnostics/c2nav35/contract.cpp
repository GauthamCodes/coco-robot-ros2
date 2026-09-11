// SPDX-License-Identifier: Apache-2.0
// Synthetic event/loss contract test; no ROS or motion-model approximation.
#include "capture.hpp"
#include <chrono>
#include <cstring>
#include <thread>
int main(int argc, char ** argv) {
  c2nav35::State state;
  if (argc > 1 && std::strcmp(argv[1], "overflow") == 0) {
    c2nav35::Record record;
    for (int i = 0; i < 100000; ++i) {c2nav35::emit(record);}
  } else {
    {
      c2nav35::Context event(state, 1000000007LL, 2000000009LL,
        "scan\"\\\n", "base_footprint", "odom");
      event.record.tf_ok = 0;
      event.event("tf_failure");
    }
    // Space synthetic events to avoid intentionally testing lock contention here.
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    {
      c2nav35::Context event(state, 1000000017LL, 2000000019LL,
        "scan", "base_footprint", "odom");
      event.record.tf_ok = 1;
      event.record.tf_ns = 1000000017LL;
      event.record.pose[0] = 2;
      event.record.pose[1] = 3;
      event.record.pose[2] = .2;
      event.event("tf_success");
      event.anchor(state);
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    {
      c2nav35::Context event(state, 1000000027LL, 2000000029LL,
        "scan", "base_footprint", "odom");
      event.record.eligible = 0;
      event.record.forced = 0;
      event.event("eligibility");
      event.event("sensor_failure");  // Deliberately do not advance anchor.
    }
  }
  c2nav35::close();
}
