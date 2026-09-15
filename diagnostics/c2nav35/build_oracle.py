#!/usr/bin/env python3
"""Build the deterministic probe against installed AMCL; save binary provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    ros = Path('/opt/ros/jazzy')
    source = Path(__file__).with_name('motion_oracle.cpp').resolve()
    includes = ['-I'+str(ros/'include')]
    includes += ['-I'+str(p) for p in sorted((ros/'include').iterdir()) if p.is_dir()]
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic', '-Werror',
                    str(source), '-o', str(args.output), *includes, '-L'+str(ros/'lib'),
                    '-Wl,-rpath,'+str(ros/'lib'), '-lmotions_lib', '-lpf_lib'], check=True)
    paths = [source, args.output, ros/'lib/libmotions_lib.so', ros/'lib/libpf_lib.so']
    manifest = dict(files={str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in paths}, installed_version=subprocess.check_output(
                               ['dpkg-query', '-W', 'ros-jazzy-nav2-amcl'], text=True).strip())
    args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
