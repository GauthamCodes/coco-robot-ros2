#!/usr/bin/env python3
"""Process-local engineering capture extension. Production TOPICS unchanged."""
from topics import TOPICS
import recorder
from recorder import main

if __name__ == '__main__':
    # Real images/intrinsics alongside existing TF/candidate/mission evidence.
    # One Hz capture limits engineering bag growth; source stamps retained.
    TOPICS.update({name: 1.0 for name in ('/camera/image_raw',
                  '/camera/depth/image_raw', '/camera/camera_info', '/perception/object_height')})
    TOPICS['/diagnostics/manipulation_checkpoints'] = 0
    TOPICS['/diagnostics/manipulation_observation_acceptance'] = 0
    for suffix in ('attach','detach'):
        TOPICS['/magnet/target_red/'+suffix] = 0
    recorder.ENGINEERING_IMAGE_SUMMARY = True
    main()
