#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash

# Shells opened with `docker compose exec` wait for this marker (see utils/utilities.sh)
READY=/tmp/jo_sim_ready
rm -f "$READY"

# Mounted packages (and optional dev packages such as glim_ros, see .env)
colcon build \
  --packages-select jo_description jo_sim jo_navigation ${EXTRA_BUILD_PACKAGES} \
  --symlink-install

source install/setup.bash
touch "$READY"

exec "$@"
