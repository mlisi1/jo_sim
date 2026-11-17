# Bridges

`jo_sim/config/bridge/` holds one ros_gz_bridge config per sensor flag. `launch_sim` starts one
`parameter_bridge` per file, if its flag is on. `core.yaml` is always bridged.

| File | What |
|---|---|
| `core.yaml` | `/cmd_vel` → TrackedVehicle; `/sim/ground_truth/odom`. |
| `imu.yaml` | `/imu/data` |
| `gnss.yaml` | `/gnss` |
| `lidar_raw.yaml` | the RGL cloud → `/sim/velodyne_points_raw` (driver emulation makes `/velodyne_points`) |
| `front_cam.yaml`, `back_cam.yaml` | `.../color/camera_info`, the depth image → `.../aligned_depth_to_color/image_raw`, the RGB-D cloud → `/sim/<cam>_camera/points_raw` (`frame_restamp` makes `.../depth/color/points`) |
| `front_cam_depth_info.yaml`, `back_cam_depth_info.yaml` | the same Gazebo `camera_info`, also as `.../aligned_depth_to_color/camera_info`: colour and depth share one viewpoint |

The images go through `ros_gz_image` (`image_bridge`), so the image transports are available.

**The clock** is bridged by `launch_sim` from `/world/<name>/clock`, not from the root `/clock`. See
[Design decisions](decisions.md).
