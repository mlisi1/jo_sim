# How-to recipes

Each recipe lists the files to touch, in order, and how to check the result. Test in the sandbox
(`./jo --domain 77 --partition jo_sim_test ...`), see [Testing](testing.md).

## Add a sensor

The sensor must exist on the real robot: the simulator exposes the robot's interface and nothing
more.

1. **Link and joint:** they come from the robot's URDF in `jo_description`. They are the real TFs,
   so they are added or changed by whoever maintains the robot's description, not for the sim. If
   the link is missing, stop and ask.
2. **The Gazebo sensor**, in a `<gazebo reference="<link>">` tag in the sensor's xacro
   (`jo_description/urdf/`):
    - the rate and resolution of the real driver's configuration (jo-zotac `jo_bringup/config/`);
    - noise through the `gz_noise` macro, with the values in `sim_noise.xacro`, so that
      `sim_noise:=false` switches it off;
    - a Gazebo topic name, and `<gz_frame_id>` set to the frame the driver stamps.
3. **The bridge:** a new `jo_sim/config/bridge/<flag>.yaml`.
    - If the real driver publishes the Gazebo output unchanged, use the real ROS topic.
    - Otherwise use `/sim/<...>_raw`, and let driver emulation produce the real topic (next step).
    - Add the file under its flag in `SENSOR_BRIDGES` (`launch/launch_sim.launch.py`).
    - Images go through `ros_gz_image` (see the cameras in `launch_sim`), so the transports exist.
4. **Driver emulation**, if the driver does more than read the sensor: encodings, extra fields, TF
   frames, range limits. Add a node in `jo_sim/src` or `jo_sim/scripts`, and start it in
   `launch/driver_emulation.launch.py` under the sensor's flag. Existing examples:
   `velodyne_emulation`, `depth_to_mm`, `frame_restamp`, `realsense_tf`.
5. **The flag:** the robot's flag name and default in `sim_bringup.launch.py` (as in `jo_bringup`),
   and the same flag in `launch_sim.launch.py`.
6. **The interface check:** the topic, its rate and frame in `jo_sim/config/testudo.yaml`.
7. **Docs:** a row in [Sensors](../user-guide/sensors.md) and
   [Topics and frames](../reference/topics-frames.md). Run `python3 docs/gen/gen_tables.py` for the
   argument and bridge tables.

**Check:** `ros2 topic hz`, `ros2 topic echo --once` (frame, encoding, fields) against a bag of the
real robot, then `health`.

## Add a patch to the world preprocessor

1. Write a `_fix_<what>(world, ..., changes)` function in `jo_sim/jo_sim/world_tools.py`. It edits
   the parsed world and appends a human-readable line to `changes` (the launch prints them).
2. Call it from `prepare_world()`. Patches must be idempotent, and must never touch the original
   file: only the copy in `/tmp/jo_sim/worlds`.
3. Model files that need changes are copied to `user_worlds/.cache/converted_models`, never edited
   in place.
4. Add a line to [Worlds](../user-guide/worlds.md#what-is-patched) and to
   [World preprocessor](world-preprocessor.md).

**Check:** `check_worlds <a world that needs it>`, then `check_worlds --robot <world>`. Make sure
other worlds still load: `check_worlds` on a sample.

## Add a launch argument

1. Declare it with a `description` in `launch_sim.launch.py` (simulator arguments) or
   `sim_bringup.launch.py` (robot flags: same name and default as `jo_bringup`).
2. If `./jo sim` should have an option for it, add it in the `sim()` function of `./jo` and to its
   help text.
3. Run `python3 docs/gen/gen_tables.py`: the tables in [Launch arguments](../user-guide/launch-arguments.md)
   and the `./jo help` text are regenerated.

## Change a noise model

Edit the values in `jo_description/urdf/sim_noise.xacro`. It is sim-only: `<gazebo>` content. Give
the source of the values (a datasheet, or a measurement on the robot) in a comment. The lidar
range noise is the `lidar_range_stddev` launch argument instead, applied by `velodyne_emulation`.

**Check:** with the robot at rest, the standard deviation of `/imu/data`, or the `/gnss` spread,
against the new values.

## Follow a new glim_ros2 commit

Set `GLIM_ROS_COMMIT` in `.env`, then run `docker compose build` (about a minute: only glim_ros is
rebuilt) and `docker compose up -d`. For development on a local checkout, see
[Docker image](docker.md#glim_ros2-development).

## Add a world to the repository

1. Put the world in `jo_sim/worlds/`, and its models next to it.
2. Add a sidecar `<world>.yaml` with a description, the spawn pose(s) and a GNSS datum if the world
   has no `<spherical_coordinates>`.
3. Run `check_worlds --robot <world>`.

## Add a scenario

Write `jo_sim/scenarios/<name>.yaml` (format: [Scenarios](../user-guide/scenarios.md)). Check that
the path is free (the robot is about 1.1 × 0.75 m), then run it until it passes reliably before
tightening the criteria.

To test against moving people, add `obstacles:` and `min_obstacle_distance`, as in
`office_crossing`.

## Re-render the logo

`docs/gen/render_logo/render.sh [azimuth] [elevation]` renders Jo from the URDF on the CPU. It
writes the logo, the favicon and the home-page image.
