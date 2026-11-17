# The `./jo` wrapper

`./jo` runs on the host. It starts the container when needed (building the image the first time)
and runs the command inside it, through the container's interactive shell. So the aliases and
DendROS's formatting apply exactly as in a container shell.

```text
usage: ./jo [--domain N] [--partition NAME] <command> [args]

  --domain N, --partition NAME   ROS_DOMAIN_ID / GZ_PARTITION for the command (default: the
                                 container's, from .env); e.g. a second, separate simulation

  sim [options] [name:=value ...]   launch the simulator (sim_bringup.launch.py)
      -w, --world NAME      world name or path (default: office_cpr; ./jo worlds lists them)
      -n, --nav MODE        none (sensors only, default) | local (= full_navigation)
                            | gps (= full_gps_navigation)
      -s, --spawn NAME      named spawn pose from the world's sidecar yaml
      --headless            no Gazebo GUI
      --no-rviz             no RViz
      --paused              start paused (play in the GUI, or ./jo ctl play)
      --rtf X               target real-time factor (0 = as fast as possible)
      --no-noise            sensor noise off
      --glim-view           open GLIM's viewer window (-n local or gps)
      name:=value           passed to the launch file as is (x:=2.0 yaw:=1.57 glim_view:=true ...)
  shell                     bash in the container
  stop                      stop the running simulation (e.g. left running by a closed terminal)
  up | down                 start (building the image the first time) / stop the container
  build                     colcon build of the mounted packages (jo_sim jo_navigation jo_description)
  worlds                    list the worlds (sim_worlds)
  check [args]              check_worlds, e.g. ./jo check --robot office_cpr
  ctl play|pause|step [N]|status   control the running simulation
```

## Examples

```bash
./jo sim -w small_city -n gps
./jo sim --headless --paused --rtf 0 -n local x:=2.0
./jo ctl step 100
./jo --domain 77 --partition test sim --headless    # alongside another simulation
./jo --domain 77 --partition test stop
```

## Stopping

++ctrl+c++ stops the launch and every process it started. If the terminal is closed instead, the
launch keeps running in the container. `./jo stop` signals the process group of every
`ros2 launch jo_sim` on the current Gazebo partition. Anything still alive after 30 s is killed
with SIGKILL.

!!! info "Terminal colours"
    `./jo` passes your terminal's `TERM` to the container. A plain `docker exec -it` sets
    `TERM=xterm` (8 colours), where DendROS's TUI cannot start and falls back to its classic output.
