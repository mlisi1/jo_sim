---
title: jo_sim
hide:
  - navigation
  - toc
---

<div class="jo-hero" markdown>

# jo<span class="jo-accent">_sim</span>

<p class="jo-tagline">The simulator of <strong>Jo</strong>, a tracked field robot. It exposes the
<strong>same ROS 2 interface as the real robot</strong>: topics, message types, frame ids, TF
ownership and rates. So the real navigation stack runs on it unchanged.</p>

[Get started :material-rocket-launch:](getting-started/index.md){ .md-button .md-button--primary }
[Develop the sim :material-wrench:](developer/index.md){ .md-button }
[For agents :material-robot:](agents.md){ .md-button }

<div class="jo-badges">
<span class="jo-badge">ROS 2 Jazzy</span>
<span class="jo-badge">Gazebo Harmonic</span>
<span class="jo-badge">GLIM (GPU)</span>
<span class="jo-badge">Nav2</span>
<span class="jo-badge">Docker + NVIDIA</span>
<span class="jo-badge">51 worlds</span>
</div>

</div>

<div class="media-ph" data-kind="video" markdown>
<span class="media-ph-kind">Video</span>
<p>Hero reel (~30 s): <code>./jo sim -n local</code> in office_cpr. Gazebo and RViz side by side,
the GLIM map growing, a Nav2 goal reached. Then a GPS goal in a city world.</p>
</div>

## What you get

<div class="grid cards" markdown>

-   :material-radar:{ .lg .middle } __The robot's sensors, as the drivers publish them__

    ---

    The Velodyne VLP-16 (with `ring` and `time` fields), the Xsens IMU and GNSS, and two RealSense
    D456 cameras. Topics, frames and noise match the real drivers.

    [:octicons-arrow-right-24: Sensors](user-guide/sensors.md)

-   :material-map-marker-path:{ .lg .middle } __The real stack, unchanged__

    ---

    GLIM, the EKF, navsat_transform and Nav2 from `jo_navigation` run on top of the simulator, with
    `use_sim_time:=true`. They are started by the same commands as on the robot:
    `full_navigation` and `full_gps_navigation`.

    [:octicons-arrow-right-24: Navigation in the sim](getting-started/navigation.md)

-   :material-earth:{ .lg .middle } __Drop-in worlds__

    ---

    51 worlds load by name, including Gazebo Classic worlds, which are patched automatically.
    Add your own in `user_worlds/`, with a small sidecar yaml for spawn poses and the GNSS datum.

    [:octicons-arrow-right-24: Worlds](user-guide/worlds.md)

-   :material-console:{ .lg .middle } __One command from the host__

    ---

    `./jo sim -w small_city -n gps` starts the container, the world, the robot and the stack.
    Pause, step and RTF control, headless runs, and two simulations side by side.

    [:octicons-arrow-right-24: The ./jo wrapper](user-guide/jo-cli.md)

-   :material-target:{ .lg .middle } __Ground truth__

    ---

    `/sim/ground_truth/odom` gives the true pose at 100 Hz, to measure GLIM, EKF and
    RTAB-Map drift. It is outside the robot interface: the stack never sees it.

    [:octicons-arrow-right-24: Ground truth](user-guide/ground-truth.md)

-   :material-source-branch:{ .lg .middle } __Built to be extended__

    ---

    Architecture, invariants, how-to recipes and design decisions, for humans and agents.

    [:octicons-arrow-right-24: Developer guide](developer/index.md)

</div>

## The guiding principle

!!! quote ""
    The simulator exposes **the same ROS interface as the real robot** (`jo-zotac@dev`) and nothing
    more. Gazebo replaces the drivers, so the simulator also emulates the parts of the drivers that
    are not the sensor itself, such as the RealSense TF tree.
    `jo_description` must keep working on the robot.

That rule decides most design questions. See [Invariants](developer/invariants.md) and
[Design decisions](developer/decisions.md).

<div class="media-ph" data-kind="image" markdown>
<span class="media-ph-kind">Image</span>
<p>Jo in Gazebo (office_cpr), next to a photo of the real robot.</p>
</div>

## Where to go

| You want to… | Start at |
|---|---|
| run the simulator and drive the robot | [Getting started](getting-started/index.md) |
| test navigation, GPS or GLIM in the sim | [Navigation in the sim](getting-started/navigation.md) |
| add a world or a spawn pose | [Worlds](user-guide/worlds.md) |
| change a sensor, a bridge or the image | [Developer guide](developer/index.md) |
| work on it as an AI agent | [For agents](agents.md), or read [`llms-full.txt`](https://mlisi1.github.io/jo_sim/llms-full.txt) |
