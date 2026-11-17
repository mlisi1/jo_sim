# The `./jo` wrapper

`./jo` runs on the host. It starts the container when needed (building the image the first time)
and runs the command inside it, through the container's interactive shell. So the aliases and
DendROS's formatting apply exactly as in a container shell.

--8<-- "docs/includes/generated/jo_help.md"

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
