# GLIM maps

GLIM saves its map **only when asked**. In the container:

```bash
save_map                 # writes saved_maps/<date_time>/ on the host
offline_viewer           # open a saved map
```

On exit, GLIM also dumps the map to `/tmp/dump` in the container. The next run overwrites it, and
recreating the container loses it.

`./jo sim -n local --glim-view` (or `glim_view:=true`) opens GLIM's live viewer.

<div class="media-ph" data-kind="video" markdown>
<span class="media-ph-kind">Video</span>
<p>Building a map: drive around office_cpr with the GLIM viewer open, <code>save_map</code>, then
open the map in <code>offline_viewer</code>.</p>
</div>

## The sim's GLIM config

The sim runs GLIM with `glim_config_bunker_sim`, which differs from the robot's
`glim_config_bunker` only where the simulation needs it. See
[Sim vs robot configs](../developer/sim-vs-robot.md).
