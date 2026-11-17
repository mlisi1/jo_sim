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

Pinned versions (GLIM, gtsam_points, RGL, nav2_config, RTAB-Map) are `ARG`s in
`docker/Dockerfile`. Keep GLIM and CUDA in sync with jo-zotac.

!!! warning "Declare each ARG right before the layer that uses it"
    BuildKit puts every declared `ARG` in the environment of all the `RUN`s after it. If an ARG is
    declared at the top, changing it, even `BUILD_RTABMAP`, invalidates every layer: CUDA,
    gtsam_points, GLIM, about an hour of build. Declared next to its layer, it invalidates only that
    layer and the ones after it.

## Building

`docker compose build` reads the build arguments from `.env`. To try a variant without touching
your image, build it under another tag. It shares every cached layer before the first argument
that differs:

```bash
set -a; . ./.env; set +a
docker build --network host -f docker/Dockerfile -t jo-sim:rtabmap \
  --build-arg BUILD_RTABMAP=true --build-arg GLIM_ROS_COMMIT=$GLIM_ROS_COMMIT \
  --build-arg BUILD_JOBS=$BUILD_JOBS --build-arg CUDA_ARCHS=$CUDA_ARCHS .
```

With a warm cache, the RTAB-Map variant takes about 20 minutes on 8 jobs. A full build from
scratch takes about an hour.

## Graphics

`compose.yaml` sets the NVIDIA PRIME render-offload variables. That's right for hybrid graphics
(desktop on the integrated GPU, rendering on NVIDIA). If the display runs on the NVIDIA GPU, set
`NV_PRIME_RENDER_OFFLOAD=` and `GLX_VENDOR_LIBRARY_NAME=` (empty) in `.env`.

The RGL lidar needs CUDA, so there is no CPU-only mode: without an NVIDIA GPU the simulation runs,
but it has no lidar.

## Entrypoint

At every container start, `entrypoint.sh` builds the mounted packages with colcon (plus
`EXTRA_BUILD_PACKAGES`), then touches `/tmp/jo_sim_ready`. Shells wait for that file.

## glim_ros2 development

Uncomment the glim_ros2 volume in `compose.yaml` and set `EXTRA_BUILD_PACKAGES=glim_ros` in `.env`:
your checkout is rebuilt at every container start.

!!! planned "Planned content"
    Sharing Dockerfile fragments with jo-zotac (postponed), and a `headless` compose setup for CI
    (it depends on the CI decision).
