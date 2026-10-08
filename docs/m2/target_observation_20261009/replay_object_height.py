import json,numpy as np,cv2
from pathlib import Path
from coco_perception.object_height import estimate_object_height
from coco_perception.target_finder import colour_mask
p=Path('/home/gautham/coco_m1_runs/rgbd-light-20261009/acquisition-02-inspection')
s=json.loads((p/'sensor_inspection.json').read_text())
# Chain decoded from actual /tf_static, not mount constants/world state.
from scipy.spatial.transform import Rotation
records=json.loads((p/'sensor_tf.json').read_text())
transforms={'base_footprint':np.eye(4)}
pending=[t for r in records for t in r['data']['transforms']]
while pending:
    progress=False
    for item in pending[:]:
        parent=item['header']['frame_id'];child=item['child_frame_id']
        if parent not in transforms:continue
        tf=item['transform'];q=tf['rotation'];m=np.eye(4)
        m[:3,:3]=Rotation.from_quat([q[k] for k in ('x','y','z','w')]).as_matrix()
        m[:3,3]=[tf['translation'][k] for k in ('x','y','z')]
        transforms[child]=transforms[parent]@m;pending.remove(item);progress=True
    if not progress:break
T=transforms['camera_optical_frame'];out=[]
for index,f in enumerate(s['frames']):
    rgb=cv2.imread(str(p/f'rgb-{index:03d}.png'));depth=np.load(p/f'depth-{index:03d}.npy')
    mask=colour_mask(cv2.cvtColor(rgb,cv2.COLOR_BGR2HSV),'red')>0
    o=estimate_object_height(mask,depth,np.array(f['camera_info']['k']).reshape(3,3),T,stamp_ns=f['rgb_stamp_ns'],depth_stamp_ns=f['depth_stamp_ns'],now_ns=f['rgb_stamp_ns'],colour='red',source_frame=f['frame'],depth_frame=f['depth_frame'],track_id='replay-single-red',reference_id='replay-support')
    out.append(o);print(index,o['reason'],o.get('center_height_above_support_m'),o.get('uncertainty_m'))
Path('/home/gautham/coco_m1_runs/rgbd-light-20261009/acquisition-02-measurements.json').write_text(json.dumps(out,indent=2,allow_nan=False))
