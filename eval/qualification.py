"""Read-only host inventory and fail-closed qualification. Never starts a simulator."""
import json
import math
import os
from pathlib import Path
import subprocess
import time

POLICY = Path(__file__).with_name('host_policy.json')


def identity(pid, proc=Path('/proc')):
    p = proc / str(pid)
    fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': int(pid), 'start_ticks': int(fields[19]),
            'pgid': int(fields[2]), 'state': fields[0]}


def robotics_process(argv, comm, exe, maps=''):
    # gz overwrites argv[0]; /proc/comm may still say ruby. Inspect both.
    head = ' '.join(argv[:3]).lower()
    return (comm.lower() in ('gz', 'gazebo', 'gzserver', 'gzclient', 'rviz2', 'ros2')
            or any(x in head for x in ('gz sim', 'gazebo', 'isaacsim', 'isaac-sim',
                                      'coco_sim.isaac.runtime', 'omni.kit'))
            or any(Path(a).name == 'ros2' for a in argv[:2])
            or '--ros-args' in argv
            or any(a.startswith('/opt/ros/') for a in argv[:2])
            or '/opt/ros/' in exe or 'librcl.' in maps or 'librclpy' in maps)


def inventory(proc=Path('/proc'), shm=Path('/dev/shm')):
    errors, processes = [], []
    for p in proc.iterdir():
        if not p.name.isdigit():
            continue
        try:
            item = identity(int(p.name), proc)
            if item['state'] == 'Z':
                continue
            item['argv'] = [s.decode(errors='replace') for s in
                            (p / 'cmdline').read_bytes().split(b'\0') if s]
            item['comm'] = (p / 'comm').read_text().strip()
            item['exe'] = os.readlink(p / 'exe')
            maps = (p / 'maps').read_text()
            item['robotics'] = robotics_process(item['argv'], item['comm'], item['exe'], maps)
            processes.append(item)
        except FileNotFoundError:
            continue  # process exited during inventory
        except (OSError, ValueError, IndexError) as exc:
            errors.append(f'{p}: {exc}')
    mem = {}
    for line in (proc / 'meminfo').read_text().splitlines():
        k, v = line.split(':', 1)
        mem[k] = int(v.split()[0]) * 1024
    gpu = None
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=uuid,memory.total,memory.free',
                                 '--format=csv,noheader,nounits'],
                                capture_output=True, text=True, timeout=5, check=True)
        lines = result.stdout.strip().splitlines()
        if len(lines) != 1:
            raise ValueError('expected the single committed laptop GPU')
        uuid, total, free = [s.strip() for s in lines[0].split(',')]
        gpu = {'uuid': uuid, 'total_bytes': int(total)*2**20, 'free_bytes': int(free)*2**20}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        errors.append(f'GPU inventory unavailable: {exc}')
    # A segment is allowed only if explicitly registered as owned by the runner.
    # Unknown DDS SHM is blocked, even when orphan ownership cannot be established.
    segments = [{'name': p.name, 'bytes': p.stat().st_size} for p in shm.iterdir()
                if any(k in p.name.lower() for k in ('dds', 'fast', 'cyclone', 'iceoryx'))]
    cpu = [int(v) for v in (proc / 'stat').read_text().splitlines()[0].split()[1:9]]
    return {'wall_epoch_ns': time.time_ns(), 'monotonic_s': time.monotonic(),
            'cpu_ticks': cpu, 'cpu_count': len(os.sched_getaffinity(0)),
            'load1': os.getloadavg()[0], 'ram_available_bytes': mem['MemAvailable'],
            'ram_total_bytes': mem['MemTotal'], 'gpu': gpu,
            'processes': processes, 'dds_segments': segments, 'errors': errors}


def qualify(snapshot, policy, backend, phase='preflight', owned=(), owned_shm=()):
    reasons = list(snapshot.get('errors', []))
    allowed = {(i['pid'], i['start_ticks']) for i in owned}
    for p in snapshot['processes']:
        if p['robotics'] and (p['pid'], p['start_ticks']) not in allowed:
            reasons.append(f"foreign robotics process pid={p['pid']} start={p['start_ticks']} argv={p['argv']}")
    for s in snapshot['dds_segments']:
        if s['name'] not in owned_shm:
            reasons.append(f"unowned/orphan DDS segment: {s['name']}")
    limits = policy['backends'][backend][phase]
    # Null is not disabled: it is an explicit calibration blocker.
    values = {'max_load1': snapshot['load1'], 'min_ram_available_bytes': snapshot['ram_available_bytes'],
              'min_vram_free_bytes': (snapshot['gpu'] or {}).get('free_bytes')}
    for key, value in values.items():
        limit = limits.get(key)
        if limit is None:
            reasons.append(f'{backend}/{phase}: uncalibrated requirement {key}')
        elif not isinstance(value, (int, float)) or not math.isfinite(value):
            reasons.append(f'{key}: metric unavailable/non-finite')
        elif (value > limit if key.startswith('max_') else value < limit):
            reasons.append(f'{key}: observed {value}, required {limit}')
    return {'qualified': not reasons, 'reasons': reasons, 'backend': backend, 'phase': phase}


def cpu_percent(previous, current):
    delta = [b-a for a, b in zip(previous['cpu_ticks'], current['cpu_ticks'])]
    total = sum(delta)
    return 100*(1-(delta[3]+delta[4])/total) if total > 0 else None


def load_policy():
    return json.loads(POLICY.read_text())
