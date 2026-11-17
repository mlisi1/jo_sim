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
<video src="../../assets/videos/nav_local.mp4" poster="../../assets/videos/nav_local.jpg" autoplay muted loop playsinline></video>
<figcaption>Local navigation in office_cpr (1.6× speed): a goal 4.5 m ahead, then back to the start.
RViz shows the local and global costmaps, the planned path (amber) and the lidar; Gazebo at the top
right. The goals go to <code>/goal_pose</code>, as the 2D Goal Pose tool does.</figcaption>
</figure>

The lidar starts 2 s (sim time) after spawn. The robot is spawned slightly above the ground and
drops, and GLIM must initialize with the robot at rest.

## GPS navigation

```bash
./jo sim -w small_city -n gps
```

<figure class="jo-media">
<video src="../../assets/videos/nav_gps.mp4" poster="../../assets/videos/nav_gps.jpg" autoplay muted loop playsinline></video>
<figcaption>GPS navigation in small_city (2× speed): two GPS waypoints sent to Nav2's
<code>follow_gps_waypoints</code>, 15 m west to the crossroads, then 12 m north. Top right, the
<code>/gnss</code> fix the robot publishes.</figcaption>
</figure>

Worlds without `<spherical_coordinates>` get a GNSS datum from their sidecar yaml, or from
`latitude:=`, `longitude:=` and `elevation:=` (see [Worlds](../user-guide/worlds.md)).

!!! note "Heading in the sim"
    Gazebo is east-north-up, and GLIM's odometry starts at the spawn heading. So the sim passes the
    spawn `yaw` to navsat_transform as its yaw offset. On the robot the offset is 1.57, for the Xsens
    convention.

## GLIM's map

GLIM saves its map only when asked: run `save_map` in the container. See
[GLIM maps](../user-guide/glim-maps.md).
