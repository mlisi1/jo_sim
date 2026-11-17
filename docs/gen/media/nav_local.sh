#!/usr/bin/env bash
# Video for getting-started/navigation: local navigation in office_cpr. A goal on /goal_pose (what
# RViz's "2D Goal Pose" publishes), 4.5 m along the corridor, then back. Gazebo left, RViz right.
#   docs/gen/media/nav_local.sh        (from the repository root; opens windows on the recorded monitor)
source "$(dirname "$0")/lib.sh"
trap 'stop_record; stop_sim' EXIT

# Spawn facing the corridor (+y), as the office_out_and_back scenario: the map frame starts there
start_sim -n local yaw:=1.5708
wait_window "Gazebo Sim"
wait_window "RViz"
sleep 40  # GLIM initialized, Nav2 active
place "Gazebo Sim" 0 0 $((MON_W / 2)) "$MON_H"
place "RViz" $((MON_W / 2)) 0 $((MON_W / 2)) "$MON_H"
sleep 3

goal() {  # goal X Y QZ QW, in the map frame
  ros "ros2 topic pub --once -w 1 /goal_pose geometry_msgs/msg/PoseStamped \
    '{header: {frame_id: map}, pose: {position: {x: $1, y: $2}, orientation: {z: $3, w: $4}}}' > /dev/null"
}

record nav_local
sleep 2
goal 4.5 0.0 0.0 1.0
sleep 24
goal 1.0 0.0 1.0 0.0
sleep 26
stop_record
echo "written: $VIDEOS/nav_local.mp4"
