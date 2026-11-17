# Glossary

Bunker
:   The tracked base of Jo (AgileX Bunker).

GLIM
:   GPU-accelerated LiDAR-IMU odometry and mapping ([koide3/glim](https://github.com/koide3/glim)).
    Jo uses the [mlisi1/glim_ros2](https://github.com/mlisi1/glim_ros2) fork of its ROS wrapper.

jo-zotac
:   The software repository of the real robot. It is the reference for the ROS interface.

Partition (Gazebo)
:   `GZ_PARTITION`: separates the Gazebo transport topics of simulations on the same host.

RGL
:   Robotec GPU Lidar, the Gazebo plugin that ray-casts the Velodyne on the GPU.

RTF
:   Real-time factor: simulated time over wall-clock time.

Sidecar
:   `<world>.yaml` next to a world (or in `user_worlds/`): spawn poses, GNSS datum, description.

Sim time
:   The simulated clock (`/clock`). Every node runs with `use_sim_time:=true`.
