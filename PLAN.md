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

## Where we left off (2026-11-16, evening)

Michele confirmed that `full_navigation` (GLIM) and `full_gps_navigation` both work in the sim:
costmaps, path, footprint, clouds, GPS, and the Gazebo camera following the robot.

**Done:**
- Phase A
- most of Phase B (worlds)
- Velodyne emulation (4c)
- the session fixes listed in "Phase A follow-ups" below
- GLIM startup investigation and GLIM config alignment (this session, see "GLIM startup" below):
  jo_sim `5f47b80`, jo_navigation `8c027f8`, `b198fb0`

**Nothing is pushed.** Commits ahead of `origin/dev`: jo_sim 15, jo_navigation 7, jo_description 1.
Push the submodules first, so the superproject never points to unpushed commits.

**Constraints:**
- **jo_description:** joints and origins are the **real robot's TFs** (Michele's `88a2aac`).
  Never change them; sim-only changes go in `<gazebo>` tags.
- **jo-zotac Docker fix:** postponed by Michele.
- **The robot runs GLIM on the GPU only.** CPU-mode results matter little (Michele).
- **Shared machine:** Spirula (`./build_vulkan/spirula`) also uses the GPU, and its builds use a lot of
  RAM. Check `free -h` and `nvidia-smi` before a test batch; the host got close to OOM twice this session.

### Next session checklist
1. **Missing GLIM keys: done in the sim only** (2026-11-17, jo_navigation `5775a10`, jo_sim `584d132`).
   Michele: "first in the sim, then we'll evaluate"; `glim_config_bunker` (robot) is untouched.
   - `glim_config_bunker_sim`: `compute_covs: true`, `ring_field: ring`, `intensity_field`,
     `image_topic: ""`, and explicit defaults `ang_scale`, `config_logging`, `enable_cropbox_filter`,
     `validate_imu`. `submap_target_num_points` was already set in the GPU/passthrough sub_mapping files.
   - `glim_anchor_frame` launch argument (`glim_common.py`): `imu` by default (robot unchanged), jo_sim
     passes `base`. Verified: GLIM odometry and `odometry/filtered` start at 0 (sub-mm).
   - **compute_covs A/B in the sim** (office_cpr, 3+3 runs, straight / 180° turn / straight): EKF end
     error at rest 1-7 mm with, 4-10 mm without; no degradation. But sim GLIM variances are ~1e-7 m²
     (near-noiseless sim) vs 3.3e-4 on the testudo bag: **the sim cannot validate the robot odom0
     tuning**; that needs the bag or the robot.
   - **Found: EKF velocity is poor in both configs** (not caused by compute_covs). `odom0` fuses only
     GLIM x, y, yaw, so EKF `vx` comes from IMU accel + position corrections: 0.11-0.13 m/s in the
     first second of a 0.5 m/s drive (GLIM 0.41-0.45), then 0.57 steady (GLIM 0.483, sd 0.003).
     The EKF output saw-tooths: jumps of 11-28 mm at each GLIM update. Candidate fix, **deferred**
     (Michele: navigation tuning comes later, the current sessions are about the simulator):
     fuse GLIM `vx, vy, vyaw` in `odom0` (GLIM's twist is in base_link with its covariance); test it
     with a variant yaml through `localization_params:=`. Probe scripts: `probe_ekf.py`,
     `analyze_ekf.py`, `jumps_ekf.py`, `run_ekf.sh` in the container's `/tmp/scratch`, data in
     `/tmp/glimrep/ekf` (lost when the container is recreated).
   - Later, with Michele: whether to apply the keys to the robot config `glim_config_bunker`.
   - **EKF on real data (glim_ros2 session, 2026-11-17, testudo bag, robot GPU config + the keys):**
     GLIM GPU 8/8 clean cold starts, variances ~2e-6 m², fork TF invariants hold. But
     `/odometry/filtered` is a median 1-2 m and up to 5-18 m off GLIM, already while standing still.
     Cause in `localization*.yaml` (both files): `imu0_config` fuses the IMU **absolute yaw** (the
     comment says it doesn't); the Xsens yaw is absolute (0 = north) while GLIM's starts at 0, so two
     conflicting yaws. The vx/vy row is ignored (Imu has no velocity), no accelerations are fused.
     **Affects the robot.** Deferred with the rest of the navigation tuning.
     **Sim gap:** the sim hides it at spawn yaw 0 (sim IMU yaw = GLIM yaw). Test with a non-zero
     `yaw:=` and check that the sim IMU orientation follows the Xsens convention (absolute heading).
2. **GPU check on the real data (glim_ros2 session, waiting for Michele's go-ahead):** the robot's
   `glim_config_bunker` with GPU GLIM on the testudo bag, in a throwaway container from the jo-sim image.
   It needs several GiB of RAM and the GPU: run it only when Spirula is not building.
3. **Push when asked:** jo_description, then jo_navigation, then jo_sim.
   - Remove the branch `backup/dev-before-rebase` in jo_description once the push is fine.
   - The robot `T_lidar_imu` change (jo_navigation `8c027f8`) is untested on the robot.
4. **Remaining plan items:**
   - RTAB-Map build check (`BUILD_RTABMAP=true`)
   - Testudo
   - D2 ground truth
   - Phase B leftovers: sensor-topic check in `check_worlds`, per-world sidecar yaml
   - Phases C, E, F
   - D3 obstacles and track re-tuning

**Container state** (`jo_sim-jo-sim-1`, image built ~2026-11-16 morning):
- The **image** contains glim_ros2 `50f7670`. Inside the running container `~/src/glim_ros2` is checked out
  at `5c89eaa` (current `dev`) and rebuilt. A new container, or a container rebuilt without
  `--no-cache`, starts again from `50f7670`: check out `5c89eaa` and run
  `colcon build --symlink-install --packages-select glim_ros`, or rebuild the image.
- The container is built with the `startup_hold` change (jo_sim `5f47b80`).
- Test leftovers: `/tmp/scratch` (probe scripts) and `/tmp/glimrep` (logs, probe json) in the container.
  They are lost when the container is recreated; the harness is described under "GLIM startup" below.

### GLIM startup (2026-11-16)
- **The "1 start in 4" divergence did not reproduce:** 34/34 headless starts clean in office_cpr,
  across localization only, the full stack (2 RealSense + Nav2) and GPS mode, with glim_ros2 `50f7670`
  and `5c89eaa`. GLIM displacement was within ~1 cm of ground truth (about 2.5 m drive with
  `/cmd_vel`, compared with `gz model -m jo -p`).
  The glim_ros2 session saw 30/30 clean cold starts on the testudo bag (fork and upstream).
  If Michele sees it again: note the world and whether the GUI or RViz were open, and keep the
  launch log (GLIM `initial IMU state estimation result` lines).
- **Found and fixed:** the robot spawns at z 0.6 and rests at 0.454, so it free-falls ~0.17 s and the
  IMU reads ~0 inside GLIM's init window. LOOSE init then estimated v_z -0.06 m/s and a 4 cm z offset.
  `velodyne_emulation` now drops clouds for `startup_hold` (default 2 s, sim time) after the first
  one, so GLIM initializes at rest, as on the robot (the VLP-16 also needs seconds to spin up).
  Result: init v_z -0.005 and z ~0, 8/8 clean. The spawn z was left at 0.6: heightmap worlds need
  the clearance.
- **Robot config in the sim:** `glim_config_bunker` (GPU, downsample 0.2, new `T_lidar_imu`) was
  8/8 clean at ~10 Hz, with Spirula sharing the GPU at 84-99 % utilization.
- **Robot `T_lidar_imu`:** Michele chose the URDF value (-0.0514, 0, -0.3753) with **no rotation**.
  The old (0.192, -0.003, -0.318) with 2.3 deg roll came from the old URDF.
- **The sim GLIM config** uses the robot values except where the sim needs otherwise:
  - IMU noise is matched to sim_noise.xacro.
  - `global_shutter_lidar: true`, because the RGL sweep is instantaneous.
  - `downsample_resolution` is 1.0, lighter with Gazebo on the GPU.
  These differences are commented in the files.
- **Ruled out by the glim_ros2 session:**
  - The fork's output side (anchor_frame, publishing thread) can't affect the estimate.
  - `acc_scale` is explicitly 1.0, so the unit isn't guessed from a free-fall sample.
  - Velodyne per-point times are handled correctly by GLIM 1a197c9, with no config change.
  - `downsample_resolution` 0.2 tracks badly with **CPU** GLIM on the testudo bag. That doesn't
    matter for the robot, which runs on the GPU.
- **Jazzy `ros2 run` does not forward SIGINT** to the node: signalling only its PID leaves
  glim_rosnode orphaned (this filled the RAM this session). `ros2 launch`, or a process-group
  signal, is fine. jo-zotac starts GLIM only through `ros2 launch` (checked).
- **Test harness:** `run.sh <idx> [launch args]` + `probe.py` in the container's `/tmp/scratch`.
  It waits 45 s, records `/imu/data` and `/glim_ros/odometry/local`, drives 6 s at 0.5 m/s, and
  compares with `gz model -m jo -p`. Parse the 3-number pose line: the output also has `[10]` (the
  model id).
  - Batches launched with `docker exec` keep running inside the container when the client is
    killed: kill them inside the container.

**Commands** (inside the container: `docker compose exec jo-sim bash`):
- `full_navigation` / `full_gps_navigation` (aliases; extra args are appended, e.g. `world:=small_city`)
- `colcon build --symlink-install --packages-select jo_sim jo_navigation jo_description` from `~`
- `ros2 run jo_sim check_worlds`, `ros2 run jo_sim list_worlds`

**Tests:**
- Use `GZ_PARTITION=jo_sim_test ROS_DOMAIN_ID=77`, launched with `setsid`, and kill the process group.
- Never use Michele's domain 0 / partition `jo_sim`.
- `pkill -f "gz sim"` kills its own shell.
- Xvfb for GUI tests is installed only in the running container (lost on rebuild).

**Background jobs:** none running (2026-11-16 evening). No sim or GLIM process on the host.

---

## Reference: real robot interface (jo-zotac@dev)

| Source (real) | Topic | Type | Frame |
|---|---|---|---|
| Velodyne VLP-16 | `/velodyne_points` | PointCloud2 (x,y,z,intensity,ring,time) | `velodyne` |
| Xsens MTi | `/imu/data` | Imu | `imu_link` |
| Xsens GNSS | `/gnss` | NavSatFix | `imu_link` |
| RealSense D456 (ns `front_camera`, node `camera`) | `/front_camera/camera/color/image_raw`, `.../color/camera_info`, `.../aligned_depth_to_color/image_raw`, `.../aligned_depth_to_color/camera_info`, `.../depth/color/points` | Image / CameraInfo / PointCloud2 | `front_camera_color_optical_frame`, `front_camera_depth_optical_frame` |
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
   lidar noise by jo_sim `velodyne_emulation`).
4c. **Velodyne driver emulation** (2026-11-16): `velodyne_emulation` publishes `/velodyne_points` with the
   driver's fields (x y z intensity ring time, ring from elevation, time 0 as the sim sweep is
   instantaneous) and range limits (0.9–130 m); the real `velodyne_laserscan_node` publishes `/scan`
   (Nav2 costmaps), as `velodyne-all-nodes-VLP16-launch.py` does on the robot. Before this, `/scan`
   did not exist in sim, so the costmaps had no obstacles. Cloud unorganized (robot: organized by ring).
5. **Fix existing bugs**: `GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib`, env vars expanded at
   build time (clobbered), README paths.
6. **Same launch flags as the robot**: `sim_bringup.launch.py` accepts the `jo_bringup` flags
   (sensor flags enable the corresponding bridges), so `full_navigation` / `full_gps_navigation`
   mean the same thing in both containers.
7. **Minimal world preprocessing** (pulled forward from B because sensors depend on it): inject the
   systems the robot needs (Physics, UserCommands, SceneBroadcaster, Sensors/ogre2, IMU, NavSat,
   RGL manager) and `spherical_coordinates` when missing.

### Phase A status (2026-11-16): done (jo_sim 9489728)

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
- glim_ros2@dev, external mode: GLIM's map origin is the initial IMU pose, not base_link (lever arm).
  - At start, `map → base_link` = minus the IMU offset.
  - With the current URDF that is about (-0.20, 0, -0.25); with the old one it was (-0.224, -0.026).
  - Worth fixing in the fork.
- GLIM configs lack the new keys (`glim_ros/ang_scale`, `sensors/ring_field`, ...): defaults used.

### Phase A follow-ups (2026-11-16 session)

**`/clock` (jo_sim be56531).** Bridged from `/world/<name>/clock` by `sim_clock_bridge`.
- In big worlds (small_city, city_osm_roundabout) the root `/clock` is created only after the world
  loads.
- A bridge subscribed before that never received it, so nothing on sim time started and RViz was empty.

**Nav2 on sim time (jo_navigation f5ea8cb).**
- `RewrittenYaml` only rewrites keys that exist, and `controller_server` had no `use_sim_time`.
- So the controller and local costmap ran on wall time: the costmap and path did not update in RViz.

**Gazebo GUI follows the robot (0c05a9f, 8165ed8).**
- `scripts/gui_follow` repeats `/gui/follow` until `/gui/currently_tracked` reports `jo`. A request
  sent while the GUI is loading can be lost.
- `follow:=false` disables it.

**CycloneDDS participant limit (7650303, 8165ed8).**
- Cyclone allows 32 participants (processes) per domain and machine by default.
- The full GPS stack with GUI and RViz, plus CLI tools and the daemon on domain 0, went past it.
  The processes started last failed with "rmw_create_node: failed to create domain":
  - `realsense_tf`: camera clouds missing;
  - the `setUTMZone` call: navsat stuck in UTM zone 31.
- Fix in `docker/utils/cyclonedds.xml`: `MaxAutoParticipantIndex` 100 (ports stay below the next domain's).
- Cyclone errors now go to stderr.
- `realsense_tf` respawns and exits cleanly on Ctrl-C.
- The setUTMZone call retries (jo_navigation 8c6d429).
- Proved with 34 dummy nodes: the old config refuses the next one, the new one accepts it.

**GPS heading (jo_navigation a913204, jo_sim b638ee0).**
- The robot's `yaw_offset: 1.57` is for the Xsens (yaw 0 at north).
- In the sim the odometry yaw is 0 facing east (Gazebo ENU; GLIM starts at the spawn heading), so
  `/odometry/gps` was rotated 90 degrees: driving 3 m east showed as 3 m south.
- `localization_gps.launch.py` has a new `navsat_yaw_offset` argument (empty = params file), and
  sim_bringup passes the spawn `yaw`.
- Verified with yaw 0 and yaw 1.0.
- Worlds with their own `<spherical_coordinates><heading_deg>` would still be rotated (none seen).

**New URDF (jo_description 88a2aac by Michele: D456, CAD sensor frames = the real robot).**
- The sim commit was rebased on top of it (baa94ca): noise, GNSS and the optical `gz_frame_id` are now in
  `d456.xacro` / `imu.xacro`.
- The sim GLIM `T_lidar_imu` comes from the new URDF: (-0.0514, 0, -0.3753) (jo_navigation 6db2f96).
  GLIM tracked a 3 m drive within 2 cm in 3 of 4 runs; the 4th diverged at init (next-session item 1).

**Rejected or explained:**
- "RViz empty" after the clock fix: a 36 s run at RTF 0.15 had not finished starting.
- Two DDS failures were first blamed on a concurrent test; later disproved (it was the participant limit).
- External monitor lag: reverse PRIME (HDMI wired to the NVIDIA GPU, desktop on Intel), not the sim.
  `small_city` with the GUI runs at RTF ~0.15 on this laptop; office_cpr / neighborhood run at ~1.

## DendROS and Testudo

- **DendROS**: installed in the image from the **latest release tag** (resolved at build time,
  `DENDROS_VERSION=latest`, overridable). `jo_sim/config/dendROS.yaml` with groups SIM
  (gz, bridges, spawner, sim helpers), DESC (`robot_state_publisher`), VIZ (rviz).
  jo-zotac should switch to the same snippet.
  Global settings: `docker/utils/dendROS/defaults.yaml` (copy of Michele's host `~/.config/dendROS/defaults.yaml`),
  symlinked into `~/.config/dendROS/` by `utilities.sh`. `node_colors.yaml` is runtime state written by each
  launch (not a setting); the group colors are in the package `dendROS.yaml`, matching jo-zotac's.
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
  **Done (2026-11-16):** `check_worlds` (load errors, server alive, RTF; results in
  `user_worlds/.cache/world_status.json`, shown by `list_worlds`). Classic fixes in the preprocessor:
  sun/ground_plane inlined; missing `model://` models (includes and inline mesh URIs) downloaded from
  Fuel (OpenRobotics, `_` → space) into `user_worlds/.cache/models` under the Classic name, with their
  dependencies and a display-name link; Classic `file://media/...` textures fetched from the
  gazebo-classic repo; Ogre material scripts → PBR albedo/normal maps (converted model copies in
  `user_worlds/.cache/converted_models`, other files linked), alpha-blended ones kept transparent;
  visual heightmaps rescaled (measured: Harmonic draws z = pixel / brightest pixel × size.z + pos.z,
  Classic pixel / 255; small_city terrain was 2.5 m above the streets); Classic `<road>` → asphalt
  strips; ambient-only materials get Classic's white diffuse; negative cloud speed; duplicate names.
  **The RGL lidar does not load heightmaps**: terrain is invisible to `/velodyne_points` and `/scan`.
  Result: **31 ok, 5 slow, 15 fail** of 51. Slow: `warehouse` (RTF ≈ 0.003, box stacks on mesh shelves;
  static models 0.13, bullet detector / featherstone no better), `barrels`, `canyonview_field`, two
  `fetchit` variants. Failing, not fixable generically: meshes without normals (DART: cyberzoo
  orange poles, office_small, simple_env_*), sdformat assertion (office_earthquake, office_env_large),
  models not on Fuel (powerplant, DRC models in test_city), invalid inertia (workshop_example, test_zone),
  world-specific texture (yosemite).
  Still to do: sensor-topic check with the robot spawned.

## Phase C — Launch ergonomics

- Args: `x y z yaw`, `gui:=false` (server only), `paused`, `rtf`, `rviz`, `namespace`, `robot_name`.
- Host wrapper (`./jo sim --world warehouse --nav gps`) around compose + launch.

## Phase D — Fidelity

- **D1 sensors**: noise models of Xsens, VLP-16, D456. Lidar must reproduce the Velodyne `ring` /
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
