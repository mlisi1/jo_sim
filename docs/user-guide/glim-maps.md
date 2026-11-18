# GLIM maps

GLIM saves its map **only when asked**. In the container:

```bash
save_map                 # writes saved_maps/<date_time>/ on the host
offline_viewer           # open a saved map
```

On exit, GLIM also dumps the map to `/tmp/dump` in the container. The next run overwrites it, and
recreating the container loses it.

`./jo sim -n local --glim-view` (or `glim_view:=true`) opens GLIM's live viewer:

<figure class="jo-media">
<video src="../../assets/videos/glim_map.mp4" poster="../../assets/videos/glim_map.jpg" autoplay muted loop playsinline></video>
<figcaption>GLIM's viewer in small_city (4.5× speed), as Nav2 drives Jo 15 m west and then 25 m
north; Gazebo at the top right.</figcaption>
</figure>

Without the viewer, GLIM still publishes its map on `/glim_ros/map` (in the `map` frame), which
RViz can show. It goes out at most every `map_publish_period` seconds (default 10).

## The sim's GLIM config

The sim runs GLIM with `glim_config_bunker_sim`, which differs from the robot's
`glim_config_bunker` only where the simulation needs it. See
[Sim vs robot configs](../developer/sim-vs-robot.md).
