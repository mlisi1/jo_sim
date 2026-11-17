# Developer guide

For anyone who changes or extends the simulator. Read [Invariants](invariants.md) first: they are
the rules every change must respect.

<div class="grid cards" markdown>

- :material-sitemap: __[Architecture](architecture.md)__: how Gazebo, the bridges, driver emulation and the stack fit together
- :material-shield-check: __[Invariants](invariants.md)__: what must never change, and why
- :material-source-repository-multiple: __[Repositories](repositories.md)__: submodules, branches, push order
- :material-rocket-launch-outline: __[Launch files](launch-files.md)__: `sim_bringup`, `launch_sim`, `driver_emulation`
- :material-earth-box: __[World preprocessor](world-preprocessor.md)__: `world_tools.py`, patch by patch
- :material-bridge: __[Bridges](bridges.md)__: the ros_gz_bridge configs
- :material-chip: __[Driver emulation nodes](nodes.md)__: `velodyne_emulation`, `frame_restamp`, `realsense_tf`, ...
- :material-docker: __[Docker image](docker.md)__: layers, pins, build args, entrypoint
- :material-chef-hat: __[How-to recipes](how-to.md)__: add a sensor, a world patch, an argument
- :material-test-tube: __[Testing](testing.md)__: the sandbox, `check_worlds`, process groups
- :material-compare: __[Sim vs robot configs](sim-vs-robot.md)__: every difference, with the reason
- :material-lightbulb-on: __[Design decisions](decisions.md)__: why things are the way they are
- :material-account-group: __[Contributing](contributing.md)__: commits, docs, reviews
- :material-road-variant: __[Roadmap](roadmap.md)__: what's done, what's next

</div>
