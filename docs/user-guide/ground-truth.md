# Ground truth

`/sim/ground_truth/odom` gives the true pose of the robot:

| | |
|---|---|
| Type | `nav_msgs/Odometry` |
| Rate | 100 Hz |
| Frames | `world` → `base_link`. No TF is published. |
| Pose | `base_link` in the Gazebo world frame. It is not relative to the spawn. |
| Twist | in `base_link` |

!!! danger "Simulation only"
    It is not part of the robot's interface: nothing in the stack may consume it. Use it to
    **evaluate** GLIM, the EKF or RTAB-Map: drift, end-of-mission error, and comparisons between
    configs or glim_ros2 versions.

## Comparing with GLIM or the EKF

GLIM's `map` and `odom` frames start at the spawn pose. Compare against the ground truth taken
relative to its first message:

```python
# T_world_base(t): from /sim/ground_truth/odom
# error(t) = inverse(T_world_base(0)) * T_world_base(t)   vs   T_map_base(t) from GLIM / the EKF
```

<div class="media-ph short" data-kind="image" markdown>
<span class="media-ph-kind">Image</span>
<p>Plot: the ground truth vs GLIM vs the EKF trajectory, and the position error over time.</p>
</div>

!!! planned "Planned content (Phase E)"
    A ready-made evaluation script and scenario pass criteria based on the ground-truth error.
