# AGENTS.md

Rules for AI agents (and new contributors) working on jo_sim. The full version, with context:
https://mlisi1.github.io/jo_sim/agents/ (source: `docs/agents.md`).

## Start here
- Read `PLAN.md`, section "Where we left off": the current state, the decisions and the next steps.
- The guiding principle: the simulator exposes **the same ROS interface as the real robot**
  (jo-zotac): topics, types, frame ids, TF ownership, rates. Nothing more.

## Never
- Change joints or origins in `jo_description`: they are the **real robot's TFs**. Sim-only content
  goes in `<gazebo>` tags.
- Let the stack consume `/sim/*` topics (the ground truth, raw sensor topics).
- Change the robot's GLIM config (`glim_config_bunker`) without the maintainer. New keys go into
  `glim_config_bunker_sim` first.
- Tune navigation or localization (`localization*.yaml`, Nav2, the EKF): out of scope. Record
  findings as deferred in `PLAN.md`.
- Test on the maintainer's ROS domain 0 or Gazebo partition `jo_sim`.
- Push without the maintainer's approval.

## Testing
- Sandbox: `./jo --domain 77 --partition jo_sim_test sim --headless --no-rviz`, then
  `./jo --domain 77 --partition jo_sim_test stop`.
- Kill launches by process group. Leave nothing of yours running in the container.
- The machine is shared: check `uptime`, `free -h` and `nvidia-smi` first. If the GPU is reserved,
  don't start Gazebo or GLIM.

## Commits
- Branch `dev` everywhere. Few commits, grouped by topic.
- Submodules first (jo_description, jo_navigation), then jo_sim with the pointer bump. Push in the
  same order.
- Update `docs/` in the same commit as the feature; `mkdocs build --strict` must pass.
