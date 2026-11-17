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

!!! planned "Planned content"
    - When a rebuild is needed, by kind of change (a table).
    - Recreating the container: what is lost (anything outside the mounted folders).
