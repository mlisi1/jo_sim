# For agents

This page is for AI agents (and humans new to the project) about to **change** the simulator.
Machine-readable versions of the whole site are at [`llms.txt`](https://mlisi1.github.io/jo_sim/llms.txt) and
[`llms-full.txt`](https://mlisi1.github.io/jo_sim/llms-full.txt). The repository's `AGENTS.md` has the same rules in short.

## Before you change anything

1. Read the [Invariants](developer/invariants.md). Above all: **never change joints or origins in
   `jo_description`**. They are the real robot's TFs. Sim-only content goes in `<gazebo>` tags.
2. Read [`PLAN.md`](https://github.com/mlisi1/jo_sim/blob/dev/PLAN.md), section "Where we left
   off". It holds the current state, the decisions and the next steps.
3. Keep the scope: **simulator work only**. Record findings about navigation or localization tuning
   (`localization*.yaml`, Nav2, the EKF) as deferred; don't tune them.
4. **Don't change the robot's GLIM config** (`glim_config_bunker`) on your own. New keys go into
   `glim_config_bunker_sim` first, and the maintainer evaluates them.

## Testing without disturbing anyone

- **Never use the maintainer's domain or partition** (domain 0, partition `jo_sim`). Use
  `./jo --domain 77 --partition jo_sim_test ...`.
- **Stop what you start, by process group.** Check that nothing of yours is left running in the
  container.
- **The machine may be shared:** check `uptime`, `free -h` and `nvidia-smi` before a test batch,
  and run one batch at a time. If you're told the GPU is needed by someone else, don't start
  Gazebo, GLIM or the lidar.
- `docker exec` without `-e` runs with the container's defaults (domain 0). Don't confuse your own
  processes with the maintainer's.

## Verifying a change

| Change | Verify with |
|---|---|
| a world patch | `check_worlds <world>` (and `--robot`) |
| a sensor, bridge or emulation | `ros2 topic hz` / `echo` in the sandbox; Testudo `health_headless`, read `/testudo/overall` |
| localization behaviour | `/sim/ground_truth/odom` against GLIM and the EKF |
| docs | `python3 docs/gen/gen_tables.py` (if arguments, bridges or `./jo` changed); `python3 docs/gen/gen_topics.py` (if topics, frames, rates or node parameters changed; needs the GPU); then `mkdocs build --strict` |

## Where things live

| What | Where |
|---|---|
| state, decisions, next steps | `PLAN.md` |
| user and developer docs | this site (`docs/`) |
| aliases and runtime environment | `docker/utils/utilities.sh` (mounted) |
| build pins | `docker/Dockerfile` (`ARG`s), `.env` |

## Commits and pushes

Work on `dev`. Use few commits, grouped by topic. Commit and push the **submodules first**, then
jo_sim with the pointer bump. Update the docs in the same commit as the feature.
