#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash

# Mounted packages (and optional dev packages such as glim_ros, see .env)
colcon build \
  --packages-select jo_description jo_sim jo_navigation ${EXTRA_BUILD_PACKAGES} \
  --symlink-install

source install/setup.bash

exec "$@"
