# Helpers for the docs recording scripts (docs/gen/media/*.sh). Source it from the repository root.
#
# The simulator runs on the user's display (:0) in its own ROS domain and Gazebo partition, and the
# windows are laid out on one monitor (MON_*), which ffmpeg records. Final videos are 1920x1080 H.264.
set -euo pipefail

DOMAIN=${DOMAIN:-79}
PARTITION=${PARTITION:-jo_sim_docs}
# The area to record: HDMI-1-0 on the maintainer's machine (xrandr --listmonitors), 2560x1440 at
# x 2560, minus the 56 px Plasma panel on its right edge, cut to 16:9
MON_X=${MON_X:-2560} MON_Y=${MON_Y:-0} MON_W=${MON_W:-2496} MON_H=${MON_H:-1404}
VIDEOS=docs/assets/videos
IMAGES=docs/assets/images
LOGS=${LOGS:-/tmp/jo_sim_media}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$VIDEOS" "$IMAGES" "$LOGS"

jo() { ./jo --domain "$DOMAIN" --partition "$PARTITION" "$@"; }

# Start ./jo sim in the background (its own session); stop with stop_sim
start_sim() {
  setsid ./jo --domain "$DOMAIN" --partition "$PARTITION" sim "$@" > "$LOGS/sim.log" 2>&1 < /dev/null &
  SIM_PID=$!
}

stop_sim() {
  jo stop > /dev/null 2>&1 || true
  [ -n "${SIM_PID:-}" ] && kill -- -"$SIM_PID" 2> /dev/null || true
  sleep 3
}

# A ROS command in the container, in our domain
ros() {
  docker exec -e ROS_DOMAIN_ID="$DOMAIN" -e GZ_PARTITION="$PARTITION" jo_sim-jo-sim-1 \
    bash -c "source /opt/ros/jazzy/setup.bash; source /home/ros/install/setup.bash; $1"
}

# Wait until a window whose title contains $1 exists (timeout $2 s, default 120)
wait_window() {
  local t=0
  # not grep -q: with pipefail, its early exit makes xwininfo die of SIGPIPE and the test fail
  until xwininfo -root -tree 2> /dev/null | grep -- "$1" > /dev/null; do
    sleep 1; t=$((t + 1))
    [ "$t" -lt "${2:-120}" ] || { echo "no window '$1'" >&2; return 1; }
  done
}

# place TITLE X Y W H, relative to the recorded monitor
place() { "$HERE/kwin_place.sh" "$1" $((MON_X + $2)) $((MON_Y + $3)) "$4" "$5"; }

# Drive with /cmd_vel: drive VX WZ SECONDS (published at 10 Hz)
drive() {
  ros "timeout $3 ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist '{linear: {x: $1}, angular: {z: $2}}' > /dev/null" || true
}

# Record the monitor in the background: record NAME [SECONDS]; stop with stop_record
record() {
  local dur=()
  [ -n "${2:-}" ] && dur=(-t "$2")
  ffmpeg -loglevel error -y -f x11grab -framerate 30 -video_size "${MON_W}x${MON_H}" \
    -i ":0.0+${MON_X},${MON_Y}" "${dur[@]}" -vf "scale=1920:1080:flags=lanczos" \
    -c:v libx264 -preset slow -crf 30 -pix_fmt yuv420p -movflags +faststart -an "$VIDEOS/$1.mp4" &
  REC_PID=$!
}

stop_record() { kill -INT "$REC_PID" 2> /dev/null || true; wait "$REC_PID" 2> /dev/null || true; }

# Screenshot of the monitor, or of a part of it: shot NAME [X Y W H]
shot() {
  local x=${2:-0} y=${3:-0} w=${4:-$MON_W} h=${5:-$MON_H}
  ffmpeg -loglevel error -y -f x11grab -video_size "${w}x${h}" -i ":0.0+$((MON_X + x)),$((MON_Y + y))" \
    -frames:v 1 "$IMAGES/$1.png"
}
