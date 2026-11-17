# Commands and aliases

## Host

`./jo`: see [The ./jo wrapper](../user-guide/jo-cli.md).

## In the container

| Alias | Command | |
|---|---|---|
| `sim` | `ros2 launch jo_sim launch_sim.launch.py sens_rviz:=true` | world, robot, all sensors, RViz |
| `sensors` | `ros2 launch jo_sim sim_bringup.launch.py` | robot defaults (IMU, lidar) |
| `full_sensors` | `sim_bringup` with `front_cam back_cam gnss` | |
| `full_navigation` | `sim_bringup` with cameras, `localization navigation rviz` | as on the robot |
| `full_gps_navigation` | `sim_bringup` with cameras, `gnss localization_gps navigation_gps rviz` | as on the robot |
| `sim_worlds` | `ros2 run jo_sim list_worlds` | |
| `check_worlds` | `ros2 run jo_sim check_worlds` | |
| `sim_control` | `ros2 run jo_sim sim_control` | `play`, `pause`, `step [N]`, `status` |
| `scenario` | `ros2 run jo_sim scenario` | run a scenario headless: pass/fail, report, bag (`--list`) |
| `teleop` | `teleop_twist_keyboard` with sim time | |
| `save_map` | `ros2 service call /glim_ros/save_map std_srvs/srv/Trigger` | |
| `offline_viewer` | `ros2 run glim_ros offline_viewer` | |
| `health` | Testudo `watch` with `jo_sim/config/testudo.yaml`, on sim time | live TUI; needs a terminal |
| `health_headless` | the same, `watch --headless` | no TUI: results on `/testudo/*` diagnostics |
| `no_gpu` | clears the PRIME offload variables | prefix a command to render on the integrated GPU |

They are defined in `docker/utils/utilities.sh` (mounted, editable without a rebuild).
