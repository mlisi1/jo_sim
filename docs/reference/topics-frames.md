# Topics and frames

## The robot interface (same as the robot)

| Topic | Type | Frame | Direction |
|---|---|---|---|
| `/velodyne_points` | `sensor_msgs/PointCloud2` (x y z intensity ring time) | `velodyne` | out |
| `/scan` | `sensor_msgs/LaserScan` | `velodyne` | out |
| `/imu/data` | `sensor_msgs/Imu` | `imu_link` | out |
| `/gnss` | `sensor_msgs/NavSatFix` | `imu_link` | out |
| `/<cam>_camera/camera/color/image_raw` (+ transports) | `sensor_msgs/Image` | `<cam>_camera_color_optical_frame` | out |
| `/<cam>_camera/camera/color/camera_info` | `sensor_msgs/CameraInfo` | `<cam>_camera_color_optical_frame` | out |
| `/<cam>_camera/camera/aligned_depth_to_color/image_raw` (+ transports) | `sensor_msgs/Image` (16UC1, mm) | `<cam>_camera_color_optical_frame` | out |
| `/<cam>_camera/camera/aligned_depth_to_color/camera_info` | `sensor_msgs/CameraInfo` | `<cam>_camera_color_optical_frame` | out |
| `/<cam>_camera/camera/depth/color/points` | `sensor_msgs/PointCloud2` | `<cam>_camera_depth_frame` | out |
| `/cmd_vel` | `geometry_msgs/Twist` | | in |
| `/clock` | `rosgraph_msgs/Clock` | | out |
| `/tf`, `/tf_static` | | | out |

`<cam>` is `front` or `back`.

## Simulation only (`/sim/...`)

Nothing in the stack may consume these.

| Topic | Type | What |
|---|---|---|
| `/sim/ground_truth/odom` | `nav_msgs/Odometry` | the true pose, `world` → `base_link`, 100 Hz |
| `/sim/velodyne_points_raw` | `sensor_msgs/PointCloud2` | the RGL cloud before `velodyne_emulation` |
| `/sim/<cam>_camera/depth_raw` | `sensor_msgs/Image` (32FC1, m) | the depth image before `depth_to_mm` |
| `/sim/<cam>_camera/points_raw` | `sensor_msgs/PointCloud2` | the RGB-D cloud before `frame_restamp` |

!!! planned "Planned content (G3)"
    Generated from the bridge configs and `testudo.yaml`, with rates and QoS.
