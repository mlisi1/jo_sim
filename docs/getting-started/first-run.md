# First run

## Start the simulator

```bash
./jo sim
```

This starts the default world, `office_cpr`, spawns Jo with all its sensors, and opens the Gazebo
GUI and RViz. The Gazebo camera follows the robot.

<div class="media-ph" data-kind="image" markdown>
<span class="media-ph-kind">Image</span>
<p>Annotated screenshot of the Gazebo GUI with Jo in office_cpr: play/pause/step, the RTF readout,
the entity tree, camera follow.</p>
</div>

<div class="media-ph" data-kind="image" markdown>
<span class="media-ph-kind">Image</span>
<p>Annotated screenshot of RViz (<code>sim.rviz</code>): the lidar cloud (Style: Points), the camera
images, the camera clouds, the TF tree.</p>
</div>

## Drive the robot

In a second terminal:

```bash
./jo shell
teleop            # teleop_twist_keyboard, publishing /cmd_vel with sim time
```

<div class="media-ph" data-kind="video" markdown>
<span class="media-ph-kind">Video</span>
<p>Driving Jo with teleop: Gazebo on the left, RViz on the right, the lidar cloud moving.</p>
</div>

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
