#!/usr/bin/env bash
# Video for getting-started/first-run: driving Jo, Gazebo on the left, RViz on the right.
#   docs/gen/media/teleop.sh        (from the repository root; opens windows on the recorded monitor)
source "$(dirname "$0")/lib.sh"
trap 'stop_record; stop_sim' EXIT

start_sim
wait_window "Gazebo Sim"
wait_window "RViz"
sleep 20  # robot settled, sensors up
place "Gazebo Sim" 0 0 $((MON_W / 2)) "$MON_H"
place "RViz" $((MON_W / 2)) 0 $((MON_W / 2)) "$MON_H"
sleep 3

record teleop
sleep 2
drive 0.5 0 6
drive 0.3 0.5 5
drive 0.5 0 5
drive 0 -0.6 4
sleep 2
stop_record
echo "written: $VIDEOS/teleop.mp4"
