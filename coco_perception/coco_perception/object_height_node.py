"""Autonomy RGB-D observation publisher. No world/evaluator input endpoints."""
import json
from collections import OrderedDict
import cv2
import numpy as np
import rclpy
from rclpy.time import Time
from rclpy.qos import qos_profile_sensor_data
from cv_bridge import CvBridge
from sensor_msgs.msg import Image,CameraInfo
from std_msgs.msg import String
from tf2_ros import Buffer,TransformListener
from scipy.spatial.transform import Rotation
from coco_config.ros_boundary import AutonomyNode
from .object_height import invalid,estimate_object_height,MAX_AGE_S
from .target_finder import colour_mask,MIN_BLOB_PX


def stamp(msg):return msg.header.stamp.sec*10**9+msg.header.stamp.nanosec


class ObjectHeightNode(AutonomyNode):
    def __init__(self):
        super().__init__('object_height_node')
        self.declare_parameter('target_colour','red');self.colour=self.get_parameter('target_colour').value
        self.bridge=CvBridge();self.depths=OrderedDict();self.images=OrderedDict();self.info=None
        self.tf=Buffer();self.listener=TransformListener(self.tf,self)
        self.track=0;self.previous=None;self.reference=0;self.last_stamp=0
        self.pub=self.create_publisher(String,'/perception/object_height',10)
        self.create_subscription(CameraInfo,'/camera/camera_info',self._info,qos_profile_sensor_data)
        self.create_subscription(Image,'/camera/depth/image_raw',self._depth,qos_profile_sensor_data)
        self.create_subscription(Image,'/camera/image_raw',self._image,qos_profile_sensor_data)
        self.create_subscription(String,'/mission/target_colour',self._colour,10)
        self.create_timer(.1,self._freshness)

    def _publish(self,o):self.pub.publish(String(data=json.dumps(o,allow_nan=False)))
    def _colour(self,msg):
        if msg.data!=self.colour:
            self.colour=msg.data;self.previous=None;self.track+=1;self.reference+=1
            self._publish(invalid('TARGET_CHANGED',colour=self.colour))
    def _info(self,msg):self.info=msg
    def _cache(self,cache,msg):
        cache[stamp(msg)]=msg
        while len(cache)>5:cache.popitem(last=False)
        self._try(stamp(msg))
    def _depth(self,msg):self._cache(self.depths,msg)
    def _image(self,msg):self._cache(self.images,msg)
    def _freshness(self):
        now=self.get_clock().now().nanoseconds
        if not self.last_stamp or (now-self.last_stamp)/1e9>MAX_AGE_S:
            self._publish(invalid('STALE_OR_UNAVAILABLE',stamp_ns=self.last_stamp,colour=self.colour))

    def _try(self,source_stamp):
        if source_stamp<=self.last_stamp:return
        if source_stamp not in self.images or source_stamp not in self.depths:return
        self.last_stamp=source_stamp
        rgb=self.images[source_stamp];depth=self.depths[source_stamp]
        def reject(reason):self._publish(invalid(reason,stamp_ns=source_stamp,depth_stamp_ns=stamp(depth),colour=self.colour))
        if self.info is None or self.info.header.frame_id!=rgb.header.frame_id:return reject('CAMERA_INFO_UNAVAILABLE')
        if self.info.width!=rgb.width or self.info.height!=rgb.height:return reject('CAMERA_INFO_MISMATCH')
        try:
            image=self.bridge.imgmsg_to_cv2(rgb,'bgr8')
            values=self.bridge.imgmsg_to_cv2(depth,'passthrough').astype(float)
            if depth.encoding=='16UC1':values/=1000
            elif depth.encoding!='32FC1':return reject('DEPTH_ENCODING')
            mask=colour_mask(cv2.cvtColor(image,cv2.COLOR_BGR2HSV),self.colour)
            n,labels,stats,_=cv2.connectedComponentsWithStats(mask)
            candidates=[i for i in range(1,n) if stats[i,cv2.CC_STAT_AREA]>=MIN_BLOB_PX]
            if len(candidates)!=1:return reject('TARGET_ABSENT_OR_AMBIGUOUS')
            tf=self.tf.lookup_transform('base_footprint',rgb.header.frame_id,Time(nanoseconds=source_stamp))
            tf_stamp=tf.header.stamp.sec*10**9+tf.header.stamp.nanosec
            if tf_stamp and abs(source_stamp-tf_stamp)/1e9>MAX_AGE_S:return reject('TF_STALE')
            q=tf.transform.rotation;t=tf.transform.translation
            matrix=np.eye(4);matrix[:3,:3]=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();matrix[:3,3]=[t.x,t.y,t.z]
            if self.previous is None:self.track+=1;self.reference+=1
            o=estimate_object_height(labels==candidates[0],values,np.array(self.info.k).reshape(3,3),matrix,
                stamp_ns=source_stamp,depth_stamp_ns=stamp(depth),now_ns=self.get_clock().now().nanoseconds,
                colour=self.colour,source_frame=rgb.header.frame_id,depth_frame=depth.header.frame_id,
                track_id=f'{self.colour}:sensor-track-{self.track}',reference_id=f'observed-support-{self.reference}')
            if o['valid']:
                if self.previous is not None:
                    # A discontinuity larger than the observed body is a new
                    # association, not evidence of an enormous object lift.
                    distance=np.linalg.norm(np.array(o['center_m'])-self.previous['center_m'])
                    same_support=abs(o['support_height_m']-self.previous['support_height_m'])<=o['uncertainty_m']+self.previous['uncertainty_m']
                    if distance>self.previous['measured_axis_extent_m'] or not same_support:
                        self.previous=None;self.track+=1;self.reference+=1
                        return reject('ASSOCIATION_OR_REFERENCE_CHANGED')
                self.previous=o
            else:
                # Losing geometry loses association; next acquisition is a
                # new track/reference and cannot manufacture a lift delta.
                self.previous=None
            self._publish(o)
        except Exception as exc:
            self.previous=None
            reject('TF_OR_SENSOR_ERROR:'+type(exc).__name__)


def main(args=None):
    rclpy.init(args=args);node=ObjectHeightNode()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.shutdown()

if __name__=='__main__':main()
