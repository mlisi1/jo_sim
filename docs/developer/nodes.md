# Driver emulation nodes

| Node | Language | Job |
|---|---|---|
| `velodyne_emulation` | C++ | RGL cloud → the Velodyne driver's cloud: `ring` (from the elevation, as the driver numbers them), `time`, range limits (0.9–130 m), range noise (`range_stddev`), `startup_hold` (2 s). |
| `velodyne_laserscan_node` | (upstream) | `/scan` from `/velodyne_points`, with the driver's parameters. |
| `frame_restamp` | C++ | Republishes a cloud under another `frame_id`. Gazebo builds the RGB-D cloud X-forward, so the cloud goes to `<cam>_camera_depth_frame` while the images keep the optical frame. |
| `depth_to_mm` | C++ | Gazebo depth (32FC1, m) → the driver's `aligned_depth_to_color/image_raw` (16UC1, mm, 0 = no data), through image_transport (so `compressedDepth` exists). The output topic is a parameter, because image_transport doesn't remap its plugin topics. |
| `realsense_tf` | Python | The static TF tree that the RealSense driver publishes below `<cam>_camera_link`. It respawns if it dies. |
| `gui_follow` | bash | The Gazebo GUI camera follows the robot. |
| `sim_control` | bash | play / pause / step / status, through the world's control service. |
| `scenario` | Python | Runs a scenario: launches headless, sends Nav2 goals, checks the criteria against the ground truth, writes the report and the bag. |
| `check_worlds`, `list_worlds` | Python | World checks, and the world list with their results. |

!!! planned "Planned content (G3)"
    The parameters of each node, and their topics and QoS.
