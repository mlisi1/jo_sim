# World preprocessor

`jo_sim/jo_sim/world_tools.py` finds worlds, reads sidecars and writes the patched copy that
Gazebo loads. Entry point: `prepare_world(world_path, latitude, longitude, elevation, rtf)`. It
returns the path of the copy, and a list of changes that the launch prints.

| Function | Job |
|---|---|
| `search_dirs`, `list_worlds`, `resolve_world` | World search: `user_worlds/`, `jo_sim/worlds/`, the external collection. Earlier directories win on a name clash. |
| `sidecar_path`, `world_settings` | Sidecar lookup and priority: command line > sidecar > defaults. |
| `resource_dirs`, `local_models` | `GZ_SIM_RESOURCE_PATH` entries; the models found locally. |
| `_fix_includes` | Inline `sun` and `ground_plane`; fetch missing models from Fuel (names cached on disk). |
| `_fetch_classic_media` | `file://media/...` textures from the Classic install, downloaded. |
| `_convert_models`, `_convert_scripts`, `_ogre_materials` | Ogre material scripts → PBR maps, in converted copies of the models. |
| `_fix_heightmaps` | Heightmaps at the heights Classic gave them. |
| `_convert_roads` | Classic `<road>`s → flat asphalt strips. |
| `_classic_default_diffuse` | Classic's white default diffuse when a material has only `<ambient>`. |
| `_cap_step_size` | Physics step ≤ 5 ms (sensor rates), scaling `real_time_update_rate`. |
| `_set_rtf` | `<physics><real_time_factor>`. |
| `_unique_names` | Duplicate model names made unique. |

## Before and after

This small Gazebo Classic world (SDF 1.6) triggers most patches:

```xml
<sdf version="1.6">
  <world name="example">
    <physics type="ode">
      <max_step_size>0.01</max_step_size>
      <real_time_update_rate>100</real_time_update_rate>
    </physics>
    <spherical_coordinates>
      <latitude_deg>0</latitude_deg>
      <longitude_deg>0</longitude_deg>
    </spherical_coordinates>
    <scene><sky><clouds><speed>-12</speed></clouds></sky></scene>
    <include><uri>model://sun</uri></include>
    <road name="main_street">
      <width>6</width>
      <point>0 0 0</point>
      <point>20 0 0</point>
    </road>
    <model name="sidewalk">
      <static>true</static>
      <link name="link"><visual name="v"><geometry><box><size>10 2 0.1</size></box></geometry>
        <material><ambient>0.6 0.6 0.6 1</ambient></material></visual></link>
    </model>
    <model name="sidewalk"><static>true</static><link name="link"/></model>
  </world>
</sdf>
```

`prepare_world(..., rtf=2)` prints these changes (the launch shows them as `[jo_sim]` lines):

```text
added system gz::sim::systems::Physics
added system gz::sim::systems::UserCommands
added system gz::sim::systems::SceneBroadcaster
added system gz::sim::systems::Sensors
added system rgl::RGLServerPluginManager
replaced placeholder spherical_coordinates (0, 0)
added spherical_coordinates (43.72, 10.4)
cloud speed made positive (Classic allowed negative values)
inlined Classic built-in sun
1 Classic <road> elements drawn as asphalt strips
1 ambient-only materials given the Classic white diffuse
renamed duplicate model sidewalk -> sidewalk_2
physics step 10 ms -> 5 ms (sensors publish at most once per step: IMU at 200 Hz)
real-time factor 2
```

Each change, from the patched copy (reformatted):

| Patch | Before | After |
|---|---|---|
| Required systems | none | `Physics`, `UserCommands`, `SceneBroadcaster`, `Sensors` (`ogre2`), `RGLServerPluginManager` (the lidar) |
| Datum | `<latitude_deg>0</latitude_deg>` (Classic's placeholder) | `EARTH_WGS84`, `ENU`, the sidecar or default datum, `heading_deg` 0 |
| Clouds | `<speed>-12</speed>` | `<speed>12</speed>` |
| `_fix_includes` | `<include><uri>model://sun</uri></include>` | an inline `<light type="directional" name="sun">`. Models missing locally are fetched from Fuel, or removed with a `WARNING` line |
| `_convert_roads` | `<road>`, width 6, (0,0) → (20,0) | static model `main_street`: one 26 × 6 × 0.1 m box per segment, grey (lengthened by the width so corners overlap) |
| `_classic_default_diffuse` | `<ambient>0.6 0.6 0.6 1</ambient>` only | `<diffuse>1 1 1 1</diffuse>` added (Harmonic's default is black) |
| `_unique_names` | two models `sidewalk` | `sidewalk`, `sidewalk_2` |
| `_cap_step_size` | step 10 ms, update rate 100 | step 5 ms, update rate 200 (same target RTF) |
| `_set_rtf` (`rtf:=2`) | no `<real_time_factor>` | `<real_time_factor>2</real_time_factor>` |

The material and heightmap patches (`_convert_models`, `_convert_scripts`, `_fix_heightmaps`,
`_fetch_classic_media`) work on model files, not on the world text. They write converted copies of
the models, and the change list counts them (`model X: N Ogre material scripts converted to PBR`).

The road and diffuse patches run only on SDF ≤ 1.6, the Classic worlds.

## Adding a patch

1. **Write `_my_patch(world, changes)`** in `world_tools.py`. It edits the `world` element in place
   and appends one human-readable line to `changes` for each thing it changed. Change nothing when
   the world doesn't need it: a patch must leave a Harmonic-native world unchanged.
2. **Call it in `prepare_world`**, inside the `<= (1, 6)` block if it only applies to Classic worlds.
3. **Try it on one world:** `./jo sim -w NAME --headless --no-rviz` (in a sandbox), and look for
   your line in the `[jo_sim]` output.
4. **Check every world:** `./jo check --robot` (all worlds, its own partition and domain 78). The
   results table must not get worse: compare it with the one in [Worlds](../user-guide/worlds.md),
   and update that page if worlds were fixed.
5. **Document it:** add a row to the table at the top of this page and, if it shows, to the
   table above.
