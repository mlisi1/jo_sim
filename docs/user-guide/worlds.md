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

## Catalogue

--8<-- "docs/includes/generated/world_catalogue.md"

The full results, slow and broken worlds included, are in [Checking worlds](#checking-worlds-check_worlds).

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

## Moving obstacles

`obstacles:=<file.yaml>` adds moving obstacles to any world. Scenarios can declare them too (see
[Scenarios](scenarios.md#moving-obstacles)).

```bash
./jo sim -n local obstacles:=/home/ros/user_worlds/people.yaml
```

```yaml
obstacles:
  - name: walker                 # optional (obstacle_<n>)
    shape: person                # person (cylinder 0.25 x 1.7 m) | cylinder | box
    waypoints: [[-2.5, 3.0], [2.5, 3.0]]   # world x y, at least 2
    speed: 0.6                   # [m/s]
    mode: pingpong               # pingpong | loop | once
    pause: 1.0                   # [s] at each waypoint
    delay: 0.0                   # [s, sim] before starting
    yield_distance: 1.2          # optional: stop while the robot is this close ahead
    color: [0.9, 0.4, 0.1]
  - {shape: box, size: [0.6, 0.4, 1.0], waypoints: [[5, -3], [5, 3]], speed: 0.4, delay: 10}
```

- **Every sensor sees them:** the lidar, the cameras and physics. They are ordinary models.
- **They are kinematic:** a contact does not move them. Without `yield_distance`, they walk into the
  robot and push it.
- **Motion runs on sim time,** so runs are repeatable, except when an obstacle yields.
- **Gazebo `<actor>`s are not used** because the lidar does not see them: the RGL plugin skips
  skinned meshes.

You can also attach the system to a model in your own world file:

```xml
<plugin filename="jo_sim_waypoint_mover" name="jo_sim::WaypointMover">
  <speed>0.6</speed><mode>pingpong</mode><pause>1.0</pause>
  <waypoint>-2.5 3.0</waypoint><waypoint>2.5 3.0</waypoint>
  <yield_to>jo</yield_to><yield_distance>1.2</yield_distance>
</plugin>
```

Give the model's links `<gravity>false</gravity>`, and don't make it static.

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

### Results (2026-11-17, all 51 bundled worlds, with the robot)

RTF varies by ±0.2 between runs on heavy worlds. Measured on an RTX-class desktop with nothing else
running.

| Status | Worlds |
|---|---|
| **Good** (robot interface OK, RTF ≥ 0.8) | agriculture, azcar, city_osm_roundabout, city_osm_roundabout_combined, cyberzoo, cyberzoo2019_ralphthesis2020, empty_aerial_manipulation, fetchit_challenge_arena_montreal2019_onlylights, house, inspection, neighborhood, obstacles, office_cpr, office_cpr_construction, outdoor, rubble, skidpan, wall_aerial_manipulation, waypoint |
| **Usable, slower** (OK, RTF 0.5–0.8) | cyberzoo_panel, fetchit_challenge_arena_montreal2019_highlights, fetchit_challenge_simple_highlights, small_city |
| **Too slow for the stack** (OK, RTF < 0.5) | barrels, canyonview_field, cyberzoo_4_panels, fetchit_challenge_arena_montreal2019, fetchit_challenge_assembly, fetchit_challenge_atrezzo, fetchit_challenge_simple, fetchit_challenge_tests, fetchit_challenge_tests_lowlights |
| **Unusable: RTF ≈ 0.003** (no sensor data in the test window) | warehouse, drone_race_track_2018_actual, drone_race_track_2018_actual_with_gatepapers |
| **No lidar** (heightmap terrain, not seen by RGL) | hemicyl |
| **Don't load** (missing models or media, or Gazebo crashes) | cyberzoo2019_orange_poles, cyberzoo2019_orange_poles_panels, cyberzoo2019_orange_poles_panels_mats, cyberzoo_orange_poles, office_earthquake, office_env_large, office_small, powerplant, simple_env_1, simple_env_2, simple_env_3, test_city, test_zone, workshop_example, yosemite |

With no lidar returns, `/scan` stays silent: `velodyne_laserscan` rejects empty clouds. It would
do the same on the robot.
