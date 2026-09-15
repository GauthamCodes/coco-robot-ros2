#!/usr/bin/env python3
"""Run one bounded foreground experiment and preserve a machine-readable outcome."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time


def utc():
    return datetime.now(timezone.utc).isoformat()


def metrics(legs):
    """Missing telemetry remains null; physical stalls are separate from safety stops."""
    def complete_sum(key):
        values = [r.get(key) for r in legs]
        return sum(values) if values and all(v is not None for v in values) else None

    clearances = [r.get('min_clearance_m') for r in legs]
    return dict(legs=len(legs),
                success_rate=sum(r.get('status') == 'SUCCEEDED' for r in legs)/len(legs)
                if legs else None,
                navigation_complete=bool(legs) and all(r.get('status') == 'SUCCEEDED'
                                                      for r in legs),
                observed_duration_sim_s=complete_sum('duration_sim_s'),
                completion_sim_s=complete_sum('duration_sim_s') if legs and
                all(r.get('status') == 'SUCCEEDED' for r in legs) else None,
                minimum_clearance_m=min(clearances) if clearances and
                all(v is not None for v in clearances) else None,
                safety_stop_count=complete_sum('safety_stop_count'),
                physical_stop_count=complete_sum('n_stops'),
                terminal_errors_m=[r.get('final_goal_err_m') for r in legs],
                zero_velocity=[dict(scenario=r.get('scenario'),
                                    command_below_005=r.get('frac_cmd_below_0.05'),
                                    actual_below_005=r.get('frac_actual_below_0.05'),
                                    dwb_zero_fraction=r.get('dwb_best_vx_zero_frac')) for r in legs])


def artifact(path):
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--params', type=Path, required=True)
    parser.add_argument('--result', type=Path, required=True, help='new nav_bench JSON path')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--diagnostic-result', type=Path, help='strict joiner output')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or not math.isfinite(args.timeout) or args.timeout <= 0 or args.result.exists():
        parser.error('command, positive timeout and a fresh result path required')
    record = dict(schema=1, run_id=args.run_id, started_utc=utc(), command=command,
                  git_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  git_status=subprocess.check_output(['git', 'status', '--porcelain'], text=True),
                  config=artifact(args.params), status='running',
                  environment={key: os.environ.get(key) for key in
                               ('RMW_IMPLEMENTATION', 'ROS_DOMAIN_ID', 'GZ_VERSION',
                                'AMENT_PREFIX_PATH', 'LD_LIBRARY_PATH', 'C2NAV35_TRACE')},
                  tracked_diff_sha256=hashlib.sha256(subprocess.check_output(
                      ['git', 'diff', 'HEAD', '--'])).hexdigest())
    # Exclusive creation reserves the ID and leaves evidence even after a hard crash.
    with args.output.open('x') as stream:
        json.dump(record, stream, indent=2)
    started = time.monotonic()
    process = None
    try:
        with args.output.with_suffix('.log').open('x') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            record['returncode'] = process.wait(timeout=args.timeout)
        record['status'] = 'finished' if record['returncode'] == 0 else 'failed'
    except subprocess.TimeoutExpired:
        record['status'] = 'timeout'
    except (OSError, KeyboardInterrupt) as error:
        record['status'], record['error'] = 'failed', str(error)
    finally:
        if process is not None:
            # Terminate the owned process group, including descendants after parent exit.
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        record.update(finished_utc=utc(), elapsed_wall_s=time.monotonic()-started)
        record['metrics'] = metrics([])
        if args.result.exists():
            try:
                record['metrics'] = metrics(json.loads(args.result.read_text())['legs'])
                record['result'] = artifact(args.result)
            except (ValueError, KeyError, TypeError) as error:
                record['status'], record['result_error'] = 'failed', str(error)
        record['diagnostic_integrity'] = 'not_recorded'
        if args.diagnostic_result:
            record['diagnostic_integrity'] = 'UNOBSERVABLE'
            if args.diagnostic_result.exists():
                try:
                    data = json.loads(args.diagnostic_result.read_text())
                    if (data.get('status') == 'OK' and data.get('predictions') and
                            all(r.get('status') == 'paired' for r in data['predictions'])):
                        record['diagnostic_integrity'] = 'OK'
                    record['diagnostic_result'] = artifact(args.diagnostic_result)
                except (ValueError, TypeError, KeyError) as error:
                    record['diagnostic_error'] = str(error)
        if args.baseline:
            try:
                data = json.loads(args.baseline.read_text())
                record['baseline'] = dict(artifact=artifact(args.baseline),
                                          metrics=metrics(data['legs']))
            except (OSError, ValueError, TypeError, KeyError) as error:
                record['baseline_error'] = str(error)
        record['success'] = (record['status'] == 'finished' and
                             record['metrics']['navigation_complete'])
        temporary = args.output.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2, allow_nan=False)+'\n')
        temporary.replace(args.output)
    return 0 if record['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
