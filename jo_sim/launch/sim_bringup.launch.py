"""Simulator counterpart of jo_bringup.launch.py (jo-zotac).

Accepts the same flags as jo_bringup, with Gazebo in place of the drivers, so the jo-zotac
aliases work unchanged (see docker/utils/utilities.sh):

    ros2 launch jo_sim sim_bringup.launch.py front_cam:=true localization:=true navigation:=true rviz:=true

Simulator-only arguments (world, gui, x, y, z, yaw, latitude, longitude, sim_noise, ...) are forwarded to
launch_sim.launch.py. `bunker` is accepted for compatibility: the simulated base always runs.
"""
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def flag(name, default, description):
    return DeclareLaunchArgument(name, default_value=default, description=description)


def generate_launch_description():
    sim_share = get_package_share_directory('jo_sim')
    nav_share = get_package_share_directory('jo_navigation')

    # Same names and defaults as jo_bringup.launch.py
    args = [
        flag('imu', 'true', 'Whether to launch the IMU stack'),
        flag('gnss', 'false', 'Whether to launch the GNSS stack'),
        flag('sens_rviz', 'false', 'Launch RViz2 with the sensors'),
        flag('lidar', 'true', 'Whether to launch the Velodyne stack'),
        flag('front_cam', 'false', 'Whether to launch the RealSense front camera stack'),
        flag('back_cam', 'false', 'Whether to launch the RealSense back camera stack'),
        flag('bunker', 'false', 'Accepted for compatibility with jo_bringup (the simulated base always runs)'),
        flag('use_sim_time', 'true', 'Always true in simulation'),
        flag('localization', 'false', 'Whether to launch the localization stack'),
        flag('glim_view', 'false', 'Whether to open the GLIM viewer window'),
        flag('localization_gps', 'false', 'Whether to launch the GPS-based localization stack'),
        flag('navigation', 'false', 'Whether to launch the navigation stack'),
        flag('navigation_gps', 'false', 'Whether to launch the GPS-based navigation stack'),
        # Simulator specific
        flag('glim_config', os.path.join(nav_share, 'config', 'glim', 'glim_config_bunker_sim'),
             'GLIM config used in simulation'),
    ]

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(sim_share, 'launch', 'launch_sim.launch.py')),
        launch_arguments={s: LaunchConfiguration(s)
                          for s in ('imu', 'gnss', 'lidar', 'front_cam', 'back_cam', 'sens_rviz')}.items(),
    )

    stack_args = {
        'use_sim_time': 'true',
        'glim_config': LaunchConfiguration('glim_config'),
    }

    def stack(launch_file, flag_name, extra=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav_share, 'launch', launch_file)),
            launch_arguments={**stack_args, **(extra or {})}.items(),
            condition=IfCondition(LaunchConfiguration(flag_name)),
        )

    return LaunchDescription([
        *args,
        sim,
        stack('localization.launch.py', 'localization'),
        # Gazebo's world is ENU and GLIM's odometry starts at the spawn heading, so the
        # navsat_transform heading offset is the spawn yaw (the robot's 1.57 is for the Xsens)
        stack('localization_gps.launch.py', 'localization_gps',
              {'navsat_yaw_offset': LaunchConfiguration('yaw', default='0.0')}),
        stack('navigation_local.launch.py', 'navigation'),
        stack('navigation_gps.launch.py', 'navigation_gps'),
    ])
