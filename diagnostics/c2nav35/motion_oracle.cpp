// SPDX-License-Identifier: Apache-2.0
// Deterministic mean-motion oracle: all motion arithmetic stays in installed Nav2.
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include "nav2_amcl/pf/pf.hpp"
#include "nav2_amcl/motion_model/differential_motion_model.hpp"
static pf_vector_t origin(void *) {return pf_vector_zero();}
int main(int argc, char ** argv) {
  if (argc != 10) {return 2;}
  double v[9];
  for (int i = 0; i < 9; ++i) {
    char * end;
    v[i] = std::strtod(argv[i+1], &end);
    if (*end || !std::isfinite(v[i])) {return 2;}
  }
  auto * pf = pf_alloc(1, 1, 0, 0, origin);
  auto & set = pf->sets[pf->current_set];
  set.sample_count = 1;
  set.samples[0].pose = {{v[6], v[7], v[8]}};
  set.samples[0].weight = 1;
  nav2_amcl::DifferentialMotionModel model;
  model.initialize(0, 0, 0, 0, 0);
  pf_vector_t pose = {{v[0], v[1], v[2]}};
  pf_vector_t delta = {{v[3], v[4], v[5]}};
  srand48(12345);
  model.odometryUpdate(pf, pose, delta);
  std::cout << std::setprecision(17) << '[' << set.samples[0].pose.v[0] << ','
            << set.samples[0].pose.v[1] << ',' << set.samples[0].pose.v[2] << "]\n";
  pf_free(pf);
}
