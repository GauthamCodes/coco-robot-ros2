#!/usr/bin/env python3
"""Read-only Gazebo transport -> /eval truth. No simulator launch or commands."""
import argparse
import json
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time
from truth import TruthPublisher, gazebo_packet


def main():
    import rclpy
    from std_msgs.msg import String
    parser=argparse.ArgumentParser()
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--world',default='coco_world')
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text())
    dimensions={t['model']:[t['diameter'],t['diameter'],t['height']] for t in manifest['targets']}
    rclpy.init(); node=rclpy.create_node('gazebo_truth',namespace='/eval')
    pub=TruthPublisher(node,dimensions); attached={}; subscriptions=[]
    for name in dimensions:
        def state(msg,n=name):
            attached[n]=True if msg.data=='attached' else False if msg.data=='detached' else None
        from rclpy.qos import QoSProfile,DurabilityPolicy
        subscriptions.append(node.create_subscription(String,f'/magnet/{name}/state',state,
                             QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)))
    child=subprocess.Popen(['gz','topic','--json-output','-e','-t',f'/world/{args.world}/pose/info'],
                           stdout=subprocess.PIPE,text=True)
    packets=queue.Queue(maxsize=1); stop=threading.Event()
    def read():
        for line in child.stdout:
            try: value=json.loads(line)
            except ValueError: continue
            if stop.is_set(): break
            if packets.full():
                try: packets.get_nowait()
                except queue.Empty: pass
            packets.put_nowait(value)
    thread=threading.Thread(target=read,daemon=True);thread.start()
    def halt(*_):stop.set()
    signal.signal(signal.SIGINT,halt);signal.signal(signal.SIGTERM,halt)
    last=0
    try:
        while rclpy.ok() and not stop.is_set():
            rclpy.spin_once(node,timeout_sec=.1)
            if child.poll() is not None: raise RuntimeError('Gazebo truth transport exited')
            if time.monotonic()-last>=1:
                try: raw=packets.get_nowait()
                except queue.Empty: continue
                pub.publish(gazebo_packet(raw,dimensions,attached));last=time.monotonic()
    finally:
        if child.poll() is None:
            child.send_signal(signal.SIGINT)
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=5)
        node.destroy_node();rclpy.shutdown()

if __name__=='__main__':main()
