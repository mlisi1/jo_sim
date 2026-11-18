# Install

## 1. Clone, with the submodules

```bash
git clone --recurse-submodules -b dev https://github.com/mlisi1/jo_sim.git
cd jo_sim
```

The repository brings in its packages as git submodules:

| Path | What |
|---|---|
| `jo_description` | The robot's URDF. Its joints and origins are the real robot's TFs. |
| `jo_navigation` | Localization (GLIM, EKF, navsat) and navigation (Nav2): the same stack as on the robot. |
| `jo_sim/worlds/external` | A [collection of Gazebo worlds](https://github.com/leonhartyao/gazebo_models_worlds_collection). |
| `testudo` | Topic health checker (experimental). |

If you cloned without `--recurse-submodules`, run `git submodule update --init --recursive`.

## 2. Settings: `.env`

`.env` holds the build options and the runtime settings. The defaults work as they are. Nothing
secret lives there.

| Variable | Default | Effect |
|---|---|---|
| `BUILD_RTABMAP` | `false` | `true` builds RTAB-Map from source (slow, RAM hungry). Without it the localization stack runs without [visual odometry](../user-guide/visual-odometry.md). |
| `GLIM_ROS_REF` | `dev` | glim_ros2 branch, tag or commit baked into the image. |
| `GLIM_ROS_COMMIT` | a pinned commit | glim_ros2 commit applied on top. Changing it rebuilds only glim_ros (about a minute). |
| `DENDROS_VERSION` | `latest` | DendROS release installed in the image. |
| `BUILD_JOBS` | `8` | Parallel build jobs. |
| `CUDA_ARCHS` | `all-major` | CUDA architectures for gtsam_points. For example `120` (RTX 50xx only) builds faster. |
| `EXTRA_BUILD_PACKAGES` | empty | Extra workspace packages rebuilt at container start (for example `glim_ros`, see [Docker image](../developer/docker.md)). |
| `ROS_DOMAIN_ID` | `0` | ROS domain of the simulator. |
| `GZ_PARTITION` | `jo_sim` | Gazebo transport partition: keeps two simulators on the same machine apart. |

Full reference: [Configuration files](../reference/configuration.md).

## 3. Build and start

```bash
./jo up        # builds the image the first time, then starts the container
```

`./jo` runs `docker compose` for you; `docker compose up --build` works too. The first build
compiles GTSAM, gtsam_points (CUDA), GLIM, glim_ros2 and the RGL lidar plugin. It takes a while,
and the image is about 12 GB.

At every start, the container rebuilds the mounted packages (`jo_description`, `jo_sim`,
`jo_navigation`, `testudo`) with colcon. Shells opened in the meantime wait until it is done.

<figure class="jo-media">
<img src="../../assets/images/install_terminal.png" alt="Terminal: ./jo up starts the container, then ./jo shell waits for the workspace build and opens a shell in the container" loading="lazy">
<figcaption><code>./jo up</code> starts the container; <code>./jo shell</code> waits for the workspace build, then opens a shell in it.</figcaption>
</figure>

## 4. Check it

```bash
./jo shell          # bash inside the container
nvidia-smi          # the GPU is visible
sim_worlds          # the worlds that load by name
```

Next: [First run](first-run.md).

## Folders shared with the host

| Host | In the container | What |
|---|---|---|
| `user_worlds/` | `/home/ros/user_worlds` | Your worlds and sidecars, plus the world caches (downloaded models, `check_worlds` results). |
| `saved_maps/` | `/saved_maps` | GLIM (and RTAB-Map) maps. |
| `bags/` | `/home/ros/bags` | Rosbags. |
| `docker/utils/` | `/home/ros/utils` | Aliases, CycloneDDS config, DendROS settings. You can edit them without rebuilding. |
| `jo_sim/`, `jo_description/`, `jo_navigation/`, `testudo/` | `/home/ros/src/...` | The packages, rebuilt at container start or with `./jo build`. |
