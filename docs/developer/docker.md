# Docker image

Base image: `osrf/ros:jazzy-desktop-full`, with CUDA, GTSAM, gtsam_points (from source), GLIM,
glim_ros2, the RGL plugin, Nav2 configs, DendROS, Testudo's dependencies, and optionally RTAB-Map.

## Layers, in build order

1. CUDA and GLIM dependencies (GTSAM 4.3 and iridescence from the koide3 PPA, gtsam_points from source)
2. the non-root user `ros`
3. the RGL GPU lidar plugin
4. the workspace: GLIM, glim_ros2 (`GLIM_ROS_REF`), tools
5. RTAB-Map (only with `BUILD_RTABMAP=true`), built one package at a time to fit in memory
6. DendROS
7. Testudo's dependencies
8. `GLIM_ROS_COMMIT`: checks out a glim_ros2 commit and rebuilds only glim_ros. It is declared late,
   so changing it doesn't invalidate the earlier layers.

Pinned versions (GLIM, gtsam_points, RGL, nav2_config, RTAB-Map) are `ARG`s at the top of
`docker/Dockerfile`. Keep GLIM and CUDA in sync with jo-zotac.

## Entrypoint

At every container start, `entrypoint.sh` builds the mounted packages with colcon (plus
`EXTRA_BUILD_PACKAGES`), then touches `/tmp/jo_sim_ready`. Shells wait for that file.

## glim_ros2 development

Uncomment the glim_ros2 volume in `compose.yaml` and set `EXTRA_BUILD_PACKAGES=glim_ros` in `.env`:
your checkout is rebuilt at every container start.

!!! planned "Planned content (Phase F, then G3)"
    The base and workspace image split, compose profiles (`nvidia`, `cpu`, `headless`), and sharing
    fragments with jo-zotac.
