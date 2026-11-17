# Navigation in the sim

The simulator runs the robot's own stack from `jo_navigation`, started by the same aliases as on
the robot (jo-zotac).

| Mode | `./jo` | Inside the container | What runs |
|---|---|---|---|
| Sensors only | `./jo sim` | `sim` | World, robot, sensors, RViz |
| Local navigation | `./jo sim -n local` | `full_navigation` | Front and back cameras, GLIM + EKF localization, Nav2 (mapless), RViz |
| GPS navigation | `./jo sim -n gps` | `full_gps_navigation` | The above, plus GNSS, navsat_transform and GPS navigation |

`--glim-view` (or `glim_view:=true`) also opens GLIM's own viewer window.

## Local navigation

```bash
./jo sim -n local
```

Wait for `Managed nodes are active` in the output, then send a goal with RViz's
**2D Goal Pose** tool.

<figure class="jo-media">
<video src="../../assets/videos/nav_local.mp4" poster="../../assets/videos/nav_local.jpg" controls muted loop playsinline preload="none"></video>
<figcaption>Local navigation in office_cpr: a goal 4.5 m down the corridor, then back. RViz shows the
costmaps, the planned path and the lidar. The goals go to <code>/goal_pose</code>, as the 2D Goal Pose
tool does.</figcaption>
</figure>

The lidar starts 2 s (sim time) after spawn. The robot is spawned slightly above the ground and
drops, and GLIM must initialize with the robot at rest.

## GPS navigation

```bash
./jo sim -w small_city -n gps
```

<div class="media-ph" data-kind="video" markdown>
<span class="media-ph-kind">Video</span>
<p>GPS navigation in a city world: a GPS goal, the robot following it, the navsat-derived pose.</p>
</div>

Worlds without `<spherical_coordinates>` get a GNSS datum from their sidecar yaml, or from
`latitude:=`, `longitude:=` and `elevation:=` (see [Worlds](../user-guide/worlds.md)).

!!! note "Heading in the sim"
    Gazebo is east-north-up, and GLIM's odometry starts at the spawn heading. So the sim passes the
    spawn `yaw` to navsat_transform as its yaw offset. On the robot the offset is 1.57, for the Xsens
    convention.

## GLIM's map

GLIM saves its map only when asked: run `save_map` in the container. See
[GLIM maps](../user-guide/glim-maps.md).
