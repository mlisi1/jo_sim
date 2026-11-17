# Launch files

```mermaid
flowchart TD
  SB["sim_bringup.launch.py<br/>(= jo_bringup)"] --> LS["launch_sim.launch.py"]
  SB --> L["jo_navigation: localization*.launch.py"]
  SB --> N["jo_navigation: navigation_*.launch.py"]
  LS --> GZ["ros_gz_sim gz_sim.launch.py<br/>(patched world)"]
  LS --> D["jo_description: description.launch.py"]
  LS --> BR["bridges (per sensor flag)"]
  LS --> DE["driver_emulation.launch.py"]
  LS --> SP["ros_gz_sim create<br/>(spawn jo)"]
```

- **`sim_bringup.launch.py`:** the robot's entry point, with the same flags and defaults as
  `jo_bringup`. It includes `launch_sim` and the stack, and computes the navsat yaw offset from the
  resolved spawn yaw.
- **`launch_sim.launch.py`:** resolves the world and its settings (command line > sidecar >
  defaults), writes the patched world, then starts Gazebo, the clock bridge, the spawn, the bridges
  and driver emulation.
- **`driver_emulation.launch.py`:** the driver parts; follows the sensor flags.

!!! planned "Planned content (G3)"
    A line-by-line walkthrough, and how to add an argument end to end.
