"""Real engineering recorder/image CDR test; simulator-free, NON_QUALIFYING."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from replay import mcap_events


def test_live_engineering_image_sidecar_uses_hash_not_pixels(tmp_path):
    import rclpy
    from rclpy.context import Context
    from sensor_msgs.msg import Image
    (tmp_path/'logs').mkdir()
    with (tmp_path/'logs/recorder.log').open('w') as log:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'bootstrap_recorder.py'),str(tmp_path)],
            env=dict(os.environ,ROS_DOMAIN_ID='189'),stdout=log,stderr=subprocess.STDOUT)
        context=Context();rclpy.init(context=context,domain_id=189)
        node=rclpy.create_node('image_fixture',namespace='/eval',context=context)
        pub=node.create_publisher(Image,'/camera/image_raw',10)
        try:
            deadline=time.monotonic()+10
            while time.monotonic()<deadline and not pub.get_subscription_count():
                assert process.poll() is None;time.sleep(.1)
            assert pub.get_subscription_count()
            msg=Image(height=2,width=2,encoding='rgb8',step=6,data=bytes(range(12)))
            msg.header.stamp.sec=3
            for _ in range(12):pub.publish(msg);time.sleep(.1)
        finally:
            if process.poll() is None:process.send_signal(signal.SIGINT)
            process.wait(timeout=10);node.destroy_node();rclpy.shutdown(context=context)
    assert process.returncode==0
    events,proof=mcap_events(tmp_path)
    images=[e for e in events if e['topic']=='/camera/image_raw']
    assert images and 'data' not in images[0]['data']
    assert images[0]['data']['raw_image_bytes']==12
    # Corrupt a retained byte hash: raw MCAP must catch it.
    rows=[json.loads(line) for line in (tmp_path/'logs/events.jsonl').read_text().splitlines()]
    next(e for e in rows if e['topic']=='/camera/image_raw')['data']['raw_image_sha256']='bad'
    (tmp_path/'logs/events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in rows))
    with pytest.raises(ValueError,match='payload mismatch'):mcap_events(tmp_path)
