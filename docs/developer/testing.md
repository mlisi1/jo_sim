# Testing

## The sandbox

Test runs use their own ROS domain and Gazebo partition, so they never disturb a simulation in use:

```bash
./jo --domain 77 --partition jo_sim_test sim --headless --no-rviz
./jo --domain 77 --partition jo_sim_test shell   # ros2 commands on the sandbox's domain
./jo --domain 77 --partition jo_sim_test stop
```

A plain `./jo shell` opens on the container's default domain, so it doesn't see the sandbox. `stop`
can report two launches for one simulation, and waits up to 30 s for them to exit.

`check_worlds --robot` uses its own partition, and domain 78.

## Stopping launches

- Stop launches **by process group**: `setsid ros2 launch ... &`, then `kill -INT -$PGID`.
- Jazzy's `ros2 run` doesn't forward SIGINT to the node.
- `pkill -f "gz sim"` also matches the shell that runs it.
- A loop started with `docker exec` keeps running in the container when the client is killed.

## Checks

- `check_worlds [--robot] [worlds...]`: worlds load, RTF, sensor rates, lidar returns, robot upright.
- `/sim/ground_truth/odom`: the reference for localization tests ([Ground truth](../user-guide/ground-truth.md)).
- `health` (Testudo, live TUI): the topics against the robot interface. Let it run for a while, because rates and staleness need time.

## Scenarios

`./jo --domain 77 --partition jo_sim_test scenario office_out_and_back` runs a mission headless and
exits 0 on pass and 1 on fail (see [Scenarios](../user-guide/scenarios.md)). Use one after any
change that can affect the robot's motion or localization.

## CI

Only the docs build runs in CI (`mkdocs build --strict`). The simulator has no CI: GitHub-hosted
runners have no GPU, and a self-hosted GPU runner isn't worth its upkeep for this project (the
maintainer's decision, 2026-11-17).

So, before pushing a change that can affect motion, localization or the robot interface, run by
hand in a sandbox:

1. `./jo --domain 77 --partition jo_sim_test scenario office_out_and_back`, `office_crossing` and `city_gps`:
   all must pass.
2. `health` on the full stack: every topic green.
3. If you changed a world patch: `./jo check --robot` on the worlds it touches.
