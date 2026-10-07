"""Native executor trace probe on owned synthetic C++ ROS nodes, no simulator."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from tracing import availability,TraceSession,inspect
from process_groups import stop
from qualification import identity


def test_native_executor_trace_with_pid_thread_context(tmp_path):
    status=availability()
    if not status['available']:pytest.skip('Native ROS UST provider unavailable')
    trace=TraceSession(tmp_path/'ctf');children=[];handles=[];identities=[]
    try:
        assert trace.start(),trace.commands
        for name in ('talker','listener'):
            handle=(tmp_path/(name+'.log')).open('x');handles.append(handle)
            children.append((name,subprocess.Popen(['/opt/ros/jazzy/lib/demo_nodes_cpp/'+name],
                env=dict(os.environ,ROS_DOMAIN_ID='184'),stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)))
            identities.append(identity(children[-1][1].pid))
        (tmp_path/'owned_processes.json').write_text(json.dumps(identities,indent=2))
        time.sleep(3.5)
    finally:
        for name,child in reversed(children):stop(name,child)
        for handle in handles:handle.close()
        (tmp_path/'session.json').write_text(json.dumps(trace.close(),indent=2))
    result=inspect(tmp_path/'ctf',owned_pids=[p['pid'] for p in identities])
    result['evidence_scope']='synthetic native C++ ROS only; no qualified mission or simulator'
    (tmp_path/'inspection.json').write_text(json.dumps(result,indent=2))
    assert result['executor_timing_verified'],result
    assert result['unmatched_callback_starts']==0
    assert all(s['wall_duration_ns']>=0 for s in result['callback_spans'])
