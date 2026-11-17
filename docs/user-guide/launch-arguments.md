# Launch arguments

There are two entry points:

| Launch file | Alias | Role |
|---|---|---|
| `sim_bringup.launch.py` | `sensors`, `full_sensors`, `full_navigation`, `full_gps_navigation`; used by `./jo sim` | The equivalent of the robot's `jo_bringup.launch.py`: the same flags, plus the stack from `jo_navigation`. |
| `launch_sim.launch.py` | `sim` | World, robot, bridges and driver emulation only, no stack. |

Pass arguments as `name:=value`, to `ros2 launch` or after `./jo sim`.

!!! warning "Different sensor defaults"
    `sim_bringup` uses the robot's defaults: `imu` and `lidar` on, `gnss`, `front_cam` and
    `back_cam` off. `launch_sim` (the `sim` alias) turns every sensor on.

## Robot flags (same as `jo_bringup`)

| Argument | Default | |
|---|---|---|
| `imu` | `true` | IMU topics |
| `gnss` | `false` | GNSS topic |
| `lidar` | `true` | Velodyne cloud and `/scan` |
| `front_cam`, `back_cam` | `false` | RealSense topics |
| `bunker` | `false` | Accepted for compatibility; the simulated base always runs. |
| `sens_rviz` | `false` | RViz with the sensors |
| `localization` | `false` | GLIM + EKF |
| `localization_gps` | `false` | GPS localization (navsat_transform) |
| `navigation` | `false` | Nav2, local |
| `navigation_gps` | `false` | Nav2, GPS |
| `glim_view` | `false` | GLIM's viewer window |
| `use_sim_time` | `true` | Always true in simulation |

## Simulator arguments

| Argument | Default | |
|---|---|---|
| `world` | `office_cpr` | World name (see `sim_worlds`) or path |
| `gui` | `true` | Gazebo GUI; `false` runs the server only (headless rendering) |
| `follow` | `true` | The GUI camera follows the robot |
| `paused` | `false` | Start paused ([Simulation control](sim-control.md)) |
| `rtf` | the world's | Target real-time factor; `0` = as fast as possible |
| `gz_verbosity` | `3` | Gazebo log level |
| `x`, `y`, `z`, `yaw` | sidecar, else `0 0 0.6 0` | Spawn pose |
| `spawn` | | A named spawn pose from the world's sidecar |
| `latitude`, `longitude`, `elevation` | sidecar, else Pisa | GNSS datum, used when the world has no `<spherical_coordinates>` |
| `sim_noise` | `true` | Sensor noise (IMU, GNSS, cameras, lidar) |
| `lidar_range_stddev` | `0.015` | [m] lidar range noise when `sim_noise` is on |
| `glim_config` | `glim_config_bunker_sim` | GLIM config directory |
| `glim_anchor_frame` | `base` | Origin of GLIM's map and odom frames (`imu` or `base`) |

!!! planned "Planned content (G3)"
    These tables will be generated from the `DeclareLaunchArgument`s, and CI will check that they
    are up to date.
