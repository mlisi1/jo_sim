# How-to recipes

!!! planned "Planned content (G3)"
    Step-by-step recipes, each with the files to touch and how to verify the result:

    - **Add a sensor:** the `<gazebo>` tag in jo_description (never joints or origins), a bridge
      config, the launch flag, driver emulation if the real driver does more than read the sensor,
      the Testudo topics, the docs.
    - **Add a patch to the world preprocessor**, and test it with `check_worlds`.
    - **Add a launch argument** end to end (`sim_bringup` → `launch_sim` → `./jo`).
    - **Change a noise model** (`sim_noise.xacro`).
    - **Follow a new glim_ros2 commit** (`GLIM_ROS_COMMIT`).
    - **Add a world to the repo**, with its sidecar.
