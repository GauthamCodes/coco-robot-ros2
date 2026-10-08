"""Simulator-free real ROS CDR/MCAP NaN preservation and sidecar replay."""
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from evidence import ros_json_data
from replay import mcap_events


def test_joint_effort_nan_round_trips_real_mcap(tmp_path):
    import rosbag2_py
    from rclpy.serialization import serialize_message,deserialize_message
    from rosidl_runtime_py.convert import message_to_ordereddict
    from sensor_msgs.msg import JointState
    source=JointState();source.header.stamp.sec=2;source.header.stamp.nanosec=123
    source.name=['joint'];source.position=[.2];source.velocity=[0.]
    source.effort=[float('nan')]
    raw=serialize_message(source)
    assert math.isnan(deserialize_message(raw,JointState).effort[0])
    writer=rosbag2_py.SequentialWriter()
    writer.open(rosbag2_py.StorageOptions(uri=str(tmp_path/'bag'),storage_id='mcap'),
                rosbag2_py.ConverterOptions('',''))
    topic='/joint_states';receipt=3_000_000_000
    writer.create_topic(rosbag2_py.TopicMetadata(id=0,name=topic,type='sensor_msgs/msg/JointState',serialization_format='cdr'))
    writer.write(topic,raw,receipt)
    del writer
    (tmp_path/'logs').mkdir()
    event=dict(topic=topic,sim_s=receipt/1e9,wall_s=1.,wall_epoch_ns=receipt,
               data=ros_json_data(message_to_ordereddict(source)))
    (tmp_path/'logs/events.jsonl').write_text(json.dumps(event,allow_nan=False)+'\n')
    events,proof=mcap_events(tmp_path)
    assert events[0]['data']['effort']==[{'$ros_nonfinite_float':'NaN'}]
    assert events[0]['data']['header']['stamp']==dict(sec=2,nanosec=123)
    assert proof['records']==1 and proof['source_headers']==1
    # Tagged NaN cannot be confused with a finite reading in strict validation.
    event['data']['effort']=[0.]
    (tmp_path/'logs/events.jsonl').write_text(json.dumps(event)+'\n')
    import pytest
    with pytest.raises(ValueError,match='payload mismatch'):
        mcap_events(tmp_path)
