# Troubleshooting

??? failure "`rmw_create_node: failed to create domain`"
    CycloneDDS's default limit is 32 participants per domain, too few for the full GPS stack. The
    container's `docker/utils/cyclonedds.xml` raises it to 100. If you use your own
    `CYCLONEDDS_URI`, raise the limit there too.

??? failure "The DendROS TUI does not start; I get plain coloured output"
    The terminal reports 8 colours: `docker exec -it` sets `TERM=xterm`. Use `./jo`, which passes
    your `TERM`, or run `docker exec -it -e TERM=$TERM ...`.

??? failure "A closed terminal left the simulation running"
    Run `./jo stop` (add `--domain` and `--partition` if you started it with them).

??? failure "RTF far below 1"
    Another GPU or CPU heavy job is running (check `nvidia-smi`, `uptime`), or the world is heavy
    (check `check_worlds`).

??? failure "Big worlds: nothing on sim time starts"
    Fixed: the clock is bridged from the world's own clock topic, not the root `/clock`. If you
    write your own bridge, do the same (see [Design decisions](../developer/decisions.md)).

??? failure "Lag on an external monitor"
    On laptops with reverse PRIME (HDMI on the NVIDIA GPU, desktop on the Intel one), the external
    monitor can lag. The cause is the display setup, not the simulator.

??? failure "Two simulators see each other's topics, or the clock jumps"
    With `network_mode: host`, every container on the machine shares the network. Give each
    simulator its own ROS domain and Gazebo partition:
    `./jo --domain 42 --partition my_test sim ...`. The defaults (domain 0, partition `jo_sim`) are
    for your main session. See [Multiple simulations](multiple-simulations.md).

??? failure "A script I started with `docker exec` is still running after I killed the terminal"
    Killing the `docker exec` client doesn't stop the process inside the container. Use `./jo stop`
    (with the same `--domain` and `--partition`), or find it with `./jo shell` and `ps` and kill its
    process group.

??? failure "Ctrl+C or `kill` on `ros2 run ...` doesn't stop the node"
    In Jazzy, `ros2 run` doesn't forward SIGINT to the node. Signal the process group:
    `kill -INT -<pgid>` (the PGID is shown by `ps -eo pid,pgid,cmd`).

??? failure "`exec ros2 ...` fails in a script: command not found"
    In the container `ros2` is a shell function (DendROS wraps it), so `exec` can't find it. Call
    `ros2 ...` without `exec`, or use `/opt/ros/jazzy/bin/ros2`.

??? failure "`health` fails in a script or over `docker exec` without `-t`"
    `health` (`testudo watch`) is a TUI and needs a terminal. In scripts, use `health_headless`: it
    publishes the results on `/testudo/*`.

??? failure "The lidar doesn't see a Gazebo actor"
    Gazebo actors are invisible to the RGL lidar. Use moving obstacles instead: models moved by the
    `WaypointMover` system, through `obstacles:=file.yaml` (see [Scenarios](scenarios.md)).

??? failure "A world doesn't load, or loads without a lidar"
    Many of the external worlds are a Gazebo Classic collection. The
    [worlds table](worlds.md) lists which ones work with the robot; `./jo check --robot NAME`
    tests one.

??? failure "GLIM diverges at startup"
    Not seen in 34 test starts since the spawn drop was fixed. If you see it, note the world and
    whether the GUI or RViz were open, and keep the launch log (the GLIM
    `initial IMU state estimation result` lines). Then report it.

??? failure "My GLIM map is gone"
    The dump in `/tmp/dump` is overwritten by the next run and lost when the container is
    recreated. Save it to `saved_maps/` (see [GLIM maps](glim-maps.md)).

??? failure "`pip install` in the container fails on Pygments"
    Debian's system Pygments can't be replaced. Use `pip install --user`.
