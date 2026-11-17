# Updating

```bash
git pull
git submodule update --init --recursive
./jo build          # rebuilds the mounted packages (jo_sim, jo_navigation, jo_description)
```

Rebuild the image only when the `Dockerfile` or the build options in `.env` change:

```bash
docker compose build && ./jo down && ./jo up
```

!!! tip "Following a new glim_ros2 commit"
    Set `GLIM_ROS_COMMIT` in `.env`, then run `docker compose build` (about a minute: only glim_ros
    is rebuilt) and `docker compose up -d`.

## When to rebuild

The mounted packages are built with `--symlink-install`, so most edits take effect at the next
launch with no rebuild.

| You changed | What to run |
|---|---|
| An existing launch file, YAML, RViz config, scenario, URDF/xacro or Python module | Nothing; relaunch |
| A world in `user_worlds/` (or a new one there) | Nothing; relaunch |
| A **new** file in `config/`, `launch/`, `rviz/`, `scenarios/` or `jo_sim/worlds/` | `./jo build` |
| C++ (`jo_sim/src/`: `frame_restamp`, `velodyne_emulation`, `depth_to_mm`, `WaypointMover`) | `./jo build` |
| A new script in `jo_sim/scripts/` or a `CMakeLists.txt` | `./jo build` |
| A submodule (`git pull` + `git submodule update`) | `./jo build` |
| `testudo` | `./jo down && ./jo up` (it's built at container start, not by `./jo build`) |
| `GLIM_ROS_COMMIT` in `.env` | `docker compose build && docker compose up -d` (about a minute) |
| Any other build option in `.env`, or the `Dockerfile` | `docker compose build && ./jo down && ./jo up` |
| A runtime setting in `.env` (`ROS_DOMAIN_ID`, `GZ_PARTITION`, PRIME variables) | `./jo down && ./jo up` |

## Recreating the container

`./jo down` removes the container. These folders are mounted from the host, so they survive:
`jo_description/`, `jo_navigation/`, `jo_sim/`, `testudo/`, `docker/utils/`, `user_worlds/`,
`saved_maps/` and `bags/`.

Everything else in the container is lost:

- the colcon `build/`, `install/` and `log/` folders (they are rebuilt at the next start, so the
  first shell waits for the build);
- `~/.ros` logs and shell history;
- the last GLIM map dump in `/tmp/dump` (save maps to `saved_maps/` first, see
  [GLIM maps](../user-guide/glim-maps.md));
- anything installed by hand with `apt` or `pip`: put it in the `Dockerfile` instead.
