# Sensors

Each simulated sensor publishes the topics, message types and frame ids of the real driver.

| Real sensor | Topics | Frame | Rate |
|---|---|---|---|
| Velodyne VLP-16 (RGL, `Puck` pattern) | `/velodyne_points` (fields x y z intensity ring time), `/scan` (velodyne_laserscan) | `velodyne` | 10 Hz |
| Xsens MTi IMU | `/imu/data` | `imu_link` | 200 Hz |
| Xsens GNSS | `/gnss` | `imu_link` | 10 Hz |
| RealSense D456, front and back | `/<cam>_camera/camera/color/image_raw`, `.../color/camera_info`, `.../aligned_depth_to_color/image_raw`, `.../aligned_depth_to_color/camera_info`, `.../depth/color/points` | `<cam>_camera_color_optical_frame` (cloud: `<cam>_camera_depth_frame`) | 30 Hz |
| Bunker base | `/cmd_vel` in. No odometry, as on the robot. | | |

<div class="media-ph" data-kind="image" markdown>
<span class="media-ph-kind">Image</span>
<p>The sensors in RViz: the lidar cloud coloured by ring, the front and back colour images, the
depth images, the camera clouds.</p>
</div>

## Driver emulation

Gazebo replaces the drivers, so the simulator also does what the drivers do besides reading the
sensor:

- **Velodyne:**
  - `velodyne_emulation` gives the RGL cloud the driver's fields (`ring`, `time`), its range limits
    (0.9 to 130 m) and range noise.
  - The real `velodyne_laserscan_node` then publishes `/scan`, with the driver's parameters.
- **RealSense:**
  - the TF tree below `<cam>_camera_link`, which on the robot comes from the driver
    (`publish_tf: true`) and not from the URDF;
  - the camera cloud is restamped to the depth frame.

## Noise

`sim_noise:=false` (or `./jo sim --no-noise`) turns every noise source off.

| Sensor | Model |
|---|---|
| IMU | Gaussian plus bias. Gyro σ 1.7e-3 rad/s (bias 4e-5); accelerometer σ 8.3e-3 m/s² (bias 1e-3). Xsens MTi datasheet values. |
| GNSS | RTK-like: about 2 cm horizontal, 4 cm vertical |
| Colour images | σ 0.007 |
| Lidar | Range σ `lidar_range_stddev` (0.015 m), added by `velodyne_emulation`: the RGL plugin has no noise model. |

## Startup hold

The Velodyne emulation publishes nothing for the first 2 s of sim time (the `startup_hold`
parameter). The robot is spawned slightly above the ground and drops, and GLIM must initialize
with the robot at rest.

## Differences from the real sensors

- The RGL sweep is captured at one instant, so the per-point `time` is 0. The sim's GLIM config uses
  `global_shutter_lidar: true` for that reason. The robot's config keeps `false`.
- The RealSense depth encoding is still to be evaluated: Gazebo gives 32-bit float metres, the real
  driver 16-bit millimetres ([Roadmap](../developer/roadmap.md)).
- The lidar does not see heightmap terrain.

!!! planned "Planned content"
    - The TF tree (a diagram generated from the URDF).
    - Per-sensor pages: the exact parameters and how they map to the datasheets.
