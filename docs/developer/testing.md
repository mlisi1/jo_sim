# Testing

## The sandbox

Test runs use their own ROS domain and Gazebo partition, so they never disturb a simulation in use:

```bash
./jo --domain 77 --partition jo_sim_test sim --headless --no-rviz
./jo --domain 77 --partition jo_sim_test stop
```

`check_worlds --robot` uses its own partition, and domain 78.

## Stopping launches

- Stop launches **by process group**: `setsid ros2 launch ... &`, then `kill -INT -$PGID`.
- Jazzy's `ros2 run` doesn't forward SIGINT to the node.
- `pkill -f "gz sim"` also matches the shell that runs it.
- A loop started with `docker exec` keeps running in the container when the client is killed.

## Checks

- `check_worlds [--robot] [worlds...]`: worlds load, RTF, sensor rates, lidar returns, robot upright.
- `/sim/ground_truth/odom`: the reference for localization tests ([Ground truth](../user-guide/ground-truth.md)).
- `health_check` (Testudo): the topics against the robot interface. Experimental.

## Scenarios

`./jo --domain 77 --partition jo_sim_test scenario office_out_and_back` runs a mission headless and
exits 0 on pass and 1 on fail (see [Scenarios](../user-guide/scenarios.md)). Use one after any
change that can affect the robot's motion or localization.

!!! planned "Planned content (Phase E)"
    CI smoke runs. GitHub-hosted runners have no GPU, so they need a self-hosted runner.
