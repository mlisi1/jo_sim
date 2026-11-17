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

!!! planned "Planned content (G3)"
    Before/after examples for each patch, and how to add one (with its `check_worlds` test).
