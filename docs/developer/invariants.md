# Invariants

These rules hold for every change. When in doubt, follow the
[guiding principle](../index.md#the-guiding-principle).

1. **Same ROS interface as the robot** (`jo-zotac@dev`): topic names, message types, frame ids,
   TF ownership, rates, middleware. Nothing more.
2. **`jo_description` must keep working on the robot.** Its joints and origins are the **real
   robot's TFs**: never change them for the simulator. Sim-only content goes in `<gazebo>` tags,
   which `robot_state_publisher` ignores.
3. **Sim-only topics live under `/sim/`**, and nothing in the stack may consume them. Examples:
   the raw sensor topics before driver emulation, and the ground truth.
4. **The stack runs unchanged.** Sim-specific stack settings are launch arguments with the robot's
   value as default (for example `glim_anchor_frame`, which is `imu` on the robot and `base` in the
   sim), or sim-only config files (`glim_config_bunker_sim`).
5. **The robot's GLIM config changes only after evaluation.** New keys go into the sim config
   first.
6. **No wheel odometry:** the robot has none, so TrackedVehicle's odometry stays out of ROS.
