# Worlds

## Loading a world

```bash
./jo sim -w small_city          # from the host
sim world:=small_city           # in the container
sim_worlds                      # list what loads by name, with the check_worlds results
```

Worlds are searched in this order:

1. `user_worlds/` (yours, mounted from the host);
2. `jo_sim/worlds/`;
3. the [external collection](https://github.com/leonhartyao/gazebo_models_worlds_collection).

A path works too.

<div class="media-ph" data-kind="image" markdown>
<span class="media-ph-kind">Image</span>
<p>World catalogue: a grid of thumbnails, one per world, each with its name, size, check_worlds
status, GNSS datum and spawn poses. Generated (G3/G4).</p>
</div>

## Adding your own world

Drop a `.sdf` or `.world` file in `user_worlds/`, with an optional `models/` folder next to it.
Then launch it by name:

```bash
./jo sim -w my_world
```

Gazebo Classic worlds work too: see [what the preprocessor patches](#what-is-patched).

## The sidecar yaml

A world can have a sidecar `<world>.yaml`, with its spawn poses, its GNSS datum and a description.
It is looked up in this order:

1. `user_worlds/`, so you can add one for any world, including the external collection;
2. `jo_sim/worlds/`;
3. next to the world file.

```yaml
description: Office with corridors
spawn: {x: 1.0, y: -2.0, z: 0.6, yaw: 1.57}
spawns:                       # named alternatives: ./jo sim -w my_world -s dock
  dock: {x: 5.0, y: 0.0, yaw: 3.14}
gnss: {latitude: 43.72, longitude: 10.33, elevation: 48.0}   # used if the world has no <spherical_coordinates>
```

The command line (`x y z yaw latitude longitude elevation`) overrides the sidecar.
In GPS mode, the navsat heading offset follows the resolved spawn yaw.

## What is patched

The original world file is never touched: a patched copy is written to `/tmp/jo_sim/worlds`.

- **Always:**
  - The world systems the robot needs (physics, sensors, the RGL lidar) and
    `<spherical_coordinates>` are added when missing.
  - A physics step above 5 ms is reduced to 5 ms. Sensors publish at most once per step, and with
    Classic's common 10 ms the 200 Hz IMU would run at 100 Hz.
  - `rtf:=` sets the target real-time factor.
- **Gazebo Classic worlds:**
  - `model://sun` and `model://ground_plane` are written inline.
  - Models that are not available locally are downloaded from
    [Gazebo Fuel](https://app.gazebosim.org/OpenRobotics) on first use, with their dependencies,
    into `user_worlds/.cache/models`.
  - Ogre material scripts are converted to PBR textures, in copies of the models
    (`user_worlds/.cache/converted_models`). Harmonic ignores Ogre scripts, so the models would
    otherwise be untextured.
  - Heightmap terrain is rescaled to the heights Classic gave it.
  - `<road>`s are drawn.
  - Duplicate model names are made unique.

!!! warning "The lidar does not see heightmap terrain"
    This is a limitation of the RGL plugin.

Details for developers: [World preprocessor](../developer/world-preprocessor.md).

## Checking worlds: `check_worlds`

Loading is not enough. Some Classic worlds run far below real time in Harmonic: for example
`warehouse` runs at RTF ≈ 0.003, because of stacked dynamic boxes on mesh shelves. Test worlds once:

```bash
check_worlds                     # all worlds, ~30 s each, headless; does not disturb a running sim
check_worlds warehouse cafe      # only some
check_worlds --robot office_cpr  # with the robot: sensor rates (sim time), lidar returns, upright
sim_worlds                       # the list, with the results: ok / slow / fails, and the robot check
```

The results are kept in `user_worlds/.cache/world_status.json`. `check_worlds --robot` takes about
70 s per world and needs the GPU.
