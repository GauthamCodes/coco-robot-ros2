"""Fixed M1 trace contract. Cameras are excluded to bound storage."""
TOPICS={t:0 for t in (
    '/clock','/mission/state','/mission/search','/mission/search_region','/mission/mode',
    '/mission/target_colour','/ramp/status','/approach/status','/grasp/status',
    '/cmd_vel_arbiter/status','/localization/health','/amcl_pose','/initialpose',
    '/tf','/tf_static','/diff_drive_controller/odom','/imu','/joint_states',
    '/cmd_vel_nav','/cmd_vel_smoothed','/cmd_vel','/cmd_vel_gated','/cmd_vel_rl',
    '/cmd_vel_approach','/diff_drive_controller/cmd_vel','/rosout','/plan',
    '/behavior_tree_log','/perception/status','/perception/target_pose/status',
    '/perception/target','/perception/target_pose','/perception/candidates',
    '/diagnostics/mission_callbacks','/eval/ground_truth/state','/eval/ground_truth/robot/pose',
    '/eval/nav2/lifecycle','/eval/graph','/eval/trace_health')}
for name in ('target_red','target_green','target_blue','target_yellow'):
    for suffix in ('pose','dimensions'):
        TOPICS[f'/eval/ground_truth/objects/{name}/{suffix}']=0
    TOPICS[f'/magnet/{name}/state']=0
for action in ('navigate_to_pose','compute_path_to_pose','follow_path','spin','execute_trajectory'):
    for suffix in ('status','feedback'):
        TOPICS[f'/{action}/_action/{suffix}']=0
    # Jazzy has action services, not goal/result topics. Capture service-event
    # streams if the existing server publishes introspection. Missing is a gap.
    for suffix in ('send_goal','get_result','cancel_goal'):
        TOPICS[f'/{action}/_action/{suffix}/_service_event']=0
for topic in ('/global_costmap/costmap','/local_costmap/costmap',
              '/global_costmap/costmap_raw','/local_costmap/costmap_raw'):
    TOPICS[topic]=1.0  # throttle bag writes only; production publication unchanged
