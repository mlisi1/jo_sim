# Performance

- **Watch the RTF** in the Gazebo GUI, or with `./jo ctl status`. Everything runs on sim time, so a
  low RTF slows the run down but doesn't break it.
- **A shared GPU:** GLIM, the RGL lidar and rendering all use the GPU. Other GPU jobs on the same
  machine lower the RTF (see [Troubleshooting](troubleshooting.md)). Check `nvidia-smi`.
- **Heavy worlds:** some Classic worlds run far below real time. Check with `check_worlds`.
- **Headless runs:** `--headless --no-rviz` saves rendering work.
- **Fewer sensors:** turn off what you don't need (`front_cam:=false back_cam:=false`).

## Measured cost per sensor and mode

Measured with `python3 docs/gen/measure_performance.py` on 2026-11-17, on a laptop with an Intel
Core Ultra 9 275HX (24 threads) and an RTX 5070 Laptop GPU (8 GB), with nothing else running. RTF
is the sim time gained over a 30 s wall-clock window; CPU cores are the launch's own processes.

| Configuration | RTF | CPU cores | GPU memory [GiB] |
|---|---|---|---|
| Gazebo and the robot, no sensors | 1.00 | 0.9 | 1.2 |
| + lidar only | 1.00 | 1.1 | 1.2 |
| + IMU and GNSS only | 1.00 | 1.0 | 1.2 |
| + one RealSense only | 1.00 | 2.3 | 1.3 |
| All sensors (`--nav none`) | 0.99 | 4.0 | 1.3 |
| All sensors, no cameras | 1.00 | 1.2 | 1.2 |
| All sensors + GLIM, EKF, Nav2 (`--nav local`) | 0.93 | 5.2 | 1.6 |
| All sensors + GPS stack (`--nav gps`) | 0.99 | 5.3 | 1.6 |

World `office_cpr`, headless, without RViz.

- **The cameras are the expensive sensors:** about 1.4 CPU cores each (rendering, the bridges, the
  depth conversion and the 30 Hz clouds). The two cameras are about 70 % of the simulator's
  CPU use.
- **The lidar is cheap:** RGL ray-casts on the GPU (+0.2 cores). The IMU and GNSS cost almost nothing.
- **The stack** adds about 1.2 cores and 0.3 GiB of GPU memory.
- **If the RTF drops,** turn the cameras off first (`front_cam:=false back_cam:=false`), unless you
  need them.

The GUI and RViz add rendering on top of this. For the RTF of each world, see the
[worlds table](worlds.md): it puts every world in a class (good, usable, too slow, unusable).
