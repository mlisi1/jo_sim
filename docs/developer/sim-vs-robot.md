# Sim vs robot configs

Each difference between the simulator's configuration and the robot's, with its reason.

## GLIM: `glim_config_bunker_sim` vs `glim_config_bunker`

| Key | Robot | Sim | Why |
|---|---|---|---|
| `imu_acc_noise`, `imu_gyro_noise`, `imu_int_noise`, `imu_bias_noise` | 0.05, 0.02, 0.001, 1e-5 (Xsens) | 0.01, 0.005, 1e-4, 1e-6 | Matched to the Gazebo IMU noise (`sim_noise.xacro`). |
| `global_shutter_lidar` | `false` | `true` | The RGL sweep is instantaneous: the per-point times are 0. |
| `downsample_resolution` | 0.2 | 1.0 (GLIM's default) | Lighter, while Gazebo shares the GPU. |
| `image_topic` | `/camera/image/compressed` | `""` | No loaded module uses images. |

`T_lidar_imu` is the same in both: (-0.0514, 0, -0.3753) from the URDF, with no rotation.

## Launch arguments

| Argument | Robot | Sim | Why |
|---|---|---|---|
| `glim_anchor_frame` | `imu` (robot unchanged) | `base` | The origin of GLIM's `map` and `odom` frames. With `base`, GLIM's odometry and `/odometry/filtered` start at 0 (checked to below 1 mm). |
| `navsat_yaw_offset` | 1.57 (the Xsens yaw is 0 at north) | the spawn yaw | Gazebo is ENU, and GLIM's odometry starts at the spawn heading. |

## EKF and Nav2

None. The simulator runs the robot's own files from jo_navigation: `localization.yaml`,
`localization_gps.yaml`, `nav2_local.yaml` and `nav2_local_gps_voxel.yaml`. Only `use_sim_time` and
`navsat_yaw_offset` (above) change.

To try a variant without touching the robot's file, pass it with `localization_params:=file.yaml`.

!!! note "Open: the IMU heading convention"
    The Xsens reports an absolute heading (0 = north). Whether the simulated IMU should follow the
    same convention is being checked on the robot first. Until then, results that depend on the
    IMU's absolute yaw are only meaningful at spawn yaw 0.
