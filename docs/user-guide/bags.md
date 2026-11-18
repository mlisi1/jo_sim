# Recording bags

Bags go to `/home/ros/bags` in the container, which is `bags/` on the host. With a simulation
running, open a shell with `./jo shell` and record:

```bash
ros2 bag record --all --use-sim-time -s mcap -o /home/ros/bags/my_run \
  --exclude-regex '(scanend|theora|compressedDepth|depth_.*/image_raw/compressed|image_rect_raw/compressed|/image_raw$|/image_rect_raw$|/depth/color/points$|^/sim/.*_raw$)'
```

Press ++ctrl+c++ to stop. Wait for the command to exit: a bag that is cut off has no metadata, and
`ros2 bag info` can't read it.

The filter leaves out raw images, the cameras' point clouds and the simulator's raw sensor topics.
It keeps `/clock`, `/tf`, the lidar, the IMU, the compressed images and the ground truth.

!!! warning "Watch the disk"
    With the front camera on, this filter recorded about 23 MB per second of sim time. The cameras'
    point clouds are the heaviest topics: without `/depth/color/points$` in the filter, the same
    setup wrote over 200 MB per second.

!!! note "Scenarios record for you"
    `./jo scenario NAME --record compressed` records a mission with the robot's profiles. See
    [Scenarios](scenarios.md).

## Play a bag back

Stop the simulation first (`./jo stop`), so that two clocks aren't publishing at once:

```bash
ros2 bag info /home/ros/bags/my_run
ros2 bag play /home/ros/bags/my_run --clock
```

`--clock` publishes the recorded `/clock`. Nodes you run on top of the bag need `use_sim_time:=true`.
