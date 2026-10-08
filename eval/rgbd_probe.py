#!/usr/bin/env python3
"""Read-only actual ROS CLI graph checks; fixture launch owns this child."""
import json
from pathlib import Path
import subprocess
import sys
import time
root=Path(sys.argv[1]);time.sleep(10)
results=[]
for argv in (
    ['ros2','node','list','--no-daemon'],
    ['ros2','node','info','/object_height_node','--no-daemon'],
    ['ros2','topic','list','--no-daemon'],
    ['ros2','topic','info','-v','/perception/object_height','--no-daemon']):
    try:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=8)
        results.append(dict(argv=argv,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
    except subprocess.TimeoutExpired as exc:
        results.append(dict(argv=argv,error='TIMEOUT'))
(root/'ros_cli_graph.json').write_text(json.dumps(results,indent=2))
