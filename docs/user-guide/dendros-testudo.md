# DendROS and Testudo

## DendROS

[DendROS](https://mlisi1.github.io/DendROS) colours ROS 2 terminal output by node group, and has
a full-screen launch TUI. It is installed in the image, and `ros2` in the container shell goes
through it.

- Package config: `jo_sim/config/dendROS.yaml`.
- Global settings: `docker/utils/dendROS/defaults.yaml`, mounted, so it can be edited without a
  rebuild.

<figure class="jo-media">
<img src="https://raw.githubusercontent.com/mlisi1/DendROS/main/docs/assets/images/screenshots/showcase.gif" alt="DendROS TUI mode: filtering a live launch, colorized ros2 CLI, and remote commands" loading="lazy">
<figcaption>DendROS's TUI: filtering a live launch, the coloured <code>ros2</code> CLI and remote
commands (from the <a href="https://github.com/mlisi1/DendROS">DendROS repository</a>).</figcaption>
</figure>

## Testudo (experimental)

`health` (a live TUI, on sim time) checks the topics against `jo_sim/config/testudo.yaml`: the
robot interface the simulator must expose. Give it some seconds, because rates and staleness need
time. Topics that publish only on events read `◌ idle`, and inputs nobody publishes read `◌ input`.

<figure class="jo-media">
<img src="https://raw.githubusercontent.com/mlisi1/testudo/main/docs/assets/media/tui/dashboard.png" alt="The Testudo dashboard" loading="lazy">
<figcaption>The Testudo dashboard (from the <a href="https://github.com/mlisi1/testudo">Testudo
repository</a>).</figcaption>
</figure>

`health_headless` runs the same session without the TUI, for scripts and agents. It publishes the
results until it's stopped: `/testudo/overall` (the verdict), `/testudo/<plugin>` and
`/testudo/vitals` (one row per topic). On the full stack, with the robot idle, every check is OK except one warning: `IMU-008` on `/imu/data`,
because the simulated IMU reports an all-zero orientation covariance.

Testudo has no one-shot check any more. For a report with an exit code, record a bag and run
`ros2 run testudo testudo replay <bag>`, which exits 0, 1 or 2.

<figure class="jo-media">
<img src="https://raw.githubusercontent.com/mlisi1/testudo/main/docs/media/testudo_replay.gif" alt="testudo replay on a bag" loading="lazy">
<figcaption><code>testudo replay</code> on a bag (from the Testudo repository).</figcaption>
</figure>
