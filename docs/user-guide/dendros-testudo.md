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

`health` (a live TUI, on sim time) checks the topics against `jo_sim/config/testudo.yaml`: the
robot interface the simulator must expose. Give it some seconds, because rates and staleness need
time. Topics that publish only on events read `◌ idle`, and inputs nobody publishes read `◌ input`.

`health_headless` runs the same session without the TUI, for scripts and agents. It publishes the
results until it's stopped: `/testudo/overall` (the verdict), `/testudo/<plugin>` and
`/testudo/vitals` (one row per topic). On the full stack, with the robot idle, every check is OK.

Testudo has no one-shot check any more. For a report with an exit code, record a bag and run
`ros2 run testudo testudo replay <bag>`, which exits 0, 1 or 2.
