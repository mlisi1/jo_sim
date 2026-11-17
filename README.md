

# Jo Sim
[![ROS 2 Jazzy](https://img.shields.io/badge/ROS%202-Jazzy-34C759?style=flat-square&logo=ros)](https://docs.ros.org/)
[![Gazebo Harmonic](https://img.shields.io/badge/Gazebo-Harmonic-FF6B35?style=flat-square&logo=gazebo)](https://gazebosim.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![Ubuntu 24.04](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?style=flat-square&logo=ubuntu)](https://ubuntu.com/)
[![Nav2](https://img.shields.io/badge/Nav2-Latest-4285F4?style=flat-square&logo=ros)](https://navigation.ros.org/)

A comprehensive ROS 2 robot description package for the Jo tracked robot platform, featuring complete robot modeling, simulation, and navigation capabilities using Gazebo (Harmonic) and ROS 2 Jazzy.

<div align="center">
  <img src="res/description.png" alt="Jo Overview" height="400"/>
</div>


## Key Features

- **Complete URDF/Xacro Model**
- **Gazebo Harmonic Simulation**
- **Sensor Suite**:
  - Velodyne LiDAR (3D point cloud)
  - Front and back depth cameras (RGB-D)
  - IMU sensor for orientation/acceleration
  - Track simulation
- **Navigation Ready**: Pre-configured Nav2 stack for autonomous (mapless) navigation 
- **Docker Support**: Full containerized environment with GPU acceleration
- **RViz Visualization**: Pre-configured visualization configs for display, simulation, and navigation


## Packages
+  ```jo_description``` - URDF model of the robot, complete with sensors
+ ```jo_sim``` - Simulation package: Gazebo world, robot, sensor bridges, driver emulation and the jo_bringup-equivalent launch
+ ```jo_navigation``` - Package containing configs and launch files for localization and navigation



# Quick Start

**Documentation: https://mlisi1.github.io/jo_sim**: install, usage, worlds, sensors, the developer
guide and the agent guide.

Requirements: Linux with X11, an NVIDIA GPU with its driver, Docker and the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

```bash
git clone --recurse-submodules -b dev https://github.com/mlisi1/jo_sim.git && cd jo_sim
./jo sim                         # builds the image the first time; office_cpr, Gazebo GUI + RViz
./jo sim -n local                # + GLIM/EKF localization and Nav2 (= full_navigation)
./jo sim -w small_city -n gps    # GPS navigation (= full_gps_navigation)
./jo help
```

The simulator exposes the **same ROS interface as the real robot** (jo-zotac), so the stack in
`jo_navigation` runs on it unchanged with `use_sim_time:=true`.

See [PLAN.md](PLAN.md) for the roadmap, and [AGENTS.md](AGENTS.md) if you are an agent.

## Additional Resources

- [ROS 2 Documentation](https://docs.ros.org/)
- [Gazebo Documentation](https://gazebosim.org/)
- [Navigation2 Documentation](https://navigation.ros.org/)
- [URDF Documentation](http://wiki.ros.org/urdf)
- [ROS 2 Control Documentation](https://control.ros.org/)

