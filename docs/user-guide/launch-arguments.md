# Launch arguments

There are two entry points:

| Launch file | Alias | Role |
|---|---|---|
| `sim_bringup.launch.py` | `sensors`, `full_sensors`, `full_navigation`, `full_gps_navigation`; used by `./jo sim` | The equivalent of the robot's `jo_bringup.launch.py`: the same flags, plus the stack from `jo_navigation`. |
| `launch_sim.launch.py` | `sim` | World, robot, bridges and driver emulation only, no stack. |

Pass arguments as `name:=value`, to `ros2 launch` or after `./jo sim`.

!!! warning "Different sensor defaults"
    `sim_bringup` uses the robot's defaults: `imu` and `lidar` on, `gnss`, `front_cam` and
    `back_cam` off. `launch_sim` (the `sim` alias) turns every sensor on.

## Robot flags (same as `jo_bringup`)

`sim_bringup.launch.py` declares them with the robot's names and defaults.

--8<-- "docs/includes/generated/launch_args_robot.md"

## Simulator arguments

Declared by `launch_sim.launch.py`. Through `sim_bringup` and `./jo sim` they are passed as
`name:=value`.

--8<-- "docs/includes/generated/launch_args_sim.md"

## Stack arguments

Declared by the `jo_navigation` launch files that `sim_bringup` includes. They are passed through
unchanged.

--8<-- "docs/includes/generated/launch_args_stack.md"

!!! info "Generated tables"
    These tables come from `ros2 launch ... --show-args`, through `docs/gen/gen_tables.py`.
    Run it again after changing a launch argument.
