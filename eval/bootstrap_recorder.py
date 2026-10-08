#!/usr/bin/env python3
"""Process-local engineering capture extension. Production TOPICS unchanged."""
from topics import TOPICS
from recorder import main

if __name__ == '__main__':
    # Real images/intrinsics alongside existing TF/candidate/mission evidence.
    # One Hz capture limits engineering bag growth; source stamps retained.
    TOPICS.update({name: 1.0 for name in ('/camera/image_raw',
                  '/camera/depth/image_raw', '/camera/camera_info')})
    main()
