// SPDX-License-Identifier: Apache-2.0
#include "capture.hpp"
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <iomanip>
#include <mutex>
#include <sstream>
#include <thread>
#include <unistd.h>

#ifndef C2NAV35_FINGERPRINT
#define C2NAV35_FINGERPRINT "standalone-test"
#endif

namespace c2nav35 {
thread_local Record * current = nullptr;
namespace {
std::string quote(const char * s) {
  std::ostringstream out;
  out << '"';
  for (; *s; ++s) {
    const unsigned char c = *s;
    if (c == '"' || c == '\\') {out << '\\' << c;}
    else if (c < 32) {out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c);}
    else {out << c;}
  }
  out << '"';
  return out.str();
}
template<size_t N> void array(std::ostream & out, const double (&v)[N]) {
  out << '[';
  for (size_t i = 0; i < N; ++i) {
    if (i) {out << ',';}
    if (std::isfinite(v[i])) {out << std::setprecision(17) << v[i];}
    else {out << "null";}
  }
  out << ']';
}
class Sink {
  std::array<Record, 4096> queue_{};
  size_t head_ = 0, tail_ = 0, size_ = 0;
  std::mutex mutex_;
  std::atomic<bool> stop_{false};
  std::atomic<uint64_t> dropped_{0};
  std::thread worker_;
  FILE * file_ = nullptr;
  bool failed_ = false;
  void write(const std::string & s) {
    if (std::fwrite(s.data(), 1, s.size(), file_) != s.size() || std::fflush(file_)) {
      if (!failed_) {std::fputs("C2NAV35: diagnostic write failed; capture UNOBSERVABLE\n", stderr);}
      failed_ = true;
    }
  }
  void drain() {
    for (;;) {
      Record r;
      bool have = false;
      {
        std::lock_guard<std::mutex> lock(mutex_);
        if (size_) {r = queue_[tail_]; tail_ = (tail_ + 1) % queue_.size(); --size_; have = true;}
      }
      if (!have) {
        if (stop_) {break;}
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
        continue;
      }
      std::ostringstream o;
      o << "{\"schema\":1,\"stage\":" << quote(r.stage)
        << ",\"scan_id\":" << r.scan_id << ",\"prediction_id\":" << r.prediction_id
        << ",\"anchor_id\":" << r.anchor_id << ",\"epoch\":" << r.epoch
        << ",\"scan_ns\":" << r.scan_ns << ",\"tf_ns\":"
        << (r.tf_ok == 1 ? std::to_string(r.tf_ns) : "null")
        << ",\"anchor_ns\":" << (r.anchor_id ? std::to_string(r.anchor_ns) : "null")
        << ",\"receipt_ns\":" << r.receipt_ns
        << ",\"tf_ok\":" << r.tf_ok << ",\"eligible\":" << r.eligible
        << ",\"forced\":" << r.forced << ",\"scanner\":" << r.scanner
        << ",\"sample_count\":" << r.sample_count << ",\"current_set\":" << r.current_set
        << ",\"truncated\":" << (r.truncated ? "true" : "false")
        << ",\"source\":" << quote(r.source) << ",\"target\":" << quote(r.target)
        << ",\"scan_frame\":" << quote(r.scan_frame) << ",\"tf\":";
      array(o, r.tf); o << ",\"pose\":"; array(o, r.pose);
      o << ",\"anchor\":"; array(o, r.anchor);
      o << ",\"delta\":"; array(o, r.delta);
      o << ",\"motion\":"; array(o, r.motion);
      o << "}\n";
      write(o.str());
    }
    write("{\"schema\":1,\"stage\":\"footer\",\"dropped\":" +
      std::to_string(dropped_.load()) + ",\"write_failed\":" +
      (failed_ ? "true" : "false") + "}\n");
  }
public:
  Sink() {
    const char * path = std::getenv("C2NAV35_TRACE");
    if (!path || !*path) {return;}
    const int fd = ::open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) {std::perror("C2NAV35: cannot create exclusive trace"); return;}
    file_ = ::fdopen(fd, "w");
    if (!file_) {::close(fd); return;}
    write("{\"schema\":1,\"stage\":\"manifest\",\"nav2\":\"1.3.11\","
      "\"instrumentation_sha256\":\"" C2NAV35_FINGERPRINT "\",\"pid\":" +
      std::to_string(::getpid()) + "}\n");
    worker_ = std::thread([this] {drain();});
  }
  ~Sink() {finish();}
  bool enabled() const {return file_ != nullptr && !stop_;}
  void push(const Record & r) noexcept {
    if (!enabled()) {return;}
    std::unique_lock<std::mutex> lock(mutex_, std::try_to_lock);
    if (!lock.owns_lock() || size_ == queue_.size()) {++dropped_; return;}
    queue_[head_] = r; head_ = (head_ + 1) % queue_.size(); ++size_;
  }
  void finish() {
    stop_ = true;
    if (worker_.joinable()) {worker_.join();}
    if (file_) {std::fclose(file_); file_ = nullptr;}
  }
};
Sink & sink() {static Sink value; return value;}
}  // namespace
bool enabled() {return sink().enabled();}
void emit(const Record & r) noexcept {sink().push(r);}
void close() {sink().finish();}
}  // namespace c2nav35
