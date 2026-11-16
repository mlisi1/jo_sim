# jo_sim — roadmap

Goal: make `jo_sim` the official simulator of Jo, used to test the real stack.

**Guiding principle:** the simulator exposes *the same ROS interface as the real robot*
(`jo-zotac@dev`) — topic names, message types, frame ids, TF ownership, rates, middleware —
and nothing more. Gazebo replaces the drivers, so the simulator also emulates the parts of the
drivers that are not the sensor itself (e.g. the RealSense TF tree). The stack (`jo_navigation`)
runs unchanged on top of it with `use_sim_time:=true`. `jo_description` must keep working on the
robot: only `<gazebo>` tags (ignored by `robot_state_publisher`) may be sim-specific.

Order: **A → DendROS/Testudo → B → C → E → F → D**.

---

## Reference: real robot interface (jo-zotac@dev)

| Source (real) | Topic | Type | Frame |
|---|---|---|---|
| Velodyne VLP-16 | `/velodyne_points` | PointCloud2 (x,y,z,intensity,ring,time) | `velodyne` |
| Xsens MTi | `/imu/data` | Imu | `imu_link` |
| Xsens GNSS | `/gnss` | NavSatFix | `imu_link` |
| RealSense D455 (ns `front_camera`, node `camera`) | `/front_camera/camera/color/image_raw`, `.../color/camera_info`, `.../aligned_depth_to_color/image_raw`, `.../aligned_depth_to_color/camera_info`, `.../depth/color/points` | Image / CameraInfo / PointCloud2 | `front_camera_color_optical_frame`, `front_camera_depth_optical_frame` |
| RealSense TF (`publish_tf: true`) | `front_camera_link → front_camera_{color,depth}_frame → ..._optical_frame` | TF static | — |
| Bunker base | subscribes `/cmd_vel`; **no odometry** (`odom_frame: none`) | Twist | — |
| Middleware | `rmw_cyclonedds_cpp` + `docker/utils/cyclonedds.xml` (`AllowMulticast=spdp`) | | |
| Bringup flags | `imu lidar gnss front_cam back_cam bunker sens_rviz localization localization_gps navigation navigation_gps glim_view` | | |

---

## Phase A — Sync with the current stack

1. **Topics and frames identical to the robot** (table above).
   - Bridge renames the Gazebo topics to the RealSense / Xsens names.
   - Cameras: `<gz_frame_id>` (a `<gazebo>`-only tag) set to the colour optical frame, so image /
     depth / camera_info carry the frame RTAB-Map expects. The RGB-D point cloud is produced by
     Gazebo in the X-forward camera convention, so a small restamp node publishes it in
     `front_camera_depth_frame`. This replaces the relay nodes used in the past.
   - `driver_emulation.launch.py` publishes the RealSense TF tree below `front_camera_link`
     (on the robot it comes from the driver, so it must **not** go in the URDF).
   - GNSS: NavSat sensor on `imu_link` publishing `/gnss` (`<gazebo>`-only tag).
2. **One GLIM, owned by jo_navigation.** Removed from `jo_sim`; the sim GLIM config becomes
   `jo_navigation/config/glim/glim_config_bunker_sim`, selected with `glim_config:=`.
   GLIM, navsat_transform get `use_sim_time`.
3. **glim_ros2 `dev` (best-practice fork) tested in sim first.**
   - Image builds `mlisi1/glim_ros2@${GLIM_ROS_REF}` (default `dev`), koide3/glim pinned to
     `1a197c9` (≥ required by the fork, contains the `a9be365` GTSAM 4.3 fix) and gtsam_points from
     source at `8e94654` (GLIM master needs `has_index`, newer than the PPA's 1.2.2).
   - jo_navigation uses only the glim_ros2@dev interface (the robot moves to it too): EKF fuses `/glim_ros/odometry/local`
     (`odom_child_frame: base`), local mode `map_odom_mode: external` + `map_odom_planar`,
     GPS mode `publish_tf: false`, `map_save_directory: /saved_maps`,
     viewer removed via the `extension_modules` parameter instead of copying the config to /tmp.
   - Optional dev mount of `~/glim_ros2` (rebuilt by the entrypoint) to iterate without rebuilding the image.
4. **Docker aligned with jo-zotac**: CycloneDDS + same `cyclonedds.xml`, CUDA 13.1, `.env`,
   runtime-mounted `docker/utils`, `saved_maps` / `bags` volumes, `BUILD_RTABMAP` build arg
   (RTAB-Map built from source sequentially, as on the robot; off by default — localization
   falls back to `visodom:=false` when it is not installed), DendROS latest release,
   all clones pinned through build args.
4b. **Sensor noise switch** `sim_noise:=true|false` (xacro arg in jo_description, `<gazebo>`-only;
   lidar noise by jo_sim `range_noise`).
5. **Fix existing bugs**: `GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib`, env vars expanded at
   build time (clobbered), README paths.
6. **Same launch flags as the robot**: `sim_bringup.launch.py` accepts the `jo_bringup` flags
   (sensor flags enable the corresponding bridges), so `full_navigation` / `full_gps_navigation`
   mean the same thing in both containers.
7. **Minimal world preprocessing** (pulled forward from B because sensors depend on it): inject the
   systems the robot needs (Physics, UserCommands, SceneBroadcaster, Sensors/ogre2, IMU, NavSat,
   RGL manager) and `spherical_coordinates` when missing.

### Phase A status (2026-11-16) — implemented, not committed

Verified in the container (headless): all robot topics/frames as in the reference table, RealSense
TF tree, `/gnss` (2 cm noise around the datum), local stack (GLIM v2 external mode → EKF → Nav2
active) and GPS stack (navsat + both EKFs + Nav2 active).

Findings:
- koide3/glim master needs `IndexedSlidingWindow::has_index` (gtsam_points > 1.2.2, the newest
  release and PPA version): gtsam_points is built from source at `8e94654` (explicit
  `CUDA_ARCHS`, `native` cannot work in docker build). **jo-zotac needs the same when it is rebuilt.**
- Gazebo's RGB-D cloud is X-forward (confirmed), hence the restamp to `<cam>_depth_frame`. It must be
  subscribed RELIABLE (~10 MB per cloud, best effort never delivers).
- image_transport does not propagate the base remap to `/compressed` etc.: each is remapped explicitly.
- NavSat horizontal noise is in degrees, not metres.
- Classic worlds carry a 0,0 `<spherical_coordinates>` placeholder: replaced by the configured datum
  (UTM 32N is hard-coded in localization_gps).
- With `network_mode: host`, all containers share the default Gazebo partition: `GZ_PARTITION=jo_sim`
  in `.env` (two simulators otherwise mix clocks).
- glim_ros2@dev, external mode: at start `map → base_link = (-0.224, -0.026)`, i.e. GLIM's map origin
  is the initial IMU pose, not base_link (lever arm). Worth fixing in the fork.
- GLIM configs lack the new keys (`glim_ros/ang_scale`, `sensors/ring_field`, ...): defaults used.

## DendROS and Testudo

- **DendROS**: installed in the image from the **latest release tag** (resolved at build time,
  `DENDROS_VERSION=latest`, overridable). `jo_sim/config/dendROS.yaml` with groups SIM
  (gz, bridges, spawner, sim helpers), DESC (`robot_state_publisher`), VIZ (rviz).
  jo-zotac should switch to the same snippet.
- **Testudo** (topic health): submodule following `main` (no `dev` branch / tags yet), built in
  the workspace (`textual` via pip). **One Testudo config shared by robot and sim** (in
  jo_navigation or jo_description, both mounted by both containers) declaring the robot's topics,
  rates, frame ids, TF chain, Nav2 actions and GLIM `/diagnostics`. Used as the normal health view
  during sim sessions; a sim that is not green under the robot's config has drifted from the
  robot interface.

## Phase B — Drop-in worlds

- Folders: built-in `jo_sim/worlds/`, the external collection, and a host-mounted `./user_worlds/`
  (`$JO_SIM_WORLDS`), each with an optional `models/` subfolder added to `GZ_SIM_RESOURCE_PATH`.
- `world:=warehouse` resolves by name (`.sdf` / `.world`), full paths still work; `sim_worlds` lists them.
- Preprocessor (started in A) writes a patched temp copy of the world: missing systems,
  spherical coordinates, obstacles (see D3).
- Optional sidecar `<world>.yaml`: spawn pose(s), GNSS datum (lat/lon), description, missions, obstacles.
- `check_worlds` script: loads every world headless for N s, checks sensor topics, maintains a
  curated "known good" list (many external worlds are Gazebo Classic and do not load in Harmonic).

## Phase C — Launch ergonomics

- Args: `x y z yaw`, `gui:=false` (server only), `paused`, `rtf`, `rviz`, `namespace`, `robot_name`.
- Host wrapper (`./jo sim --world warehouse --nav gps`) around compose + launch.

## Phase D — Fidelity

- **D1 sensors**: noise models of Xsens, VLP-16, D455. Lidar must reproduce the Velodyne `ring` /
  per-point `time` fields and end-of-sweep stamping (GLIM deskewing depends on it); RealSense
  depth encoding (16UC1 mm vs Gazebo 32FC1 m) to be evaluated.
- **D2 odometry**: the robot has none, so `TrackedVehicle` odometry stays out of the ROS interface
  (no topic, no TF). Add a sim-only ground truth (`/sim/ground_truth/odom`, OdometryPublisher)
  that nothing in the stack consumes — used to evaluate GLIM / EKF / RTAB-Map
  (drift, end-of-mission error, upstream vs fork glim_ros2, `map_odom_mode:=external` consistency,
  deskew with/without per-point times).
- **D3 dynamic obstacles**, declared in the world sidecar and injected by the preprocessor,
  toggled with `obstacles:=true|false`:
  - *actors*: animated people on scripted waypoints (realistic, no physics);
  - *moving models*: physical boxes/carts driven along paths (TrajectoryFollower or a ROS node),
    can block the robot, can be reactive.
  Use: `dynamic-obstacle-layer` branch, Nav2 replanning/recoveries, GLIM/RTAB-Map robustness to
  moving points. To verify first: whether RGL sees animated actor meshes.
  ```yaml
  obstacles:
    - {type: person, path: [[2,0],[2,6],[-2,6]], speed: 1.2, loop: true}
    - {type: box, size: [0.5,0.5,1.0], path: [[5,-3],[5,3]], speed: 0.6, start_delay: 10}
  ```
- Track model re-tuning after the Bunker CAD update.

## Phase E — Testing workflow

- Scenario files: world + spawn + mission + pass criteria (goal reached, ground-truth error).
  `ros2 launch jo_sim scenario.launch.py scenario:=...`, headless.
- Bag per run into `./bags` (reuse jo-zotac's YAML recording profiles).
- CI: build image, run 1–2 headless smoke scenarios.

## Phase F — Docker

- Base image (ROS, Gazebo, CUDA, RGL, GLIM, RTAB-Map) + thin workspace layer.
- Compose profiles `nvidia` (default) / `cpu` / `headless`; no hard-coded PRIME offload vars.
- Entrypoint rebuilds only when sources changed.
- Ideally share Dockerfile fragments / build args (GLIM pin, CUDA, DendROS) with jo-zotac.
