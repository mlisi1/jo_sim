# Design decisions

The "why" behind choices that aren't obvious from the code.

??? note "Instantaneous lidar sweep, `time` = 0, `global_shutter_lidar: true`"
    The RGL plugin captures a whole sweep at one instant. Real per-point times would make GLIM
    "deskew" a cloud that has no motion distortion. So `velodyne_emulation` writes `time` = 0, and
    the sim's GLIM config declares a global-shutter lidar.

??? note "`startup_hold`: no lidar for the first 2 s"
    The robot is spawned above the ground and drops. GLIM's initial state estimation assumes the
    robot is at rest, as on the real robot (where the VLP-16 also needs a few seconds to start).

??? note "Physics step capped at 5 ms"
    Sensors publish at most once per physics step. Many Classic worlds use 10 ms, which would cap the
    200 Hz IMU at 100 Hz.

??? note "The clock comes from `/world/<name>/clock`"
    The server creates the root `/clock` topic only after the world has loaded. With big worlds
    (`small_city`, `city_osm_roundabout`), a bridge that subscribed earlier never received it, and
    nothing on sim time started.

??? note "CycloneDDS at 100 participants per domain"
    The default of 32 is too few for the full GPS stack:
    `rmw_create_node: failed to create domain`.

??? note "The camera cloud is restamped to the depth frame"
    Gazebo stamps every RGB-D output with the same frame. The images must carry the optical frame,
    as the RealSense driver does (RTAB-Map relies on it). But Gazebo builds the cloud X-forward, so
    the cloud is republished in `<cam>_camera_depth_frame`.

??? note "No TrackedVehicle odometry in ROS"
    The real robot has no wheel odometry (`bunker_base` runs with `odom_frame: none`), so the
    simulator doesn't provide any either. The ground truth is under `/sim/`, outside the interface.

??? note "One robot per simulation"
    Topic prefixes, frame prefixes and a namespaced stack would be needed for several robots. The
    robot needs none of them, so it isn't planned. Two separate simulations use separate domains
    and partitions.
