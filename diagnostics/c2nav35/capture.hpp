// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <algorithm>
#include <cstdint>
#include <limits>
#include <string>

namespace c2nav35 {
constexpr double missing = std::numeric_limits<double>::quiet_NaN();
struct Record {
  const char * stage = "scan";
  uint64_t scan_id = 0, prediction_id = 0, anchor_id = 0, epoch = 0;
  int64_t scan_ns = 0, tf_ns = 0, anchor_ns = 0, receipt_ns = 0;
  int tf_ok = -1, eligible = -1, forced = -1, scanner = -1;
  int sample_count = -1, current_set = -1;
  bool truncated = false;
  char source[256] = {}, target[256] = {}, scan_frame[256] = {};
  double tf[7] = {missing, missing, missing, missing, missing, missing, missing};
  double pose[3] = {missing, missing, missing};
  double anchor[3] = {missing, missing, missing};
  double delta[3] = {missing, missing, missing};
  double motion[3] = {missing, missing, missing};
};
struct State {
  uint64_t scan_id = 0, prediction_id = 0, anchor_id = 0, epoch = 0;
  int64_t anchor_ns = 0, last_receipt_ns = 0;
};
// One process-local sink, shared by amcl_core and motions_lib.
bool enabled();
void emit(const Record & record) noexcept;
void close();
extern thread_local Record * current;
inline void frame(char (&out)[256], const std::string & in, Record & r) {
  const auto n = std::min(in.size(), sizeof(out) - 1);
  std::copy_n(in.data(), n, out);
  out[n] = 0;
  r.truncated = r.truncated || n != in.size();
}
class Context {
public:
  Record record;
  Record * previous;
  explicit Context(State & s, int64_t stamp, int64_t receipt,
    const std::string & scan, const std::string & source, const std::string & target)
  : previous(current) {
    if (!enabled()) {return;}
    if (receipt < s.last_receipt_ns) {++s.epoch;}
    s.last_receipt_ns = receipt;
    record.scan_id = ++s.scan_id;
    record.epoch = s.epoch;
    record.scan_ns = stamp;
    record.receipt_ns = receipt;
    record.anchor_id = s.anchor_id;
    record.anchor_ns = s.anchor_ns;
    frame(record.scan_frame, scan, record);
    frame(record.source, source, record);
    frame(record.target, target, record);
    current = &record;
    event("scan");
  }
  ~Context() {if (current == &record) {event("callback_end");} current = previous;}
  Context(const Context &) = delete;
  Context & operator=(const Context &) = delete;
  void event(const char * stage) {
    if (current != &record) {return;}
    record.stage = stage;
    emit(record);
  }
  void anchor(State & s) {
    s.anchor_id = record.scan_id;
    s.anchor_ns = record.scan_ns;
    event("anchor_set");
  }
};
inline void decomposition(double r1, double trans, double r2) {
  if (!current) {return;}
  current->motion[0] = r1;
  current->motion[1] = trans;
  current->motion[2] = r2;
  current->stage = "motion_decomposition";
  emit(*current);
}
}  // namespace c2nav35
