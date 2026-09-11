// SPDX-License-Identifier: Apache-2.0
// No node/init/spin: exercise the real motion library and its diagnostic hook.
#include <cstdio>
#include <cstdlib>
#include "nav2_amcl/pf/pf.hpp"
#include "nav2_amcl/motion_model/differential_motion_model.hpp"
#ifdef C2NAV35_CAPTURE
#include "nav2_amcl/capture.hpp"
#endif
static pf_vector_t origin(void *) {return pf_vector_zero();}
int main() {
  constexpr int n = 100;
  auto * pf = pf_alloc(n, n, 0, 0, origin);
  pf->sets[pf->current_set].sample_count = n;
  for (int i = 0; i < n; ++i) {
    auto & p = pf->sets[pf->current_set].samples[i];
    p.pose = pf_vector_zero();
    p.pose.v[2] = i * 0.01;
    p.weight = 1.0 / n;
  }
  nav2_amcl::DifferentialMotionModel model;
  model.initialize(.2, .2, .2, .2, .2);
  srand48(12345);
#ifdef C2NAV35_CAPTURE
  c2nav35::State state;
#endif
  const double cases[][3] = {{0, 0, .3}, {1, 0, 0}, {-1, 0, 0}, {.1, .2, -.4}};
  for (int j = 0; j < 4; ++j) {
    pf_vector_t pose = {{cases[j][0], cases[j][1], cases[j][2]}};
    pf_vector_t delta = pose;
#ifdef C2NAV35_CAPTURE
    c2nav35::Context context(state, 1000000001LL + j, 2000000001LL + j,
      "scan", "base_footprint", "odom");
    context.record.prediction_id = ++state.prediction_id;
    context.record.tf_ok = 1;
    context.record.eligible = 1;
    context.event("prediction_begin");
#endif
    model.odometryUpdate(pf, pose, delta);
#ifdef C2NAV35_CAPTURE
    context.event("prediction_end");
#endif
  }
  for (int i = 0; i < n; ++i) {
    const auto & p = pf->sets[pf->current_set].samples[i];
    std::printf("%a %a %a %a\n", p.pose.v[0], p.pose.v[1], p.pose.v[2], p.weight);
  }
  std::printf("rng=%a\n", drand48());
  pf_free(pf);
#ifdef C2NAV35_CAPTURE
  c2nav35::close();
#endif
}
