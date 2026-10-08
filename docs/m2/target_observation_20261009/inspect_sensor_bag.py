#!/usr/bin/env python3
"""Offline inspection of legitimate sensor records only; no /eval/world inputs."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
import cv2
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
from rosidl_runtime_py.convert import message_to_ordereddict

REPO=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO/'coco_perception'),str(REPO/'coco_config')]
from coco_perception.target_finder import colour_mask, STAMP_TOLERANCE


def stamp(msg):
    return msg.header.stamp.sec*10**9+msg.header.stamp.nanosec


def nonfinite(value,path=''):
    if isinstance(value,float) and not math.isfinite(value):return [dict(path=path,value=str(value))]
    if isinstance(value,dict):return [p for k,v in value.items() for p in nonfinite(v,path+'/'+str(k))]
    if isinstance(value,(list,tuple)):return [p for i,v in enumerate(value) for p in nonfinite(v,path+'/'+str(i))]
    return []


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();args.output.mkdir(exist_ok=False)
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(args.run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    kinds={t.name:get_message(t.type) for t in reader.get_all_topics_and_types()}
    counts=Counter();images=[];depths=[];infos=[];transforms=[];invalid=[]
    while reader.has_next():
        topic,raw,receipt=reader.read_next();counts[topic]+=1
        # Privileged state is neither read nor used for sensor inference.
        if topic.startswith('/eval/'):continue
        msg=deserialize_message(raw,kinds[topic])
        if topic=='/camera/image_raw':
            if msg.encoding not in ('rgb8','bgr8'):raise ValueError(msg.encoding)
            data=np.array(msg.data,dtype=np.uint8).reshape(msg.height,msg.step)[:,:msg.width*3].reshape(msg.height,msg.width,3)
            if msg.encoding=='rgb8':data=cv2.cvtColor(data,cv2.COLOR_RGB2BGR)
            images.append((stamp(msg),msg.header.frame_id,data))
        elif topic=='/camera/depth/image_raw':
            dtype=np.dtype('>f4' if msg.is_bigendian else '<f4') if msg.encoding=='32FC1' else np.dtype('>u2' if msg.is_bigendian else '<u2')
            if msg.encoding not in ('32FC1','16UC1'):raise ValueError(msg.encoding)
            data=np.frombuffer(bytes(msg.data),dtype=dtype).reshape(msg.height,msg.step//dtype.itemsize)[:,:msg.width].astype(float)
            if msg.encoding=='16UC1':data/=1000
            depths.append((stamp(msg),msg.header.frame_id,data))
        elif topic=='/camera/camera_info':
            infos.append(dict(stamp_ns=stamp(msg),frame=msg.header.frame_id,width=msg.width,height=msg.height,k=list(msg.k)))
        elif topic in ('/tf','/tf_static'):
            transforms.append(dict(topic=topic,receipt_ns=receipt,data=message_to_ordereddict(msg)))
        else:
            bad=nonfinite(message_to_ordereddict(msg))
            if bad:invalid.append(dict(topic=topic,receipt_ns=receipt,fields=bad))
    results=[]
    for index,(rgb_stamp,frame,rgb) in enumerate(images):
        cv2.imwrite(str(args.output/f'rgb-{index:03d}.png'),rgb)
        if not depths:continue
        d_stamp,d_frame,depth=min(depths,key=lambda item:abs(item[0]-rgb_stamp))
        np.save(args.output/f'depth-{index:03d}.npy',depth)
        valid=np.isfinite(depth)&(depth>=.15)&(depth<=8.)
        display=np.where(np.isfinite(depth),np.clip(depth,0,8),0)/8*255
        cv2.imwrite(str(args.output/f'depth-{index:03d}.png'),cv2.applyColorMap(display.astype(np.uint8),cv2.COLORMAP_TURBO))
        cv2.imwrite(str(args.output/f'valid-depth-{index:03d}.png'),valid.astype(np.uint8)*255)
        masks={}
        for colour in ('red','green','blue','yellow'):
            mask=colour_mask(cv2.cvtColor(rgb,cv2.COLOR_BGR2HSV),colour)>0
            points=np.argwhere(mask);values=depth[mask];usable=values[np.isfinite(values)&(values>=.15)&(values<=2.)]
            bbox=None if len(points)==0 else [int(points[:,1].min()),int(points[:,0].min()),int(points[:,1].max()),int(points[:,0].max())]
            masks[colour]=dict(mask_pixels=int(mask.sum()),bbox_xyxy_px=bbox,
                accepted_depth_points=len(usable),valid_fraction=float(len(usable)/len(values)) if len(values) else None,
                median_depth_m=float(np.median(usable)) if len(usable) else None,
                near_plane_points=int(np.sum(np.isfinite(values)&(values<.1))),
                below_acquisition_min_points=int(np.sum(np.isfinite(values)&(values<.15))),
                physical_identity_verified=False,physical_geometry_available=False)
        info=min(infos,key=lambda value:abs(value['stamp_ns']-rgb_stamp)) if infos else None
        results.append(dict(rgb_stamp_ns=rgb_stamp,depth_stamp_ns=d_stamp,skew_ns=abs(rgb_stamp-d_stamp),
            pairing_valid=abs(rgb_stamp-d_stamp)<=STAMP_TOLERANCE*1e9 and frame==d_frame,
            frame=frame,depth_frame=d_frame,camera_info=info,finite_depth_fraction=float(np.isfinite(depth).mean()),
            sensor_valid_depth_fraction=float(valid.mean()),colour_regions=masks,
            required_phase='STARTUP_ONLY; manipulation phases not reached',geometry_reason='NO_ASSOCIATED_TARGET_GEOMETRY'))
    (args.output/'sensor_inspection.json').write_text(json.dumps(dict(
        execution_class='NON_QUALIFYING',qualified=False,topic_counts=dict(counts),frames=results,
        nonfinite_message_fields=invalid,ground_truth_inputs_used=False,
        limitation='Startup-only aborted run; colour masks do not certify physical identity or mandatory phase visibility'),indent=2,allow_nan=False)+'\n')
    (args.output/'sensor_tf.json').write_text(json.dumps(transforms,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(rgb_frames=len(images),depth_frames=len(depths),camera_info=len(infos),nonfinite_messages=len(invalid),topic_counts=dict(counts)),indent=2))

if __name__=='__main__':main()
