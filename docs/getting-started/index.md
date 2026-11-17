# Getting started

This section takes you from a fresh machine to Jo driving autonomously in a simulated world.

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } __[Install](install.md)__

    ---

    Requirements, clone, and the first image build.

-   :material-play-circle:{ .lg .middle } __[First run](first-run.md)__

    ---

    `./jo sim`: Gazebo, RViz, driving the robot.

-   :material-map-marker-path:{ .lg .middle } __[Navigation in the sim](navigation.md)__

    ---

    `full_navigation` and `full_gps_navigation`: GLIM, EKF, Nav2 goals.

-   :material-update:{ .lg .middle } __[Updating](updating.md)__

    ---

    Pull, submodules, rebuild.

</div>

## Requirements

| | Needed | Notes |
|---|---|---|
| OS | Linux with X11 | Developed on Ubuntu 24.04. The GUI windows (Gazebo, RViz, GLIM viewer) open on the host's X server. |
| GPU | NVIDIA, with the proprietary driver | Used by the lidar simulation (RGL), GLIM (CUDA) and rendering. There is no CPU-only mode yet ([Phase F](../developer/roadmap.md)). |
| Docker | Docker Engine, usable without `sudo` | [Install guide](https://docs.docker.com/engine/install/ubuntu/), [non-root setup](https://docs.docker.com/engine/install/linux-postinstall/). |
| NVIDIA Container Toolkit | yes | [Install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). |
| Disk | ~12 GB for the image | Plus maps, bags and downloaded world models. |
| RAM | 16 GB or more recommended | The image build and the full stack are memory hungry, especially with `BUILD_RTABMAP=true`. |

!!! tip "NVIDIA driver"
    A guide to installing the driver on Ubuntu:
    [NVIDIA-Ubuntu-Driver-Guide](https://github.com/oddmario/NVIDIA-Ubuntu-Driver-Guide).
    Check it with `nvidia-smi` on the host, and later inside the container.
