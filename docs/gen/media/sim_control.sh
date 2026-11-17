#!/usr/bin/env bash
# Video for user-guide/sim-control: start paused, step, play, pause, with ./jo ctl in a terminal.
#   docs/gen/media/sim_control.sh        (from the repository root; opens windows on the recorded monitor)
source "$(dirname "$0")/lib.sh"
TERM_TITLE=jo_docs_demo
trap 'stop_record; [ -n "${TERM_PID:-}" ] && kill "$TERM_PID" 2> /dev/null; stop_sim' EXIT

start_sim --paused --no-rviz
wait_window "Gazebo Sim"
sleep 12
# The robot is spawned 0.6 m up and drops: stepping shows it falling a few ms at a time
konsole --separate --nofork -p tabtitle="$TERM_TITLE" -p 'Font=DejaVu Sans Mono,15' \
  -e bash "$HERE/demo_term.sh" "$DOMAIN" "$PARTITION" \
  './jo ctl status' './jo ctl step 150' './jo ctl step 150' './jo ctl status' \
  './jo ctl play' 'sleep 6' './jo ctl status' './jo ctl pause' './jo ctl status' \
  > "$LOGS/konsole.log" 2>&1 &
TERM_PID=$!
wait_window "$TERM_TITLE" 30
place "Gazebo Sim" 0 0 $((MON_W * 3 / 5)) "$MON_H"
place "$TERM_TITLE" $((MON_W * 3 / 5)) 0 $((MON_W * 2 / 5)) "$MON_H"
record sim_control
wait "$TERM_PID" || true
TERM_PID=
stop_record
echo "written: $VIDEOS/sim_control.mp4"
