#!/usr/bin/env python3
"""Read-only environment capture. Never imports Isaac or launches a simulator."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET


def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=30)
        return {'argv': args, 'returncode': p.returncode,
                'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'argv': args, 'unavailable': str(exc)}


def dds_config(value):
    if value.startswith('file://'):
        path = Path(value[7:])
    elif value and not value.lstrip().startswith('<'):
        path = Path(value)
    else:
        return {'value': value, 'kind': 'inline' if value else 'unset'}
    try:
        raw = path.read_bytes()
        return {'value': value, 'kind': 'file', 'content': raw.decode(),
                'sha256': hashlib.sha256(raw).hexdigest()}
    except OSError as exc:
        return {'value': value, 'kind': 'file', 'unavailable': str(exc)}


def capture(isaac_python):
    repo = Path(__file__).resolve().parents[1]
    packages = {}
    for prefix in os.environ.get('AMENT_PREFIX_PATH', '').split(':'):
        if not prefix:
            continue
        for name in ('nav2_bringup', 'nav2_controller', 'rclpy', 'rmw_cyclonedds_cpp'):
            path = Path(prefix) / 'share' / name / 'package.xml'
            if name not in packages and path.exists():
                packages[name] = {'version': ET.parse(path).getroot().findtext('version'),
                                  'package_xml': str(path)}
    metadata = "import importlib.metadata as m,json; print(json.dumps({d.metadata['Name']:d.version for d in m.distributions() if d.metadata['Name'].lower().startswith(('isaacsim','omni'))},sort_keys=True))"
    return {
        'schema_version': 1,
        'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'repo_head': command(['git', '-C', str(repo), 'rev-parse', 'HEAD']),
        'os_release': Path('/etc/os-release').read_text(),
        'kernel': platform.release(), 'python': sys.version,
        'ros_distro': os.environ.get('ROS_DISTRO', 'UNSET'),
        'ros_packages': packages,
        'apt_versions': command(['dpkg-query', '-W', '-f=${Package}\t${Version}\n',
                                 'ros-*', '*gz*', '*gazebo*', '*nvidia*']),
        'gazebo': command(['gz', 'sim', '--versions']),
        'nvidia_gpu_driver_vram': command(['nvidia-smi',
            '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader']),
        'python_lock': command([sys.executable, '-m', 'pip', 'freeze', '--all']),
        'isaac_python': str(isaac_python),
        'isaac_versions': command([str(isaac_python), '-c', metadata]),
        'isaac_python_lock': command([str(isaac_python), '-m', 'pip', 'freeze', '--all']),
        'rmw': os.environ.get('RMW_IMPLEMENTATION', 'UNSET (ROS default unresolved)'),
        'dds': {key: dds_config(os.environ.get(key, '')) for key in
                ('CYCLONEDDS_URI', 'FASTRTPS_DEFAULT_PROFILES_FILE', 'FASTDDS_DEFAULT_PROFILES_FILE')},
        'ros_domain_id': os.environ.get('ROS_DOMAIN_ID', 'UNSET'),
        'prefixes': {key: os.environ.get(key, '') for key in
                     ('AMENT_PREFIX_PATH', 'COLCON_PREFIX_PATH', 'COCO_WS', 'COCO_MOVEIT_PREFIX')},
        'qualification': 'NOT QUALIFIED: environment inventory only; M1 preflight is separate',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--isaac-python', type=Path,
                        default=Path.home() / 'isaac-sim/venv/bin/python')
    args = parser.parse_args()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    # Exclusive creation preserves evidence. Every run uses its own directory.
    with (args.run_dir / 'env.json').open('x') as f:
        json.dump(capture(args.isaac_python), f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
