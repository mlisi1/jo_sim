# Repositories

| Repository | Path in jo_sim | Branch |
|---|---|---|
| [mlisi1/jo_sim](https://github.com/mlisi1/jo_sim) | (superproject) | `dev` |
| [mlisi1/jo_description](https://github.com/mlisi1/jo_description) | `jo_description` | `dev` |
| [mlisi1/jo_navigation](https://github.com/mlisi1/jo_navigation) | `jo_navigation` | `dev` |
| [mlisi1/testudo](https://github.com/mlisi1/testudo) | `testudo` | `dev` |
| [gazebo_models_worlds_collection](https://github.com/leonhartyao/gazebo_models_worlds_collection) | `jo_sim/worlds/external` | |
| [mlisi1/glim_ros2](https://github.com/mlisi1/glim_ros2) | baked into the image (`GLIM_ROS_REF`, `GLIM_ROS_COMMIT`) | `dev` |

`jo_description` and `jo_navigation` are shared with the robot (`jo-zotac`).

## Push order

Push the **submodules first**, then jo_sim. That way the superproject never points to a commit that
isn't on GitHub.

## Layout of jo_sim

```text
jo                        host wrapper (./jo help)
compose.yaml  .env        container definition and settings
docker/                   Dockerfile, entrypoint, utils/ (aliases, CycloneDDS, DendROS; mounted)
jo_sim/                   the ROS package
  launch/                 sim_bringup, launch_sim, driver_emulation
  config/bridge/          ros_gz_bridge configs, one per sensor flag
  jo_sim/world_tools.py   world search, sidecars, preprocessor
  scenarios/              office_out_and_back, office_crossing
  scripts/                check_worlds, list_worlds, scenario, sim_control, gui_follow, realsense_tf
  src/                    velodyne_emulation, frame_restamp, depth_to_mm, waypoint_mover (C++)
  worlds/                 own worlds, external/ collection
  rviz/sim.rviz
docs/  mkdocs.yml         this site
user_worlds/ saved_maps/ bags/   mounted data folders
PLAN.md                   working roadmap and session notes
```
