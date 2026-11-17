# Roadmap

The working roadmap, with session notes, is
[`PLAN.md`](https://github.com/mlisi1/jo_sim/blob/dev/PLAN.md) in the repository.

| Phase | Status |
|---|---|
| A: sync with the robot's stack | :material-check-circle: done |
| B: drop-in worlds (preprocessor, sidecar yaml, `check_worlds --robot`) | :material-check-circle: done |
| C: launch ergonomics (`paused`, `rtf`, `sim_control`, `./jo`) | :material-check-circle: done |
| D1: sensor fidelity (noise, Velodyne fields, RealSense depth encoding) | :material-check-circle: done |
| D2: ground truth | :material-check-circle: done |
| D3: dynamic obstacles | :material-circle-outline: planned |
| Track model re-tuning (steering calibrated against the ground truth) | :material-check-circle: done |
| E: testing workflow (scenarios, bags, CI) | :material-progress-wrench: scenarios and bags done; CI to do |
| F: Docker (base image, compose profiles) | :material-circle-outline: planned |
| G: this documentation site | :material-progress-wrench: in progress |
