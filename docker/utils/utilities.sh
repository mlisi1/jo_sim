# Sourced from ~/.bashrc. Mounted at runtime: edit without rebuilding the image.
source /opt/ros/jazzy/setup.bash
source /home/ros/install/setup.bash
source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash

alias no_gpu='__NV_PRIME_RENDER_OFFLOAD=0 __GLX_VENDOR_LIBRARY_NAME='

# Simulator only (world + robot + all sensors)
alias sim='ros2 launch jo_sim launch_sim.launch.py rviz:=true'
alias sim_worlds='ros2 run jo_sim list_worlds'

# Same names and flags as jo-zotac (docker/utils/utilities.sh), on the simulator.
# Extra simulator arguments can be appended, e.g. `full_navigation world:=warehouse`.
alias sensors='ros2 launch jo_sim sim_bringup.launch.py'
alias full_sensors='ros2 launch jo_sim sim_bringup.launch.py front_cam:=true back_cam:=true gnss:=true'
alias full_navigation='ros2 launch jo_sim sim_bringup.launch.py front_cam:=true localization:=true navigation:=true rviz:=true back_cam:=true'
alias full_gps_navigation='ros2 launch jo_sim sim_bringup.launch.py front_cam:=true gnss:=true localization_gps:=true navigation_gps:=true rviz:=true back_cam:=true'

alias teleop='ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p use_sim_time:=true'
alias offline_viewer='ros2 run glim_ros offline_viewer'
alias save_map='ros2 service call /glim_ros/save_map std_srvs/srv/Trigger'
