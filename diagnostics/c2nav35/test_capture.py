#!/usr/bin/env python3
"""Offline instrumentation tests. No rclpy/rclcpp initialization or nodes."""
import ast
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace as NS
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


joiner = load('joiner', HERE / 'join.py')
capture = load('capture', ROOT / 'gazebo_models/scripts/odom_capture.py')
prepare = load('prepare', HERE / 'prepare.py')


def gt(stamp, x, identity=1):
    return dict(schema=1, stage='gt', epoch=0, stamp_ns=stamp, id=identity,
                frame='world', child='model', pose=[x, 0, 0, 0, 0, 0, 1])


def events():
    anchor = dict(stage='tf_success', epoch=0, scan_id=1, scan_ns=10, tf_ns=10,
                  tf_ok=1, scan_frame='scan', tf=[0, 0, 0, 0, 0, 0, 1],
                  pose=[0, 0, 0], source='base_footprint', target='odom')
    prediction = dict(stage='prediction_begin', epoch=0, scan_id=2,
                      scan_ns=20, tf_ns=20, prediction_id=1, anchor_id=1, anchor_ns=10,
                      pose=[1.08, 0, 0], anchor=[0, 0, 0], delta=[1.08, 0, 0],
                      source='base_footprint', target='odom',
                      tf_ok=1, truncated=False, scan_frame='scan', tf=[1.08, 0, 0, 0, 0, 0, 1])
    current = dict(prediction, stage='tf_success')
    current['pose'] = prediction['pose']
    return [anchor, prediction,
            dict(prediction, stage='motion_decomposition', motion=[0, 1.08, 0]),
            dict(prediction, stage='prediction_end'), current]


class CaptureTests(unittest.TestCase):

    def test_installed_oracle_lateral_and_world(self):
        oracle = ROOT / os.environ.get('C2NAV35_BUILD_ROOT', '.navbench/c2nav35') / 'motion_oracle'
        # Odom displacement has lateral motion, projected from a 90-degree GT anchor.
        output = subprocess.check_output([str(oracle), '1', '.25', '.1',
                                          '1', '.25', '.1', '0', '0', str(math.pi/2)],
                                         text=True)
        x, y, yaw = json.loads(output)
        self.assertAlmostEqual(x, -.25)
        self.assertAlmostEqual(y, 1)
        self.assertAlmostEqual(yaw, math.pi/2+.1)

    def test_mismatched_prediction_event(self):
        data = events()
        data[2]['scan_ns'] = 21
        with self.assertRaises(ValueError):
            joiner.join(data, [gt(10, 0), gt(20, 1, 2)], [0, 0, 0, 0, 0, 0, 1], 20)

    def test_current_tf_and_end_required(self):
        for index in (3, 4):
            data = events()
            data.pop(index)
            rows = joiner.join(data, [gt(10, 0), gt(20, 1, 2)], [0, 0, 0, 0, 0, 0, 1], 20)
            self.assertEqual(rows[0]['status'], 'unobservable')

    def test_frame_duplicate_and_clock_rejected(self):
        for change in ('frame', 'duplicate', 'epoch', 'ordering'):
            data = [gt(10, 0), gt(20, 1, 2)]
            if change == 'frame':
                data[1]['child'] = 'other'
            elif change == 'duplicate':
                data[1]['id'] = 1
            elif change == 'epoch':
                data[1]['epoch'] = 1
            else:
                data.reverse()
            with self.assertRaises(ValueError):
                joiner.join(events(), data, [0, 0, 0, 0, 0, 0, 1], 20)

    def test_no_tf_records(self):
        with self.assertRaises(ValueError):
            joiner.join([r for r in events() if r['stage'] != 'tf_success'],
                        [gt(10, 0), gt(20, 1, 2)], [0, 0, 0, 0, 0, 0, 1], 20)

    def test_lateral_world_projection(self):
        data = events()
        data[1]['pose'][1] = .25
        data[1]['tf'][1] = .25
        samples = [gt(10, 0), gt(20, 0, 2)]
        for r in samples:
            r['pose'][5:] = [math.sin(math.pi/4), math.cos(math.pi/4)]
        samples[1]['pose'][1] = 1
        row = joiner.join(data, samples, [0, 0, 0, 0, 0, 0, 1], 20)[0]
        self.assertAlmostEqual(row['longitudinal'], .08)
        self.assertAlmostEqual(row['lateral'], .25)
        self.assertAlmostEqual(row['world_residual'][0], -.25)
        self.assertAlmostEqual(row['world_residual'][1], .08)

    def test_integrity_count_and_empty_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data'
            body = dict(schema=1, stage='gt')
            footer = dict(schema=1, stage='footer', attempted=1, successful=1,
                          malformed=0, dropped=0, write_failed=False, completion='complete')
            for rows, valid in (([body], True), ([], False), ([body, body], False)):
                path.write_text(''.join(json.dumps(r)+'\n' for r in
                                       [dict(schema=1, stage='manifest'), *rows, footer]))
                if valid:
                    self.assertEqual(len(joiner.read(path)), 3)
                else:
                    with self.assertRaises(ValueError):
                        joiner.read(path)

    def test_gt_acquisition_and_receipt_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'gt.jsonl'
            sink = capture.GroundTruthCapture(path)
            msg = NS(header=NS(stamp=NS(sec=3, nanosec=123), frame_id='world'),
                     child_frame_id='model', pose=NS(pose=NS(
                         position=NS(x=1, y=2, z=3),
                         orientation=NS(x=0, y=0, z=0, w=1))))
            sink.add(msg, 4.5, 900.25)
            sink.add(msg, 1.0, 901.0)
            sink.close()
            rows = joiner.read(path)
            self.assertEqual(rows[1]['stamp_ns'], 3000000123)
            self.assertEqual(rows[1]['receipt_sim'], 4.5)
            self.assertEqual(rows[1]['receipt_wall'], 900.25)
            self.assertEqual(rows[2]['epoch'], 1)
            with self.assertRaises(FileExistsError):
                capture.GroundTruthCapture(path)

    def test_injected_error_and_null_control(self):
        for x in (1, 1.08):
            data = events()
            data[1]['pose'][0] = x
            data[1]['tf'][0] = x
            rows = joiner.join(data, [gt(10, 0), gt(20, 1, 2)], [0, 0, 0, 0, 0, 0, 1], 20)
            self.assertEqual(rows[0]['status'], 'paired')
            self.assertAlmostEqual(rows[0]['residual'][0], x-1)

    def test_missing_anchor_tf_and_prediction_end(self):
        for mutate in ('anchor', 'tf', 'end', 'duplicate', 'timestamp'):
            data = events()
            if mutate == 'anchor':
                data[1]['anchor_id'] = 99
            elif mutate == 'tf':
                data[1]['tf_ok'] = 0
            elif mutate == 'end':
                data.pop()
            elif mutate == 'duplicate':
                data.append(copy.deepcopy(data[1]))
            else:
                data[1]['tf_ns'] = 25
            if mutate == 'duplicate':
                with self.assertRaises(ValueError):
                    joiner.join(data, [gt(10, 0), gt(20, 1, 2)], [0, 0, 0, 0, 0, 0, 1], 20)
            else:
                rows = joiner.join(data, [gt(10, 0), gt(20, 1, 2)], [0, 0, 0, 0, 0, 0, 1], 20)
                self.assertEqual(rows[-1]['status'], 'unobservable')

    def test_gt_no_extrapolation_or_epoch_crossing(self):
        for stamp, epoch, gap in ((5, 0, 20), (15, 1, 20), (15, 0, 1)):
            with self.assertRaises(ValueError):
                joiner.gt_at([gt(10, 0), gt(20, 1, 2)], stamp, epoch, gap,
                             [0, 0, 0, 0, 0, 0, 1])

    def test_interpolation_and_wrap(self):
        a = [0, 0, 0, 0, 0, math.sin(1.55), math.cos(1.55)]
        b = [2, 0, 0, 0, 0, math.sin(-1.55), math.cos(-1.55)]
        p = joiner.interpolate(a, b, .5)
        self.assertAlmostEqual(p[0], 1)
        yaw = joiner.base_pose(p, [0, 0, 0, 0, 0, 0, 1])[2]
        self.assertAlmostEqual(abs(yaw), math.pi)
        self.assertAlmostEqual(joiner.relative([0, 0, 3.1], [0, 0, -3.1])[2], 2*math.pi-6.2)

    def test_capture_loss_and_missing_footer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data'
            for rows in ([dict(stage='manifest', schema=1)],
                         [dict(stage='manifest', schema=1),
                          dict(stage='footer', schema=1, dropped=1, write_failed=False)]):
                path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.assertRaises(ValueError):
                    joiner.read(path)

    def test_legacy_trace_and_default_constructor_unchanged(self):
        path = 'gazebo_models/scripts/nav_bench.py'
        old = ast.parse(subprocess.check_output(['git', 'show', 'eff6dd5:'+path], cwd=ROOT))
        new = ast.parse((ROOT / path).read_text())

        def function(tree, name):
            return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
        self.assertEqual(ast.dump(function(old, 'write_trace')), ast.dump(function(new, 'write_trace')))
        cls = next(n for n in new.body if isinstance(n, ast.ClassDef) and n.name == 'NavBench')
        self.assertEqual(function(cls, '__init__').args.defaults[0].value, None)
        series = next(n for n in new.body if isinstance(n, ast.ClassDef) and n.name == 'Series')
        self.assertEqual(len(function(series, '__init__').args.args), 1)

    def test_prepare_rejects_bad_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'bad'
            archive.write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                prepare.prepare(archive, Path(tmp) / 'output')
            self.assertFalse((Path(tmp) / 'output').exists())

    def test_cpp_event_contract_and_overflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'contract'
            subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic',
                            '-Werror', '-pthread', str(HERE / 'contract.cpp'),
                            str(HERE / 'capture.cpp'), '-o', str(exe)], check=True)
            env = dict(os.environ)
            env.pop('C2NAV35_TRACE', None)
            result = subprocess.run([str(exe)], env=env, capture_output=True, check=True)
            self.assertEqual(result.stdout + result.stderr, b'')
            self.assertEqual(list(Path(tmp).iterdir()), [exe])
            path = Path(tmp) / 'trace'
            env['C2NAV35_TRACE'] = str(path)
            subprocess.run([str(exe)], env=env, check=True)
            rows = joiner.read(path)
            failure = next(r for r in rows if r.get('stage') == 'tf_failure')
            self.assertIsNone(failure['tf_ns'])
            self.assertEqual(failure['tf'], [None]*7)
            self.assertEqual(failure['scan_ns'], 1000000007)
            self.assertEqual(failure['scan_frame'], 'scan"\\\n')
            eligibility = next(r for r in rows if r.get('stage') == 'eligibility')
            self.assertEqual(eligibility['anchor_id'], 2)
            self.assertEqual(eligibility['anchor_ns'], 1000000017)
            self.assertEqual(eligibility['eligible'], 0)
            self.assertFalse(any(r.get('stage') == 'anchor_set' and r['scan_id'] == 3
                                 for r in rows))
            env['C2NAV35_TRACE'] = str(Path(tmp) / 'overflow')
            subprocess.run([str(exe), 'overflow'], env=env, check=True)
            overflow = [json.loads(line) for line in Path(env['C2NAV35_TRACE']).read_text().splitlines()]
            self.assertGreater(overflow[-1]['dropped'], 0)
            with self.assertRaises(ValueError):
                joiner.read(env['C2NAV35_TRACE'])

    def test_off_library_has_no_diagnostic_symbols(self):
        binary = ROOT / os.environ.get('C2NAV35_BUILD_ROOT', '.navbench/c2nav35') / 'build-disabled/libamcl_core.so'
        symbols = subprocess.check_output(['nm', '-D', '-C', str(binary)], text=True)
        self.assertNotIn('c2nav35', symbols)

    def test_source_off_is_upstream_and_public_header_unchanged(self):
        root = ROOT / os.environ.get('C2NAV35_BUILD_ROOT', '.navbench/c2nav35') / 'prepared/src/nav2_amcl'
        archive = ROOT / '.navbench/c2nav35/navigation2-1.3.11.tar.gz'
        with tarfile.open(archive) as tar:
            originals = {name: tar.extractfile('navigation2-1.3.11/nav2_amcl/'+name).read()
                         for name in ('src/amcl_node.cpp',
                                      'src/motion_model/differential_motion_model.cpp',
                                      'include/nav2_amcl/amcl_node.hpp')}
        # Strip only our explicit conditional blocks, preserving all upstream text.

        def disabled(text):
            out, inside, keep = [], False, True
            for line in text.splitlines():
                if line == '#ifdef C2NAV35_CAPTURE':
                    inside, keep = True, False
                elif inside and line == '#else':
                    keep = True
                elif inside and line == '#endif':
                    inside, keep = False, True
                elif keep:
                    out.append(line)
            return ''.join(''.join(out).split())
        for name in ('src/amcl_node.cpp', 'src/motion_model/differential_motion_model.cpp'):
            self.assertEqual(disabled((root / name).read_text()),
                             disabled(originals[name].decode()))
        header = 'include/nav2_amcl/amcl_node.hpp'
        self.assertEqual((root / header).read_bytes(), originals[header])

    def test_real_library_equivalence(self):
        # Required build artifacts: fail visibly instead of silently skipping.
        scratch = ROOT / os.environ.get('C2NAV35_BUILD_ROOT', '.navbench/c2nav35')
        on = scratch / 'build-enabled'
        off = scratch / 'build-disabled'
        source = scratch / 'prepared/src/nav2_amcl'
        ros = Path('/opt/ros/jazzy')
        includes = ['-I'+str(ros / 'include')]
        includes += ['-I'+str(p) for p in (ros / 'include').iterdir() if p.is_dir()]
        env = dict(os.environ)
        env.pop('C2NAV35_TRACE', None)
        outputs = []
        with tempfile.TemporaryDirectory() as tmp:
            for tag, build in [('installed', ros / 'lib'), ('off', off), ('on', on)]:
                paths = [build, build / 'src/motion_model', build / 'src/pf',
                         ros / 'lib', ros / 'lib/x86_64-linux-gnu']
                env['LD_LIBRARY_PATH'] = ':'.join(map(str, paths))
                exe = Path(tmp) / tag
                command = ['g++', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic', '-Werror',
                           str(HERE / 'probe.cpp'), '-o', str(exe)]
                if tag == 'on':
                    command += ['-DC2NAV35_CAPTURE', '-I'+str(source / 'include')]
                command += includes + ['-L'+str(p) for p in paths]
                command += ['-lmotions_lib', '-lpf_lib']
                if tag == 'on':
                    command += ['-lc2nav35_capture']
                result = subprocess.run(command, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                if tag != 'on':
                    env['C2NAV35_TRACE'] = str(Path(tmp) / 'must-not-exist')
                else:
                    env.pop('C2NAV35_TRACE', None)
                outputs.append(subprocess.check_output([str(exe)], env=env))
                self.assertFalse((Path(tmp) / 'must-not-exist').exists())
                if tag == 'on':
                    env['C2NAV35_TRACE'] = str(Path(tmp) / 'amcl.jsonl')
                    outputs.append(subprocess.check_output([str(exe)], env=env))
                    rows = joiner.read(env['C2NAV35_TRACE'])
                    manifest = json.loads((scratch / 'prepared/source_manifest.json').read_text())
                    self.assertEqual(rows[0]['instrumentation_sha256'],
                                     manifest['instrumentation_sha256'])
                    motions = [r for r in rows if r.get('stage') == 'motion_decomposition']
                    self.assertEqual(len(motions), 4)
                    self.assertEqual(motions[0]['scan_ns'], 1000000001)
                    self.assertEqual(motions[0]['motion'], [0, 0, .3])
                    self.assertEqual(motions[1]['motion'], [0, 1, 0])
                    self.assertAlmostEqual(abs(motions[2]['motion'][0]), math.pi)
            self.assertTrue(all(output == outputs[0] for output in outputs))


if __name__ == '__main__':
    unittest.main(verbosity=2)
