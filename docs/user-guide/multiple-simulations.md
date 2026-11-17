# Two simulations at once

Two simulations on the same machine must not see each other. They need different values for:

- `ROS_DOMAIN_ID`, which separates the ROS topics;
- `GZ_PARTITION`, which separates Gazebo's transport topics and clocks.

With `network_mode: host`, every container shares Gazebo's default partition, so two simulators
would otherwise mix their topics and clocks.

```bash
./jo sim                                              # the default: domain 0, partition jo_sim (.env)
./jo --domain 77 --partition other sim --headless     # a second one
./jo --domain 77 --partition other stop               # stops only the second one
```

One simulation with several robots is not supported, and not planned.
