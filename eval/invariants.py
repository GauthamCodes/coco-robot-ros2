"""M1 catalog: normalized evaluator measurements, never autonomy inputs.

Each rule returns True/False/None. None means missing evidence or calibration,
never a pass. Fixed physics/encoding/oracle requirements cite existing contracts.
"""
import math

# (measurement, relation, threshold-key or literal). "$" refers to another
# contemporaneous measured field, e.g. the unchanged stage's own time budget.
RULES={
'I01':[('host_qualified','eq',True),('rtf','ge','rtf_floor')],
'I02':[('clock_monotonic','eq',True),('clock_stall_wall_s','le','clock_stall_wall_s')],
'I03':[('tf_chains_present','eq',True),('tf_age_sim_s','le','tf_age_sim_s')],
'I04':[('amcl_true_error_m','le','amcl_true_error_m')],
'I05':[('odom_true_displacement_error_m','le','odom_true_displacement_error_m')],
'I06':[('sole_arbiter_publisher','eq',True),('arbiter_selected_matches','eq',True),('arbiter_latency_sim_s','le','arbiter_latency_sim_s')],
'I07':[('command_motion_delay_sim_s','le','command_motion_delay_sim_s'),('command_motion_observed','eq',True)],
'I08':[('planner_active','eq',True),('controller_active','eq',True),('navigator_active','eq',True)],
'I09':[('server_goal_receipt','eq',True),('goal_ack_sim_s','le','goal_ack_sim_s')],
'I10':[('planner_start_occupied','eq',False)],
'I11':[('planner_goal_free','eq',True)],
'I12':[('costmap_age_sim_s','le','costmap_age_sim_s'),('false_lethal_near_robot','eq',False)],
'I13':[('plan_latency_sim_s','le','plan_latency_sim_s')],
'I14':[('retreat_clearance_m','ge','retreat_clearance_m'),('retreat_start_occupied','eq',False)],
'I15':[('rgb_age_sim_s','le','rgb_age_sim_s'),('depth_age_sim_s','le','depth_age_sim_s'),('rgb_depth_skew_sim_s','le','rgb_depth_skew_sim_s')],
'I16':[('projected_extent_error_fraction','le','projected_extent_error_fraction')],
'I17':[('accepted_target_true_error_m','le','accepted_target_true_error_m')],
'I18':[('accepted_is_requested_target','eq',True)],
'I19':[('nonrequested_displacement_m','le',.005)],
'I20':[('moveit_execution_succeeded','eq',True),('joint_tracking_error_rad','le','joint_tracking_error_rad')],
'I21':[('attachment_proximity_m','le','attachment_proximity_m'),('lift_height_m','ge',.03)],
'I22':[('target_attached_during_carry','eq',True)],
'I23':[('fingers_open_before_detach','eq',True),('placed_detached','eq',True),('placement_rest_motion_m','le',.005),('placement_rest_window_sim_s','ge',2.)],
'I24':[('physics_poses_finite','eq',True),('solver_error','eq',False),('max_roll_pitch_rad','le','max_roll_pitch_rad')],
'I25':[('stage_without_progress_sim_s','le','$stage_budget_sim_s')],
}
STAGES={i:('All' if i in ('I01','I02','I03','I04','I05','I06','I19','I24','I25') else
           'Motion' if i=='I07' else 'Navigation' if i in ('I08','I09','I10','I11','I12','I13') else
           'Recovery' if i=='I14' else 'Perception' if i in ('I15','I16','I17','I18') else
           'Manipulation' if i=='I20' else 'Grasp' if i=='I21' else 'Carry' if i=='I22' else 'Place') for i in RULES}


def evaluate(invariant,measurements,thresholds):
    missing=[]
    failures=[]
    observed=0
    for field,op,source in RULES[invariant]:
        value=measurements.get(field)
        limit=(measurements.get(source[1:]) if isinstance(source,str) and source.startswith('$') else
               thresholds.get(source) if isinstance(source,str) else source)
        if value is None or limit is None:
            missing.append(field if value is None else 'threshold:'+source);continue
        if op=='eq':
            if not isinstance(value,bool) or not isinstance(limit,bool):
                missing.append('invalid:'+field);continue
            passed=value==limit
        else:
            if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (value,limit)):
                missing.append('invalid:'+field);continue
            passed=value<=limit if op=='le' else value>=limit
        observed+=1
        if not passed:failures.append({'measurement':field,'value':value,'relation':op,'limit':limit})
    return {'holds':False if failures else None if missing else True,
            'failures':failures,'missing':missing,'observed_checks':observed}


def threshold_keys():
    return sorted({s for rules in RULES.values() for _,_,s in rules if isinstance(s,str) and not s.startswith('$')})
