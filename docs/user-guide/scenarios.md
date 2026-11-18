# Scenarios

A scenario is a repeatable, headless test: a world, a spawn pose, a mission and pass criteria. The
runner starts everything, drives the mission through Nav2, checks the result against the
[ground truth](ground-truth.md), and exits 0 on pass and 1 on fail. So it works in scripts and CI.

```bash
./jo scenario --list
./jo scenario office_out_and_back
./jo scenario office_out_and_back --record compressed     # also record a bag
./jo --domain 77 --partition test scenario office_out_and_back   # next to a running sim
```

In the container: `scenario office_out_and_back`.

```text
[scenario] office_out_and_back: world office_cpr, spawn x 0.0 y 0.0 yaw 1.5708, nav local, record none
[scenario] waiting for the ground truth, localization and Nav2
[scenario] ready at sim time 6.2 s
[scenario] goal 1: world (0.00, 4.50, yaw 1.57) = map (4.50, -0.00, yaw 0.00)
[scenario] goal 1: succeeded in 8.0 s, error 0.241 m, yaw 0.006 rad
[scenario] goal 2: world (0.00, 1.00, yaw -1.57) = map (1.00, -0.00, yaw 3.14)
[scenario] goal 2: succeeded in 8.4 s, error 0.256 m, yaw 0.055 rad
[scenario] result: PASS  (report: /home/ros/bags/scenarios/20261117_135611_office_out_and_back/report.json)
[scenario]   ok   goals_reached: True (limit True)
[scenario]   ok   goal_1_error: 0.241 (limit 0.5)
[scenario]   ok   goal_2_error: 0.256 (limit 0.5)
[scenario]   ok   max_localization_error: 0.048 (limit 0.15)
[scenario]   ok   final_localization_error: 0.006 (limit 0.1)
[scenario]   ok   max_duration: 16.4 (limit 240)
```

## Output

Each run writes `bags/scenarios/<date>_<name>/` on the host:

| File | What |
|---|---|
| `report.json` | Goals (status, duration, final error), localization error (max and final), criteria, result |
| `launch.log` | The whole launch output |
| `bag/` | The bag (with `--record` or `record:`), in MCAP |

## Writing a scenario

Put it in `user_worlds/scenarios/<name>.yaml` (searched first), or in `jo_sim/scenarios/` to
ship it with the repository.

```yaml
description: office_cpr, 4.5 m out along +y and back (local navigation, GLIM + EKF + Nav2)
world: office_cpr
spawn: {x: 0.0, y: 0.0, yaw: 1.5708}     # or a named spawn from the sidecar: spawn: dock
nav: local                               # none | local | gps
record: none                             # none | all | compressed
settle: 3.0                              # [s, sim] wait after the stack is ready
launch_args: {}                          # any extra name: value for sim_bringup
obstacles: []                            # moving obstacles, see below
mission:                                 # goals in WORLD coordinates
  - {x: 0.0, y: 4.5, yaw: 1.5708, tolerance: 0.5, timeout: 90}
  - {x: 0.0, y: 1.0, yaw: -1.5708, tolerance: 0.5, timeout: 120}
criteria:
  goals_reached: true                    # every goal SUCCEEDED in Nav2
  max_localization_error: 0.15           # [m] TF map->base_link vs ground truth, whole run
  final_localization_error: 0.10         # [m] at the end
  max_duration: 240                      # [s, sim] the whole mission
  min_obstacle_distance: 0.5             # [m] only with obstacles
  goal_tolerance: 0.5                    # [m] for goals without their own tolerance
```

- **Goals are in world coordinates**, like the spawn pose. GLIM's `map` frame starts at the spawn
  pose, and the runner converts each goal.
- **`tolerance`** is checked against the ground truth: the robot's true final position, not what
  Nav2 believes.
- **`nav: local`** starts localization and navigation without the cameras, which is cheaper. Add
  `front_cam: true` (and so on) in `launch_args` to include them.
- **Recording profiles** (see also [Recording bags](bags.md)) are the robot's (jo-zotac `record_all` / `record_compressed`), plus the
  sim-only raw sensor topics excluded. The ground truth is kept.

## Moving obstacles

A scenario can add [moving obstacles](worlds.md#moving-obstacles), in the same format, with
`obstacles:`. The runner reads their true poses from Gazebo, and records how close `base_link` came
to each obstacle's surface. The check runs at 100 Hz.

```yaml
obstacles:
  - {name: walker, shape: person, waypoints: [[-2.5, 3.0], [2.5, 3.0]], speed: 0.6, pause: 1.0,
     yield_distance: 1.2}
criteria:
  min_obstacle_distance: 0.5     # [m] base_link to the obstacle surface (Nav2 robot_radius is 0.52)
```

`report.json` has the minimum per obstacle under `obstacles.min_distance`. A value of about 0.45 m
or less means contact, because the chassis is 0.91 m long. `office_crossing` is the example: a
person crossing the corridor at y = 3.

!!! warning "GPS scenarios"
    `nav: gps` sends goals in the `map` frame like `local`. It has not been validated yet.

<figure class="jo-media">
<video src="../../assets/videos/scenario.mp4" poster="../../assets/videos/scenario.jpg" autoplay muted loop playsinline></video>
<figcaption><code>./jo scenario office_crossing</code> (run at 3× speed): the walker crosses the corridor and
stops while Jo is close ahead of it; Jo reaches both goals. The terminal shows the runner's real
output, with the checks against the pass criteria.</figcaption>
</figure>
