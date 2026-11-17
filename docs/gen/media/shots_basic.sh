#!/usr/bin/env bash
# Screenshots for getting-started/first-run and user-guide/sensors: the Gazebo GUI and RViz
# (sim.rviz), each over the whole recorded area, with Jo turning so the clouds have some structure.
#   docs/gen/media/shots_basic.sh        (from the repository root; opens windows on the recorded monitor)
source "$(dirname "$0")/lib.sh"
trap 'stop_sim' EXIT

start_sim
wait_window "Gazebo Sim"
wait_window "RViz"
sleep 20
drive 0.4 0.3 4  # out of the spawn spot, facing the corridor
sleep 2

place "RViz" 0 0 "$MON_W" "$MON_H"
sleep 4
shot rviz_sim

place "Gazebo Sim" 0 0 "$MON_W" "$MON_H"
sleep 4
shot gazebo_gui
stop_sim

# Markers (explained in the pages' lists); the positions fit this layout and the default view
A="python3 $HERE/annotate.py"
$A "$IMAGES/gazebo_gui.png" "$IMAGES/gazebo_gui.jpg" 80,1300 2025,1318 2440,600 1060,560
$A "$IMAGES/rviz_sim.png" "$IMAGES/rviz_sim.jpg" 1125,330 1960,250 1420,610 315,960 240,300
$A "$IMAGES/rviz_sim.png" "$IMAGES/sensors_rviz.jpg"
rm "$IMAGES/gazebo_gui.png" "$IMAGES/rviz_sim.png"
echo "written: $IMAGES/gazebo_gui.jpg $IMAGES/rviz_sim.jpg $IMAGES/sensors_rviz.jpg"
