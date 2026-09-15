#!/usr/bin/env python3
"""Prepare an isolated, checksum-pinned AMCL overlay. Never builds or runs ROS."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

SHA256 = '05782fd66698ea51de6a62d2483da34b85c1149ef93ba7c1b67507005a4d0170'
URL = 'https://codeload.github.com/ros-navigation/navigation2/tar.gz/refs/tags/1.3.11'
HERE = Path(__file__).resolve().parent


def guarded(code):
    return '\n#ifdef C2NAV35_CAPTURE\n' + code + '\n#endif\n'


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f'{path}: expected exactly one patch site: {old[:70]}')
    path.write_text(text.replace(old, new))


def prepare(archive, destination):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError('upstream archive checksum mismatch')
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            prefix = 'navigation2-1.3.11/nav2_amcl/'
            if not member.name.startswith(prefix) or not member.isfile():
                continue
            relative = Path(member.name[len(prefix):])
            if '..' in relative.parts or relative.is_absolute():
                raise ValueError('unsafe archive path')
            output = destination / 'src/nav2_amcl' / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source:
                output.write_bytes(source.read())
    root = destination / 'src/nav2_amcl'
    baseline = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob('*') if p.is_file()}
    shutil.copyfile(HERE / 'capture.hpp', root / 'include/nav2_amcl/capture.hpp')
    shutil.copyfile(HERE / 'capture.cpp', root / 'src/capture.cpp')
    replace(root / 'src/capture.cpp', '#include "capture.hpp"',
            '#include "nav2_amcl/capture.hpp"')
    cmake = root / 'CMakeLists.txt'
    fingerprint = hashlib.sha256(b''.join((HERE / name).read_bytes() for name in
                                 ('prepare.py', 'capture.hpp', 'capture.cpp'))).hexdigest()
    replace(cmake, 'add_subdirectory(src/pf)', '''option(C2NAV35_CAPTURE "Exact input diagnostic (OFF by default)" OFF)
if(C2NAV35_CAPTURE)
  add_compile_definitions(C2NAV35_CAPTURE)
  find_package(Threads REQUIRED)
  add_library(c2nav35_capture SHARED src/capture.cpp)
  target_link_libraries(c2nav35_capture Threads::Threads)
  install(TARGETS c2nav35_capture LIBRARY DESTINATION lib)
endif()

add_subdirectory(src/pf)''')
    replace(cmake, '  add_library(c2nav35_capture SHARED src/capture.cpp)',
            '  add_library(c2nav35_capture SHARED src/capture.cpp)\n'
            '  target_compile_definitions(c2nav35_capture PRIVATE '
            f'C2NAV35_FINGERPRINT="{fingerprint}")')
    replace(cmake, 'target_include_directories(${library_name} PRIVATE src/include)',
            '''target_include_directories(${library_name} PRIVATE src/include)
if(C2NAV35_CAPTURE)
  target_link_libraries(${library_name} c2nav35_capture)
endif()''')
    motion_cmake = root / 'src/motion_model/CMakeLists.txt'
    replace(motion_cmake, 'target_link_libraries(motions_lib pf_lib)',
            '''target_link_libraries(motions_lib pf_lib)
if(C2NAV35_CAPTURE)
  target_link_libraries(motions_lib c2nav35_capture)
endif()''')
    node = root / 'src/amcl_node.cpp'
    site = '#include "nav2_amcl/amcl_node.hpp"'
    replace(node, site, site + guarded('#include "nav2_amcl/capture.hpp"'))
    replace(node, '  initParameters();', '  initParameters();' + guarded(
        '  (void)c2nav35::enabled();  // Initialize sink outside scan callbacks.'))
    site = '  std::lock_guard<std::recursive_mutex> cfl(mutex_);'
    start = 'AmclNode::laserReceived(sensor_msgs::msg::LaserScan::ConstSharedPtr laser_scan)\n{\n' + site
    replace(node, start, start + guarded('''  // One AMCL instance per diagnostic process; retain the public class ABI.
  static thread_local c2nav35::State diagnostic_state;
  c2nav35::Context diagnostic(diagnostic_state,
    rclcpp::Time(laser_scan->header.stamp).nanoseconds(), now().nanoseconds(),
    laser_scan->header.frame_id, base_frame_id_, odom_frame_id_);'''))
    replace(node, '    ++scan_error_count_;', guarded('''    if (c2nav35::current) {
      c2nav35::current->tf_ok = 0;
      c2nav35::current->stage = "tf_failure";
      c2nav35::emit(*c2nav35::current);
    }''') + '    ++scan_error_count_;')
    site = '  yaw = tf2::getYaw(odom_pose.pose.orientation);'
    replace(node, site, site + guarded('''  if (c2nav35::current) {
    auto & d = *c2nav35::current;
    d.tf_ok = 1;
    d.tf_ns = rclcpp::Time(odom_pose.header.stamp).nanoseconds();
    c2nav35::frame(d.target, odom_pose.header.frame_id, d);
    c2nav35::frame(d.source, ident.header.frame_id, d);
    const auto & p = odom_pose.pose.position;
    const auto & q = odom_pose.pose.orientation;
    const double tf[] = {p.x, p.y, p.z, q.x, q.y, q.z, q.w};
    std::copy_n(tf, 7, d.tf);
    d.pose[0] = x; d.pose[1] = y; d.pose[2] = yaw;
    d.stage = "tf_success";
    c2nav35::emit(d);
  }'''))
    site = '  pf_vector_t delta = pf_vector_zero();'
    replace(node, site, guarded('''  if (c2nav35::current) {
    auto & d = diagnostic.record;
    d.scanner = laser_index;
    d.forced = force_update_;
    if (pf_init_) {std::copy_n(pf_odom_pose_.v, 3, d.anchor);}
  }''') + site)
    # Cleanup joins the scan executor before closing the sink. No producer remains.
    site = '  executor_thread_.reset();'
    replace(node, site, site + guarded('  c2nav35::close();'))
    site = '    pf_odom_pose_ = pose;'
    replace(node, site, site + guarded('    diagnostic.anchor(diagnostic_state);'))
    # Eligibility is read at its existing calculation, not recomputed.
    site = '  update = update || force_update_;'
    replace(node, site, guarded('''  if (c2nav35::current) {
    c2nav35::current->eligible = update;  // Threshold-only, before force flag.
  }''') + site + guarded('''  if (c2nav35::current) {
    std::copy_n(delta.v, 3, c2nav35::current->delta);
    c2nav35::current->stage = "eligibility";
    c2nav35::emit(*c2nav35::current);
  }'''))
    site = '      motion_model_->odometryUpdate(pf_, pose, delta);'
    replace(node, site, guarded('''      if (c2nav35::current) {
        diagnostic.record.prediction_id = ++diagnostic_state.prediction_id;
        diagnostic.record.sample_count = pf_->sets[pf_->current_set].sample_count;
        diagnostic.record.current_set = pf_->current_set;
        std::copy_n(delta.v, 3, diagnostic.record.delta);
        diagnostic.event("prediction_begin");
      }''') + site + guarded('      diagnostic.event("prediction_end");'))
    site = '    updateFilter(laser_index, laser_scan, pose);'
    replace(node, site, '''#ifdef C2NAV35_CAPTURE
    const bool diagnostic_sensor_ok = updateFilter(laser_index, laser_scan, pose);
    diagnostic.event(diagnostic_sensor_ok ? "sensor_success" : "sensor_failure");
    if (diagnostic_sensor_ok) {diagnostic.anchor(diagnostic_state);}
#else
''' + site + '\n#endif')
    # Jazzy's installed MessageFilter exposes no registerFailureCallback.
    # Do not fabricate pre-callback drop events or patch tf2 behavior.
    model = root / 'src/motion_model/differential_motion_model.cpp'
    site = '#include "nav2_amcl/motion_model/differential_motion_model.hpp"'
    replace(model, site, site + guarded('#include "nav2_amcl/capture.hpp"'))
    site = '  delta_rot2 = angleutils::angle_diff(delta.v[2], delta_rot1);'
    replace(model, site, site + guarded(
        '  c2nav35::decomposition(delta_rot1, delta_trans, delta_rot2);'))
    manifest = {'upstream_url': URL, 'archive_sha256': SHA256,
                'instrumentation_sha256': fingerprint,
                'baseline': baseline,
                'patched': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in root.rglob('*') if p.is_file()}}
    (destination / 'source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(prepare(args.archive, args.destination))
