# First run

## Start the simulator

```bash
./jo sim
```

This starts the default world, `office_cpr`, spawns Jo with all its sensors, and opens the Gazebo
GUI and RViz. The Gazebo camera follows the robot.

<figure class="jo-media">
<img src="../../assets/images/gazebo_gui.jpg" alt="The Gazebo GUI with Jo in office_cpr, with numbered markers" loading="lazy">
<figcaption>The Gazebo GUI.</figcaption>
</figure>

1. **Play/pause, step and reset.** `./jo ctl` does the same from a terminal (see
   [Simulation control](../user-guide/sim-control.md)).
2. **The real-time factor**, in percent. Below 100 % the simulation runs slower than real time,
   but everything is on sim time, so nothing breaks.
3. **The entity tree:** the world's models, and `jo`, the robot.
4. **The view follows Jo** (`follow:=false` turns it off). Drag to orbit, scroll to zoom.

<figure class="jo-media">
<img src="../../assets/images/rviz_sim.jpg" alt="RViz with the lidar cloud, the camera clouds and the camera images, with numbered markers" loading="lazy">
<figcaption>RViz with <code>sim.rviz</code>.</figcaption>
</figure>

1. **The lidar cloud** (`/velodyne_points`), coloured by height: the 16 rings of the VLP-16.
2. **The camera clouds** (`/<cam>_camera/camera/depth/color/points`), in the colours of the scene.
3. **The robot model**, from `/robot_description`. The fixed frame is `base_footprint`, so the view
   moves with Jo.
4. **The colour images** of the back and front cameras.
5. **The displays:** turn each sensor on or off here. The TF display is off by default.

## Drive the robot

In a second terminal:

```bash
./jo shell
teleop            # teleop_twist_keyboard, publishing /cmd_vel with sim time
```

<figure class="jo-media">
<video src="../../assets/videos/teleop.mp4" poster="../../assets/videos/teleop.jpg" controls muted loop playsinline preload="none"></video>
<figcaption>Driving Jo in office_cpr: Gazebo on the left, RViz on the right (the lidar cloud and the
two cameras). Here the commands come from a script; <code>teleop</code> publishes the same <code>/cmd_vel</code>.</figcaption>
</figure>

The base takes `/cmd_vel`, as the Bunker driver does on the robot. Like the real robot, it publishes
**no wheel odometry**.

## Useful variants

```bash
./jo sim -w small_city            # another world (./jo worlds lists them)
./jo sim --headless --no-rviz     # no windows at all
./jo sim --paused                 # start paused, then: ./jo ctl play
./jo sim --no-noise               # sensors without noise
./jo sim x:=2.0 y:=-1.0 yaw:=1.57 # spawn pose (name:=value goes to the launch file)
```

All options: [The ./jo wrapper](../user-guide/jo-cli.md).

## Stop it

Press ++ctrl+c++ in the terminal that runs `./jo sim`. If that terminal was closed, the launch keeps
running in the container. Stop it with:

```bash
./jo stop
```

Next: [Navigation in the sim](navigation.md).
