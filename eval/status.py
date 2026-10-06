#!/usr/bin/env python3
"""Resolve the true current SHA and clean state beside committed STATUS.md."""
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()


if __name__ == '__main__':
    print('Current SHA: ' + git('rev-parse', 'HEAD'))
    print('Branch: ' + git('branch', '--show-current'))
    print('Worktree clean: ' + ('y' if not git('status', '--porcelain=v1') else 'n'))
    print('\n' + (REPO / 'docs/STATUS.md').read_text())
