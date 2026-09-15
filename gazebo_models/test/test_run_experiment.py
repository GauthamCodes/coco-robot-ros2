"""Regression coverage for missing telemetry and failed experiment commands."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run_experiment.py'
spec = importlib.util.spec_from_file_location('experiment', SCRIPT)
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


def test_missing_telemetry_is_not_zero():
    data = experiment.metrics([{'status': 'SUCCEEDED', 'n_stops': 3}])
    assert data['safety_stop_count'] is None
    assert data['physical_stop_count'] == 3
    assert data['minimum_clearance_m'] is None
    assert experiment.metrics([])['success_rate'] is None


def test_failure_leaves_machine_readable_outcome(tmp_path):
    params = tmp_path / 'params.yaml'
    params.write_text('test: true\n')
    report = tmp_path / 'report.json'
    result = subprocess.run([sys.executable, '-P', str(SCRIPT), '--run-id', 'failure',
                             '--params', str(params), '--output', str(report),
                             '--result', str(tmp_path / 'missing.json'), '--',
                             sys.executable, '-c', 'raise SystemExit(7)'], timeout=20)
    assert result.returncode == 1
    data = json.loads(report.read_text())
    assert data['returncode'] == 7
    assert data['status'] == 'failed'
    assert not data['success']
    assert not data['metrics']['navigation_complete']
