# DendROS and Testudo

## DendROS

[DendROS](https://mlisi1.github.io/DendROS) colours ROS 2 terminal output by node group, and has
a full-screen launch TUI. It is installed in the image, and `ros2` in the container shell goes
through it.

- Package config: `jo_sim/config/dendROS.yaml`.
- Global settings: `docker/utils/dendROS/defaults.yaml`, mounted, so it can be edited without a
  rebuild.

<div class="media-ph" data-kind="image" markdown>
<span class="media-ph-kind">Image</span>
<p>The DendROS launch TUI running <code>full_navigation</code>.</p>
</div>

## Testudo (experimental)

`health` (live TUI) and `health_check` (one-shot report) check the topics against
`jo_sim/config/testudo.yaml`: the robot interface the simulator must expose.

!!! warning
    Not reliable on the full stack yet.
