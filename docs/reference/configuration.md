# Configuration files

| File | What |
|---|---|
| `.env` | Build options and runtime settings. See [Install](../getting-started/install.md#2-settings-env). |
| `compose.yaml` | The container: GPU, X11, host network and IPC, mounts, environment. |
| `docker/utils/utilities.sh` | Aliases, and waiting for the entrypoint build. |
| `docker/utils/cyclonedds.xml` | CycloneDDS: 100 participants per domain. |
| `docker/utils/dendROS/defaults.yaml` | DendROS global settings. |
| `jo_sim/config/bridge/*.yaml` | ros_gz_bridge configs ([Bridges](../developer/bridges.md)). |
| `jo_sim/config/dendROS.yaml` | DendROS node groups for jo_sim. |
| `jo_sim/config/testudo.yaml` | The robot interface, for Testudo. |
| `jo_sim/rviz/sim.rviz` | RViz config for the sensors. |
| `jo_navigation/config/glim/glim_config_bunker_sim/` | GLIM config for the sim ([Sim vs robot configs](../developer/sim-vs-robot.md)). |
| `jo_description/urdf/sim_noise.xacro` | Sensor noise values. |
| `<world>.yaml` | World sidecar ([Worlds](../user-guide/worlds.md#the-sidecar-yaml)). |
