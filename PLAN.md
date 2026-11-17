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

## Where we left off (2026-11-17)

`full_navigation` (GLIM) and `full_gps_navigation` work in the sim (Michele, 2026-11-16).
This work is about **updating the simulator**: Michele said navigation/EKF tuning comes later.

**Done:**
- Phase A
- Phase B (see "Phase B" below):
  - `check_worlds --robot` and the physics-step cap: `500a0ae`
  - world sidecar yaml: `66908a4`
- **Phase C** (2026-11-17, jo_sim commit "Phase C: ..."): `paused`, `rtf`, `sim_control`, host wrapper `./jo`
  (DendROS TUI included). Michele tried it: "really good". `namespace` / `robot_name` not planned
  (multi-robot), see "Phase C" below.
- **D2 ground truth** (2026-11-17): `/sim/ground_truth/odom`, see "Phase D" below.
- **RViz clouds as points** (Michele's preference): `sim.rviz` and jo_navigation `navigation.rviz`
  (`9e37e8e`) use `Style: Points`, 3 px, instead of Flat Squares.
- Velodyne emulation (4c)
- GLIM startup investigation (2026-11-16, see "GLIM startup" below)
- **GLIM keys in the sim config** (jo_navigation `5775a10`, jo_sim `584d132`). Details and the EKF
  findings are in "GLIM keys and EKF (2026-11-17)" below.
- **DendROS** (`b10329f`): global settings copied from Michele's host, image stays at v1.1.0. See "DendROS and Testudo".
- **Testudo** (`c99519c`): integrated but parked. See "DendROS and Testudo".
- **Image** (`c99519c`): glim_ros2 is pinned through the `GLIM_ROS_COMMIT` build arg, currently `da3fae1`.

**Pushed on 2026-11-17** (all on `dev`). Always push the submodules first, so the superproject never
points to unpushed commits.

**Constraints:**
- **jo_description:** joints and origins are the **real robot's TFs** (Michele's `88a2aac`).
  Never change them; sim-only changes go in `<gazebo>` tags.
- **Scope: simulator only for now.** Record navigation findings (`localization*.yaml`, Nav2) as
  deferred; don't tune them.
- **The robot config `glim_config_bunker` is untouched.** New GLIM keys go in the sim config first;
  Michele evaluates before anything reaches the robot.
- **jo-zotac Docker fix:** postponed by Michele. Don't touch jo-zotac: another session has
  uncommitted changes there. The robot's Testudo config will belong to jo-zotac.
- **The robot runs GLIM on the GPU only.** CPU-mode results matter little.
- **Shared machine:**
  - Spirula (`./build_vulkan/spirula`) uses the GPU, and its builds use a lot of RAM and CPU. On
    2026-11-17 its shader compiles dropped office_cpr to RTF 0.06.
  - Check `uptime`, `free -h` and `nvidia-smi` before a test batch.
  - The glim_ros2 session (`~/glim_ros2`) coordinates GPU slots through SendMessage.

### Next session checklist
1. **D2 ground truth: done** (2026-11-17). Next: use it in probes instead of `gz model -p`.
2. **Questions of 2026-11-17, answered:**
   - **GLIM map auto-save: no** (Michele, 2026-11-17: `save_map` from the shell is enough).
   - **`TERM` in `compose.yaml`: dropped** (Michele, 2026-11-17). `./jo` passes the host `TERM`.
   - **DendROS 8-colour bug:** note left in `~/DendROS/NOTE_tui_8_color_terminals.md` (2026-11-17).
   - **`namespace` / `robot_name`: not planned** (Michele, 2026-11-17: no multi-robot needed).
3. **Decisions of 2026-11-17** (Michele):
   - **`check_worlds --robot` over all 51 worlds: not yet.** Wait for Michele's go.
   - **IMU heading convention** (the "Sim gap" in "GLIM keys and EKF"): **later**. Some things must
     be confirmed on the robot first.
   - **Approved, order to be decided with Michele:** Phase E, Phase F, D3, track re-tuning (use the
     D2 ground truth), RealSense depth encoding (D1), the RTAB-Map build check (RAM-heavy: only when
     Spirula is not building). Also the documentation site, Phase G below.
   - **EKF tuning: later** (Michele).
   - **Robot `T_lidar_imu`** (jo_navigation `8c027f8`): Michele will test it on the robot soon.
4. **GLIM robot config** (jo_navigation `a49e82f`):
   - The neutral keys went into `glim_config_bunker`. They are GLIM defaults made explicit:
     `config_logging`, `validate_imu`, `enable_cropbox_filter`, `ang_scale`, `intensity_field`.
     `ring_field: ring` makes GLIM read the ring field, which nothing in GLIM uses yet.
   - **`compute_covs: true` too** (Michele approved, jo_navigation `b9690aa`). GLIM's odometry
     covariance goes from glim_ros's fixed fallback (1e-2 m², 1e-3 rad²) to GLIM's marginals
     (~2e-6 m² on the GPU on the testudo bag): about 5000x more weight for GLIM in the EKF's `odom0`.
     Watch for it in the EKF tuning.
   - Robot and sim configs now differ only in the sim-specific values (IMU noise,
     `global_shutter_lidar`, `downsample_resolution`, `image_topic`).
   - **GLIM viewers**, robot and sim: GLIM's metric point size again (`point_size_metric: true`,
     `point_size: 0.025` m) for `standard_viewer` and `interactive_viewer` (`offline_viewer`).
     They were screen-space sizes 0.01 and 10.0, from `31a3c4d`. GUI only. Not yet checked visually:
     look at it on the next `--glim-view` or `offline_viewer`.
5. **Pushed 2026-11-17**, all on `dev`: jo_description, then jo_navigation, then jo_sim.
   - Remove the branch `backup/dev-before-rebase` in jo_description (local only).
6. **Deferred, for Michele (not simulator work):** the EKF findings below. They **affect the robot**:
   `imu0` fuses an absolute yaw.
7. **GLIM drift on the testudo bag** (glim_ros2 session, 2026-11-17, FYI). Parked robot, bag s 30-60,
   95th-percentile pose spread, robot GPU config:
   - upstream glim_ros2 10.4 / 12.2 m;
   - fork 8.5 / 10.0 m;
   - fork with `downsample_resolution` 1.0: 4.9 / 8.3 m;
   - the robot's own live GLIM in the bag: 7.9 m. Wheel odometry: 0.1 m.

   So the cause is GLIM with this config or this environment, not the fork or the downsampling.

**How to run:**
- From the host: `./jo sim [-w world] [-n none|local|gps] [--headless] [--paused] [--rtf X]
  [--glim-view] [name:=value ...]`, `./jo ctl play|pause|step|status`, `./jo stop`, `./jo build`,
  `./jo shell`. `./jo help` lists everything.
- Tests through the wrapper: `./jo --domain 77 --partition jo_sim_test sim --headless --no-rviz`.
  Then `./jo --domain 77 --partition jo_sim_test stop`. In a pseudo-tty (`script -qfc`), Ctrl-C works too.
- Inside the container (`docker exec -it jo_sim-jo-sim-1 bash`):
- Tests always use `GZ_PARTITION=jo_sim_test ROS_DOMAIN_ID=77`, never the user's domain 0 or
  partition `jo_sim`. `check_worlds --robot` uses its own partition and domain 78.
- Stop launches by process group (`setsid ros2 launch ... &`, then `kill -INT -$PG`).

**Container state** (`jo_sim-jo-sim-1`, image rebuilt and container recreated 2026-11-17):
- **glim_ros2:** pinned with `GLIM_ROS_COMMIT` in `.env` (`dev` `da3fae1`). A late layer checks it
  out and rebuilds only glim_ros. To follow a newer commit, set it in `.env`, run
  `docker compose build` (about a minute), then `docker compose up -d`. glim_ros2 `dev` has newer
  commits (`9ea1bff`, `3838f5c`, `af79c6c`), none of them changing `glim_rosnode`.
- **Left running** after the session (2026-11-17 ~12:10). No sim, no background jobs or test
  launches of this session.
- **The glim_ros2 session's** container `glim_gpu_test` was running then (short GPU GLIM runs on
  domain 88 about the robot config's parked drift, suspected `downsample_resolution 0.2`). Not ours:
  leave it alone; its results go to Michele / that session.
- **Test leftovers** in the container, lost when it is recreated: `/tmp/glimrep` (logs).

### GLIM keys and EKF (2026-11-17)
- **Sim config `glim_config_bunker_sim`** (jo_navigation `5775a10`). Michele: "first in the sim,
  then we'll evaluate".
  - New: `compute_covs: true`, `ring_field: ring`, `intensity_field`, `image_topic: ""`.
  - Explicit defaults: `ang_scale`, `config_logging`, `enable_cropbox_filter`, `validate_imu`.
  - `submap_target_num_points` was already set in the GPU/passthrough sub_mapping files.
- **`glim_anchor_frame` launch argument** (`glim_common.py`): `imu` by default, so the robot is
  unchanged; jo_sim passes `base`. Verified: GLIM odometry and `odometry/filtered` start at 0 (sub-mm).
- **`global_shutter_lidar: true` stays in the sim config.** The RGL sweep is instantaneous, so
  per-point times are 0. The robot config keeps `false`.
- **compute_covs A/B in the sim** (office_cpr, 3+3 runs, straight / 180° turn / straight):
  - EKF end error at rest: 1-7 mm with compute_covs, 4-10 mm without. No degradation.
  - But sim GLIM variances are ~1e-7 m² (near-noiseless sim), vs 3.3e-4 on CPU and ~2e-6 on GPU on
    the testudo bag. **The sim cannot validate the robot's `odom0` tuning.**
- **EKF velocity is poor in both configs** (deferred, not caused by compute_covs):
  - `odom0` fuses only GLIM x, y and yaw, so EKF `vx` lags: 0.11-0.13 m/s in the first second of a
    0.5 m/s drive (GLIM 0.41-0.45), then 0.57 at steady speed (GLIM 0.483).
  - Result: 11-28 mm jumps at each GLIM update.
  - Candidate fix: fuse GLIM `vx, vy, vyaw`. GLIM's twist is in base_link, with its covariance. Test
    it with a variant yaml through `localization_params:=`.
- **EKF on real data** (glim_ros2 session, testudo bag, robot GPU config plus the new keys):
  - GLIM: 8/8 clean cold starts, fork TF invariants hold.
  - `/odometry/filtered` is a median 1-2 m and up to 5-18 m off GLIM, even while the robot stands still.
  - Cause, in both `localization*.yaml` files: `imu0_config` fuses the IMU's **absolute yaw**,
    although the comment says it doesn't. The Xsens yaw is absolute (0 = north) while GLIM's starts
    at 0. The vx/vy row does nothing, and no accelerations are fused.
  - **Affects the robot.** Deferred.
  - **Sim gap:** at spawn yaw 0 the sim IMU yaw equals GLIM's, which hides this. Check with a
    non-zero `yaw:=`, and check that the sim IMU follows the Xsens absolute-heading convention.

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

**Background jobs:** none of ours (2026-11-17 ~12:10).

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
- **Testudo** (topic health): submodule `testudo` following `main`, mounted and built by the
  entrypoint (`textual` via `pip --user` in the image). Config **owned by jo_sim**:
  `jo_sim/config/testudo.yaml` (Michele: the robot's belongs to jo-zotac). Aliases `health`,
  `health_check`. **Status (2026-11-17): integrated but not reliable yet, parked** (Michele: "not
  that important"). Testudo-side problems are written up in `~/testudo/JO_SIM_NOTES.md` for the
  Testudo agent: invalid package.xml (`--` in comments, so the aliases call
  `~/install/testudo/lib/testudo/testudo` instead of `ros2 run`), no use_sim_time, content checks
  failing with the full stack (~128 topics), TF watch missing map->odom. jo_sim-side leftover:
  declare the Nav2 action feedback / selector topics as `event_driven` (most of the ERRORs while
  idle).

## Phase B — Drop-in worlds

- Folders: built-in `jo_sim/worlds/`, the external collection, and a host-mounted `./user_worlds/`
  (`$JO_SIM_WORLDS`), each with an optional `models/` subfolder added to `GZ_SIM_RESOURCE_PATH`.
- `world:=warehouse` resolves by name (`.sdf` / `.world`), full paths still work; `sim_worlds` lists them.
- Preprocessor (started in A) writes a patched temp copy of the world: missing systems,
  spherical coordinates, obstacles (see D3).
- Optional sidecar `<world>.yaml`: spawn pose(s), GNSS datum (lat/lon), description, missions, obstacles.
  **Done (2026-11-17)** for spawn (`spawn:` + named `spawns:`, `spawn:=<name>`), `gnss:` datum and
  `description` (`world_tools.world_settings`: command line > sidecar > defaults; looked up in the
  search dirs first, so `user_worlds/` overrides and external-collection sidecars go in
  `jo_sim/worlds/`, then next to the world). sim_bringup's navsat yaw offset follows the resolved
  yaw. Verified end to end (spawn pose, GNSS fix, navsat yaw_offset). Missions/obstacles: later (E, D3).
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
  **Done (2026-11-17): `check_worlds --robot`** spawns the robot with every sensor (own Gazebo
  partition and ROS domain 78) and checks each robot-interface topic's rate from header stamps
  (sim time), lidar valid and ground returns, robot upright on the ground. Tested: office_cpr,
  small_city ok; hemicyl flagged (heightmap: 0 lidar returns, no /scan). It found a
  physics-step issue: 9 Classic worlds use 10 ms, so the 200 Hz IMU ran at 100 Hz. The preprocessor
  now caps the step at 5 ms and scales `real_time_update_rate` (hemicyl IMU 199.7 Hz).
  Not yet run on all worlds (each takes ~70 s; run it when the GPU is free).

## Phase C — Launch ergonomics

- Args: `x y z yaw`, `gui:=false` (server only), `paused`, `rtf`, `rviz`, `namespace`, `robot_name`.
- Host wrapper (`./jo sim --world warehouse --nav gps`) around compose + launch.

**Done (2026-11-17):**
- `paused:=true`: gz starts without `-r`. Play from the GUI or `sim_control play` (new script, alias
  `sim_control`: `play | pause | step [N] | status`, finds the world's control service in the current
  `GZ_PARTITION`).
- `rtf:=X`: the preprocessor sets `<physics><real_time_factor>` (adds a 1 ms `<physics>` if the world
  has none). Harmonic honours it: office_cpr ran at 0.50 with `rtf:=0.5`, and at ~2.3 with `rtf:=0`
  (as fast as possible) while Spirula held the GPU at 100 %. `real_time_update_rate` is not what
  sets the pace.
- `./jo` host wrapper: `sim [-w world] [-n none|local|gps] [-s spawn] [--headless] [--no-rviz]
  [--paused] [--rtf X] [--no-noise] [name:=value ...]`, plus `shell build worlds check ctl stop up
  down`. It starts the container if needed and runs through `bash -ic`, so utilities.sh (build wait,
  environment) applies. The global `--domain N --partition P` options select the ROS domain and Gazebo
  partition. `-n local|gps` uses the same flags as `full_navigation` / `full_gps_navigation`.
  - Verified headless: paused + step + play, rtf 0 / 0.5 / 1, `-n local` up to "Managed nodes are
    active".
  - Ctrl-C through a pseudo-tty stops every process.
  - A client killed without a tty leaves the launch running in the container. `./jo stop` signals
    the process group of each `ros2 launch jo_sim` whose `GZ_PARTITION` matches (SIGKILL after 30 s).
    Signalling only `ros2 launch` left `gz sim` running.
  - The commands run as `ros2 ...` inside `bash -ic`, never `exec ros2`: `ros2` is DendROS's shell
    function (output piped through DendROS), and `exec` would run the plain binary. Michele noticed
    it. `--glim-view` = `glim_view:=true`.
  - The wrapper passes the host `TERM`: `docker exec -t` sets `TERM=xterm` (8 colours), and DendROS's
    TUI then raises `ValueError: Color number is greater than COLORS-1 (7)` in `init_pair` and silently
    falls back to the classic output. That is a DendROS bug (it should handle 8-colour terminals),
    and it also hits a plain `docker compose exec jo-sim bash`.
- **Not planned: `namespace` and `robot_name`** (Michele, 2026-11-17: no multi-robot needed). They
  only matter for several robots, and the robot has neither:
  - the stack (jo_navigation) is not namespaced;
  - the Gazebo sensor topics (`imu`, `gnss`, `<cam>_camera`, `velodyne_points`) are global names in
    the jo_description `<gazebo>` tags;
  - the cmd_vel bridge uses `/model/jo/cmd_vel`;
  - TF frames carry no prefix.
  A second robot needs all of these: xacro topic prefixes, templated bridge configs, a frame prefix
  and a namespaced stack. For a second, separate simulation, use another domain and partition
  (`./jo --domain 77 --partition other sim ...`).

## Phase D — Fidelity

- **D1 sensors**: noise models of Xsens, VLP-16, D456. Lidar must reproduce the Velodyne `ring` /
  per-point `time` fields and end-of-sweep stamping (GLIM deskewing depends on it); RealSense
  depth encoding: **done 2026-11-17**.
  - New node `depth_to_mm`: Gazebo's `/sim/<cam>_camera/depth_raw` (32FC1, m) -> the driver's
    `aligned_depth_to_color/image_raw`, 16UC1 mm with 0 = no data (robot: `depth_format: Z16`,
    `align_depth`, in jo-zotac `front_d455.yaml`). It publishes through image_transport, so
    `compressedDepth` exists.
  - Verified: max |mm - 1000*m| = 0.5 (rounding), invalid pixels -> 0, ~30 Hz, both cameras.
  - The only consumer is RTAB-Map's `rgbd_odometry` (`visual_odom.launch.py`).
  - **Noted, not changed:** the sim renders 640x480, while the robot's colour stream is 1280x720 (a
    larger render costs GPU). The depth clip 0.35-8 m in `d456.xacro` isn't applied: depth goes up
    to ~20 m.
- **D2 odometry**: the robot has none, so `TrackedVehicle` odometry stays out of the ROS interface
  (no topic, no TF). **Ground truth: done (2026-11-17).**
  - `OdometryPublisher` in a sim-only `<gazebo>` tag of `jo_main.urdf.xacro` (jo_description;
    joints and origins untouched), bridged by `config/bridge/core.yaml`.
  - `/sim/ground_truth/odom`, `nav_msgs/Odometry`, 100 Hz, `world` -> `base_link`, twist in
    `base_link`. The plugin's TF (`/sim/ground_truth/tf`) is not bridged. Explicit topics: the
    plugin's default `/model/jo/odometry` is TrackedVehicle's topic.
  - Verified (spawn x 2, y -1, yaw 0.7): world-frame pose (not relative to spawn), identical to
    `gz model -p` to the mm; ~99.5 Hz; twist 0.500 m/s on a 0.5 m/s command.
  - Nothing in the stack may consume it. Use it to evaluate GLIM / EKF / RTAB-Map (drift,
    end-of-mission error, upstream vs fork glim_ros2, `map_odom_mode:=external` consistency,
    deskew with/without per-point times). GLIM's frames start at the spawn pose: compare
    relative to the first ground-truth message.
  - **Track finding (for the re-tuning below), one run:** a straight 0.5 m/s command for 4 s turned
    the yaw 0.70 -> 1.06 rad, and a 0.5 rad/s turn command gave 0.74 rad/s.
    Both resolved, see "Track model re-tuning" below: the drift was a collision, the turn gain is now calibrated.
- **check_worlds --robot over all worlds: done 2026-11-17** (the user gave the go). 44 min for 51
  worlds. The results table is in docs/user-guide/worlds.md:
  - 19 good, 4 usable but slower, 9 too slow (RTF < 0.5), 3 unusable (RTF 0.003);
  - 1 with no lidar (hemicyl, a heightmap);
  - 15 don't load. These are the same ones that failed in Phase B: missing models or media
    (powerplant, test_city, yosemite...) or Gazebo segfaults (office_small, simple_env_*,
    cyberzoo_orange_poles...). Not regressions; fixing them is open, if those worlds are wanted.
  - **Probe bug, fixed:** the first pass reported the camera clouds at 8–15 Hz, or "no messages",
    in 9 worlds. A direct check in city_osm_roundabout gave 30.3 Hz on every camera topic. The
    probe was at fault:
    - it was single-threaded Python and fully deserialized two ~9 MB clouds at 30 Hz;
    - it subscribed best effort, and CycloneDDS then loses a whole cloud when any fragment drops.
    Now: raw subscriptions (stamp read from the CDR bytes, only sampled lidar/scan messages
    deserialized, numpy for the valid-point count), and reliable QoS depth 10. Re-checked the 10
    affected worlds: all OK.
  - **RTF varies between runs** by up to about 0.2 on heavy worlds (montreal2019 0.66 vs 0.43).
- **Testudo on the full stack: green (2026-11-17).** The submodule is at testudo dev 32f7473, which
  has the Testudo agent's fixes for all of ~/testudo/JO_SIM_NOTES.md plus later changes:
  - package.xml, so `ros2 run` works again;
  - ROS args, so use_sim_time can be set;
  - the executor starving the last-created subscriptions;
  - TF decimation, which always dropped map->odom;
  - `/tf_static` QoS depth;
  - event-driven defaults for action feedback, paths and costmap updates;
  - idle inputs;
  - `check` removed (the maintainer's decision);
  - `watch --headless`.
  jo_sim side: `health` = watch, `health_headless` = watch --headless (results on /testudo/*),
  event_driven entries for /motion_target, /slowdown, /glim_ros/grid, and GLIM odom thresholds
  (green 0.05: GLIM's covariance is a configured 1e-2 constant). Result: 167/167 OK with the robot
  idle. `.gitmodules` now tracks testudo `dev`, like the other submodules.
- **D3 dynamic obstacles: done 2026-11-17.**
  - **Gazebo actors don't work:** the RGL lidar sees nothing of them, because RGLServerPluginManager
    only takes entities with Visual + Geometry, and a skinned actor has neither. Verified: 0 returns
    from an actor walking 3 m ahead.
  - **Moving models instead:** `jo_sim/src/waypoint_mover.cc`, a Gazebo system
    (`jo_sim::WaypointMover`, `libjo_sim_waypoint_mover.so`). It teleports its model along
    waypoints with WorldPoseCmd, on sim time. Modes: pingpong, loop, once; pause, delay,
    face_motion; optional `yield_to` / `yield_distance`. RGL updates entity transforms every step,
    so the lidar sees them: about 600 returns from a person 3 m ahead, moving at the commanded speed.
  - **Declared** with `obstacles:=<file.yaml>` (launch_sim) or `obstacles:` in a scenario. The
    preprocessor adds them (`world_tools._add_obstacles`) and writes the world as
    `<world>.obstacles_<hash>.sdf`, so a sim on the same world without obstacles isn't affected.
    Not in the world sidecar yet: add it if needed.
  - **Scenario runner:** reads the true obstacle poses (gz-transport, `dynamic_pose/info`) and
    records the minimum base_link to surface distance at 100 Hz. Criterion `min_obstacle_distance`.
  - **`office_crossing`:** a person crosses the corridor at y = 3. With `yield_distance: 1.2`,
    2 of 2 runs PASS (closest approach 0.74 and 0.67 m).
  - **Nav2 finding (deferred, not tuned: see the scope rule):** without yield, 1 of 2 runs collided.
    The walker crossed the robot's path during goal 2 (min distance -0.075 m). The kinematic
    obstacle shoved the robot, localization went 3.8 m off, and the goal aborted. The other run
    passed (goal 1 took 15 s instead of 8, so Nav2 slowed or waited). Nav2 doesn't reliably avoid a
    person crossing its path. Relevant for the `dynamic-obstacle-layer` branch.
- **Track model re-tuning:** `steering_efficiency` calibrated on 2026-11-17 (jo_description `6be30be`):
  0.5 -> 0.707.
  - On a flat plane, before: the speed ratio was 1.000 with no yaw drift, but the yaw rate was 1.413x
    the command, at every rate.
  - After: yaw rate and speed within 1% of the command, for turns in place (0.3-1.0 rad/s) and for
    combined commands.
  - Probe: drive (v, w) commands, average the body twist and yaw rate from `/sim/ground_truth/odom`
    over the second half of each 6 s window.
  - **The straight-line yaw drift in office_cpr (D2 track finding): explained, not a model issue.**
    - From that spawn (x 2, y -1, yaw 0.7) the robot's front-right corner hits office geometry
      1.7-2.5 m ahead on its right. Mesh check: surface points inside the swept footprint.
    - From the default spawn in office_cpr, straight runs are exact both ways: speed 1.000, yaw 0.
    - The floor along that path is flat at z = 0, with no holes (raycast).

## Phase E — Testing workflow

**Status (2026-11-17): scenarios and bags done; CI to do.**
- **The runner**, `jo_sim/scripts/scenario` (alias `scenario`, `./jo scenario`):
  - launches sim_bringup headless in its own process group, and waits for the ground truth, the
    map->base_link TF and bt_navigator `active`;
  - sends `navigate_to_pose` goals given in world coordinates (converted with the spawn pose);
  - samples the localization error against the ground truth at 5 Hz;
  - writes `report.json`, `launch.log` and an optional bag (the robot's all / compressed profiles,
    minus `/sim/*_raw`) to `bags/scenarios/<date>_<name>/`;
  - exits 0 = pass, 1 = fail, 2 = error.
- **Scenarios** are searched in `user_worlds/scenarios/`, then `jo_sim/scenarios/`. The first one,
  `office_out_and_back`, drives 4.5 m along +y and back. The corridor was checked free on the mesh.
- **Verified in the sandbox:**
  - PASS: goals reached in 8 s each, final errors 0.24 / 0.26 m (about Nav2's goal tolerance),
    localization max 4.8 cm, final 6 mm.
  - A 1 cm variant FAILs with exit 1.
  - `--record compressed` records the bag, ground truth included.
- **Max localization error varies between runs** (4.8 vs 10.9 cm; the second run was recording).
  It peaks during the turn. Watch it before tightening the limits.
- **CI:** GitHub-hosted runners have no GPU, so the smoke scenarios need a self-hosted runner, or a
  CPU-only mode (Phase F). To discuss with Michele.

- Scenario files: world + spawn + mission + pass criteria (goal reached, ground-truth error).
  `ros2 launch jo_sim scenario.launch.py scenario:=...`, headless.
- Bag per run into `./bags` (reuse jo-zotac's YAML recording profiles).
- CI: build image, run 1–2 headless smoke scenarios.

## Phase F — Docker

**Status (2026-11-17): done, as far as it applies.**
- **ARGs moved next to the layers that use them.** BuildKit puts every declared ARG in the
  environment of the later RUNs, so `BUILD_RTABMAP` at the top rebuilt CUDA, gtsam_points and GLIM.
  - Verified: `jo-sim:rtabmap` reused steps 1–16 of the default build; only RTAB-Map and the
    steps after it were rebuilt (15 min).
- **`LD_LIBRARY_PATH` had a trailing ':'**, an empty entry, which means the current directory.
  Fixed with `${VAR:+:$VAR}`.
- **PRIME offload variables:** overridable from `.env` (`NV_PRIME_RENDER_OFFLOAD`,
  `GLX_VENDOR_LIBRARY_NAME`). The defaults are unchanged.
- **Already true:** the base / thin workspace split (the mounted packages are built by the
  entrypoint, about 1 s when unchanged), and the entrypoint rebuilding only on change (colcon).
- **Not done:**
  - `cpu` profile: the RGL lidar needs CUDA, so a CPU-only sim has no lidar.
  - `headless` profile: only needed for CI. Michele questioned whether the sim needs CI at all.
  - Sharing fragments with jo-zotac: postponed by Michele.
- **The user's container was recreated on the new image** (Michele's OK), and `office_out_and_back`
  PASSes on it.
- **RTAB-Map check, done:** `jo-sim:rtabmap` (BUILD_RTABMAP=true) in a temporary container, with
  `visual_odom.launch.py` (rgbd_odometry, compressed + compressedDepth, front camera) in office_cpr.
  - 3 m straight: 2.982 m vs 2.996 m ground truth (1.5 cm, 0.1°).
  - 90° turn in place: 88.5° vs 88.2° (0.3°).
  - Never lost, about 30 Hz, no warnings.
  - So the 16UC1 depth (D1) works end to end through compressedDepth.

- Base image (ROS, Gazebo, CUDA, RGL, GLIM, RTAB-Map) + thin workspace layer.
- Compose profiles `nvidia` (default) / `cpu` / `headless`; no hard-coded PRIME offload vars.
- Entrypoint rebuilds only when sources changed.
- Ideally share Dockerfile fragments / build args (GLIM pin, CUDA, DendROS) with jo-zotac.

## Phase G — Documentation site (GitHub Pages)

Asked by Michele on 2026-11-17. It must be thorough and complete, with images and videos. Readers:
- people who only want to set up and use the simulator;
- people who change or extend it;
- agents.

### Stack
- **MkDocs Material**, as DendROS (`~/DendROS/mkdocs.yml`, `.github/workflows/docs.yml`): the same
  theme and extensions, and Mermaid diagrams through `pymdownx.superfences`.
- Sources in jo_sim: `docs/` and `mkdocs.yml`. Built and deployed by a GitHub Actions workflow to
  `https://mlisi1.github.io/jo_sim`. The repos are public, so Pages is free.
- `mkdocs build --strict` in CI: broken links and missing pages fail the build.
- `llms.txt` / `llms-full.txt` (mkdocs-llmstxt plugin), so an agent can read the whole site as one
  text file.

### Site structure
1. **Home:** what jo_sim is, the guiding principle (the same ROS interface as the robot), a hero video,
   and three entry points: *Use it*, *Develop it*, *Agents*.
2. **Getting started** (users):
   - requirements (NVIDIA GPU and driver, Docker, NVIDIA Container Toolkit, X11; disk and RAM);
   - clone with submodules, `.env`, first build (with the expected durations);
   - first run: `./jo sim`, a tour of the Gazebo GUI and RViz with annotated screenshots, driving with
     `/cmd_vel`;
   - the navigation modes (`-n local`, `-n gps`), a Nav2 goal, a GPS goal;
   - stopping, cleaning up, updating (`git pull`, submodules, image rebuild).
3. **User guide:**
   - `./jo`, every command and option;
   - launch arguments (a generated table);
   - worlds:
     - a catalogue of the 51 worlds, with thumbnail, size, GNSS datum and spawns;
     - the sidecar yaml;
     - adding your own world in `user_worlds/`;
     - `check_worlds`.
   - sensors: topics, types, rates, frames, noise, and how each differs from the real sensor;
   - the TF tree (a diagram generated from the URDF);
   - simulation control: paused, step, RTF;
   - ground truth (`/sim/ground_truth/odom`) and how to compare it with GLIM or the EKF;
   - GLIM maps: `save_map`, `offline_viewer`, `glim_view`;
   - bags and scenarios (after Phase E);
   - running two simulations (domain and partition);
   - DendROS and Testudo in the sim;
   - performance on a shared GPU;
   - troubleshooting and FAQ, built from the gotchas in this file (DDS participant limit, TERM and the
     DendROS TUI, reverse-PRIME monitor lag, a slow RTF, ...).
4. **Developer guide:**
   - architecture: Gazebo, bridges, driver emulation, the stack (Mermaid diagram), and who owns
     which TF;
   - repos and submodules, branches, the push order;
   - **invariants:** jo_description joints and origins are the robot's real TFs; sim changes go only
     in `<gazebo>` tags; nothing in the stack consumes `/sim/*`;
   - walkthroughs:
     - the launch files (`sim_bringup`, `launch_sim`, `driver_emulation`);
     - the world preprocessor (`world_tools.py`: every patch it makes, and why);
     - the bridge configs;
     - the nodes: `velodyne_emulation`, `frame_restamp`, `realsense_tf`, `gui_follow`, `sim_control`;
   - the Docker image: layers, build args, the GLIM pin, rebuilding only glim_ros, the entrypoint;
   - how-tos: add a sensor, add a world feature to the preprocessor, add a launch argument, follow
     a new glim_ros2 commit, change noise models;
   - testing: the sandbox domain and partition, process-group kills, `check_worlds`, scenarios and CI;
   - the sim vs robot config differences (GLIM, navsat, EKF), each with its reason;
   - a design decisions log (the "why" now spread over this file): instantaneous RGL sweep and
     `global_shutter_lidar`, `startup_hold`, the physics-step cap, the clock bridge from the world
     topic, CycloneDDS at 100 participants, ...
   - conventions: commits, docs updated in the same commit as a feature;
   - the roadmap, from this file.
5. **For agents:**
   - an `AGENTS.md` at the repo root (a short page also on the site): invariants, the test sandbox,
     how to verify a change, where state lives (PLAN.md, the docs), what not to touch (jo-zotac,
     the robot GLIM config without Michele);
   - `llms-full.txt`.
6. **Reference:** topics and frames, parameters, config files, the `./jo help` output, a glossary
   (GLIM, RGL, RTF, partition, sidecar, ...).

### Media
- **Screenshots:** Gazebo GUI, RViz in every mode, the GLIM viewer, `offline_viewer`, the DendROS TUI,
  the sensor views (cloud, cameras, depth).
- **World thumbnails:** generated automatically, with a headless camera render of each world (the
  same per-world loop as `check_worlds`, so it needs the GPU).
- **Videos:** short, compressed MP4/WebM (a few MB each, kept in `docs/assets`; Pages serves no Git
  LFS):
  - a quick-start run;
  - local navigation to a goal;
  - GPS navigation in a city world;
  - pause, step and RTF;
  - building a GLIM map and opening it.

  I can record them by screen capture (ffmpeg) while a scripted run drives the sim. Michele records
  the ones that need real interaction, or reviews mine.
- **Diagrams:** Mermaid (architecture, launch graph, data flow), and the TF tree.

### Kept up to date by generation
Scripts in `docs/gen/` rebuild these tables, and CI fails if they are out of date:
- the world catalogue, from the sidecars and `list_worlds`;
- launch arguments, from the `DeclareLaunchArgument`s;
- topics, from the bridge yamls and `testudo.yaml`;
- `./jo help`.

### Steps
- **G1: done (2026-11-17).** Skeleton, theme, CI deploy, `AGENTS.md`. Move the README content in; the README keeps a
  quick start and the link.
- **G2:** the user pages.
- **G3:** the developer and reference pages, plus the generators.
- **G4:** media (screenshots, thumbnails, videos).
- **G5:** review:
  - a fresh agent with only the site sets up the sim and adds a sensor;
  - Michele reads it as a new user.

### Open points for Michele
- the deploy branch: **`main`** (Michele, 2026-11-17);
- scope: jo_sim only, with jo_description and jo_navigation covered where the sim touches them
  (proposed), or separate sites;
- who records the videos.

### G1 status (2026-11-17)
- **Site:**
  - `docs/` (39 pages), `mkdocs.yml`, `.github/workflows/docs.yml`.
  - Built with `mkdocs build --strict` on pull requests and on pushes to `dev` and `main`.
  - **Deployed only from `main`** (Michele), through the Pages artifact actions
    (`upload-pages-artifact`, `deploy-pages`). There are no commits and no `gh-pages` branch:
    `mkdocs gh-deploy` committed as `github-actions[bot]`, who then showed up among the
    contributors. The first deploy was replaced the same day and its `gh-pages` branch deleted.
  - Pages must be set once in the repo settings: Pages → Source: **GitHub Actions**.
  - The site is published only after `dev` is merged into `main`.
- **Theme:** navy base, "sensor" cyan (#06b6d4), amber accent (#f59e0b). Dark scheme first. Hero on
  the home page, grid cards, media placeholders (`<div class="media-ph" data-kind=...>`; list them
  with `grep -rn media-ph docs`), and `!!! planned` boxes for content still to write.
- **For agents:** `llms.txt` and `llms-full.txt` (mkdocs-llmstxt), and `AGENTS.md` at the repo root.
- **The README** keeps a quick start and links the site.
- **Material for MkDocs reaches end of life on 2027-05-05** (it prints this at build). Its successor,
  Zensical, reads the same `mkdocs.yml`: migrate before then.
- **Checking the look without the GPU:** headless Chrome with `--disable-gpu`. For the dark scheme,
  first set the localStorage key `/.__palette` to scheme `slate` in the same profile.
- **Logo, favicon and home render** (Michele's choice): Jo rendered from the URDF, with a
  transparent background, by `docs/gen/render_logo/render.sh`. CPU only: Blender Cycles on the CPU,
  with CUDA hidden. Run it again if the URDF's look changes.
- **Open:** who records the videos.
