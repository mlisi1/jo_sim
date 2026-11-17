# Performance

- **Watch the RTF** in the Gazebo GUI, or with `./jo ctl status`. Everything runs on sim time, so a
  low RTF slows the run down but doesn't break it.
- **A shared GPU:** GLIM, the RGL lidar and rendering all use the GPU. Other GPU jobs on the same
  machine lower the RTF (see [Troubleshooting](troubleshooting.md)). Check `nvidia-smi`.
- **Heavy worlds:** some Classic worlds run far below real time. Check with `check_worlds`.
- **Headless runs:** `--headless --no-rviz` saves rendering work.
- **Fewer sensors:** turn off what you don't need (`front_cam:=false back_cam:=false`).

!!! planned "Planned content"
    Measured RTF per world and mode, and the cost of each sensor.
