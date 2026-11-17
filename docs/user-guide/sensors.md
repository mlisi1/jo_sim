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
  - the depth image is converted from Gazebo's 32-bit float metres to the driver's 16-bit
    millimetres (`16UC1`, 0 = no data), as with `depth_format: Z16` on the robot;
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
- RealSense resolution: the sim renders colour and depth at 640×480; the robot's colour stream is
  1280×720 (and its aligned depth with it).
- RealSense depth range: up to ~20 m in the sim (the depth clip in `d456.xacro` is not applied).
- The lidar does not see heightmap terrain.

## TF tree

The simulator alone (`launch_sim`) publishes only static transforms. With the stack running,
GLIM adds `map` → `odom` and the EKF adds `odom` → `base_link`, as on the robot.

--8<-- "docs/includes/generated/tf_tree.md"

## Sensor parameters

The Gazebo side is in jo_description (`velodyne.xacro`, `imu.xacro`, `d456.xacro`, the noise in
`sim_noise.xacro`), inside `<gazebo>` tags. The driver side is in `driver_emulation.launch.py`. The
values below are read from those files.

### Velodyne VLP-16

| Parameter | Sim | Real sensor / driver |
|---|---|---|
| Model | RGL `pattern_preset: Puck` | VLP-16 ("Puck") |
| Channels | 16, numbered by elevation from −15° in 2° steps (`velodyne_emulation`: `rings`, `vertical_fov_min_deg`, `vertical_step_deg`) | 16, ±15°, 2° apart |
| Rate | 10 Hz | 10 Hz (driver default; the sensor does 5–20) |
| Range | RGL casts 0.1–100 m; `velodyne_emulation` keeps 0.9–130 m, the driver's limits | 100 m sensor; driver `min_range` 0.9, `max_range` 130 |
| Range noise | Gaussian σ 0.015 m (`lidar_range_stddev`) | ±3 cm accuracy |
| Point time | 0 for every point (instant sweep) | per-point time within the 0.1 s sweep |
| `/scan` | `velodyne_laserscan_node`, `ring: -1`, `resolution: 0.007` | the same node and parameters |

### Xsens IMU and GNSS

| Parameter | Sim | Real sensor |
|---|---|---|
| IMU rate | 200 Hz | 200 Hz output |
| Gyro noise | σ 1.7e-3 rad/s, bias σ 4e-5 | MTi-6x0: 0.007 °/s/√Hz at 200 Hz |
| Accelerometer noise | σ 8.3e-3 m/s², bias σ 1e-3 | MTi-6x0: 60 µg/√Hz at 200 Hz |
| GNSS rate | 10 Hz | 10 Hz |
| GNSS noise | horizontal 1.8e-7° (about 2 cm), vertical 0.04 m | RTK |
| Frame | `imu_link` for both | `imu_link` for both |

The GNSS horizontal noise is in degrees because gz-sensors applies it to latitude and longitude.

### RealSense D456 (front and back)

| Parameter | Sim | Robot |
|---|---|---|
| Rate | 30 Hz | 30 Hz |
| Colour resolution | 640×480 | 1280×720 |
| Horizontal FOV | 1.50 rad (about 86°), colour and depth | see the D456 datasheet |
| Colour clip | 0.1–20 m | |
| Depth | 32FC1 from Gazebo, converted to 16UC1 mm (`depth_to_mm`) | 16UC1 mm (`depth_format: Z16`) |
| Depth range | up to about 20 m: the `<depth_camera>` clip (0.35–8 m) is not applied | |
| Colour noise | Gaussian σ 0.007 (normalized intensity) | |
| Image frame | `<cam>_camera_color_optical_frame` | the same |
