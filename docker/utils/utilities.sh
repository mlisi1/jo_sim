# Sourced from ~/.bashrc. Mounted at runtime: edit without rebuilding the image.
source /opt/ros/jazzy/setup.bash

# The entrypoint builds the mounted packages at container start: wait for it before sourcing
if [ ! -f /tmp/jo_sim_ready ]; then
  echo -n "[jo_sim] waiting for the workspace build to finish"
  for _ in $(seq 1 600); do [ -f /tmp/jo_sim_ready ] && break; echo -n "."; sleep 1; done
  echo
fi
source /home/ros/install/setup.bash
source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash

# DendROS global settings (same as the host): the repo file, so `dendros config` edits persist.
# node_colors.yaml next to it is runtime state written by each launch, not a setting.
mkdir -p ~/.config/dendROS && ln -sfn /home/ros/utils/dendROS/defaults.yaml ~/.config/dendROS/defaults.yaml

alias no_gpu='__NV_PRIME_RENDER_OFFLOAD=0 __GLX_VENDOR_LIBRARY_NAME='

# Simulator only (world + robot + all sensors)
alias sim='ros2 launch jo_sim launch_sim.launch.py sens_rviz:=true'
alias sim_worlds='ros2 run jo_sim list_worlds'
alias check_worlds='ros2 run jo_sim check_worlds'
alias sim_control='ros2 run jo_sim sim_control'   # play | pause | step [N] | status
alias scenario='ros2 run jo_sim scenario'         # run a scenario headless, pass/fail (--list)

# Same names and flags as jo-zotac (docker/utils/utilities.sh), on the simulator.
# Extra simulator arguments can be appended, e.g. `full_navigation world:=warehouse`.
alias sensors='ros2 launch jo_sim sim_bringup.launch.py'
alias full_sensors='ros2 launch jo_sim sim_bringup.launch.py front_cam:=true back_cam:=true gnss:=true'
alias full_navigation='ros2 launch jo_sim sim_bringup.launch.py front_cam:=true localization:=true navigation:=true rviz:=true back_cam:=true'
alias full_gps_navigation='ros2 launch jo_sim sim_bringup.launch.py front_cam:=true gnss:=true localization_gps:=true navigation_gps:=true rviz:=true back_cam:=true'

# Topic health (Testudo) against the robot interface: jo_sim/config/testudo.yaml (mounted source, so
# rules added from the TUI's Options screen persist in the repo)
# use_sim_time: rates and staleness on the sim clock (Testudo >= 8a65177 passes ROS args to rclpy)
alias health='ros2 run testudo testudo watch -c /home/ros/src/jo_sim/config/testudo.yaml --ros-args -p use_sim_time:=true'
# Same, without the TUI (scripts, agents): results on /testudo/overall, /testudo/<plugin>, /testudo/vitals
alias health_headless='ros2 run testudo testudo watch --headless -c /home/ros/src/jo_sim/config/testudo.yaml --ros-args -p use_sim_time:=true'

alias teleop='ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p use_sim_time:=true'
alias offline_viewer='ros2 run glim_ros offline_viewer'
alias save_map='ros2 service call /glim_ros/save_map std_srvs/srv/Trigger'
