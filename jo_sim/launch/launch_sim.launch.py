"""Jo simulator: world + robot + sensor bridges + driver emulation.

The simulator exposes the same ROS interface as the real robot (jo-zotac / jo_bringup): same
topics, frame ids and TF ownership. The stack (jo_navigation) is NOT launched here; use
sim_bringup.launch.py for the jo_bringup-equivalent entry point.

    ros2 launch jo_sim launch_sim.launch.py world:=warehouse sens_rviz:=true
    ros2 run jo_sim list_worlds
"""
import os
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument, ExecuteProcess,
                            IncludeLaunchDescription, LogInfo, OpaqueFunction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from jo_sim.world_tools import prepare_world, resolve_world, resource_dirs

PKG = 'jo_sim'

IMAGE_TRANSPORTS = ('', '/compressed', '/compressedDepth', '/theora', '/zstd')

# Sensor flag -> bridge config files (config/bridge/)
# The lidar cloud is bridged to /sim/velodyne_points_raw, driver_emulation publishes /velodyne_points
SENSOR_BRIDGES = {
    'lidar': ['lidar_raw.yaml'],
    'imu': ['imu.yaml'],
    'gnss': ['gnss.yaml'],
    'front_cam': ['front_cam.yaml', 'front_cam_depth_info.yaml'],
    'back_cam': ['back_cam.yaml', 'back_cam_depth_info.yaml'],
}


def bridge(name, config, condition=None):
    return Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name=name,
        output='screen',
        parameters=[{'config_file': config, 'use_sim_time': True}],
        condition=condition,
    )


def world_and_gazebo(context):
    world = resolve_world(LaunchConfiguration('world').perform(context))
    patched, changes = prepare_world(
        world,
        latitude=float(LaunchConfiguration('latitude').perform(context)),
        longitude=float(LaunchConfiguration('longitude').perform(context)),
        elevation=float(LaunchConfiguration('elevation').perform(context)),
    )
    gui = LaunchConfiguration('gui').perform(context).lower() in ('true', '1')
    gz_args = f"-r -v{LaunchConfiguration('gz_verbosity').perform(context)} "
    if not gui:
        gz_args += '-s --headless-rendering '

    actions = [LogInfo(msg=f'[jo_sim] world: {world}')]
    actions += [LogInfo(msg=f'[jo_sim]   {c}') for c in changes]
    actions += [AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', d) for d in resource_dirs(world)]
    actions.append(IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args + patched, 'on_exit_shutdown': 'true'}.items(),
    ))
    if gui and LaunchConfiguration('follow').perform(context).lower() in ('true', '1'):
        # Gazebo GUI camera follows the robot: once the GUI's CameraTracking service and the
        # spawned model exist, set the target (Gazebo's default offset: 3 m behind, 2 m above)
        follow = (
            'for i in $(seq 1 600); do '
            'gz service -l 2>/dev/null | grep -qx /gui/follow '
            '&& gz model --list 2>/dev/null | grep -q -- "- jo$" && break; sleep 1; done; '
            'gz service -s /gui/follow --reqtype gz.msgs.StringMsg --reptype gz.msgs.Boolean '
            '--timeout 3000 --req \'data: "jo"\' >/dev/null '
            '&& echo "[jo_sim] Gazebo GUI camera following jo (follow:=false to disable)"')
        actions.append(ExecuteProcess(cmd=['bash', '-c', follow], name='sim_gui_follow', output='screen'))

    # Clock from /world/<name>/clock, not the root /clock: the server creates the root topic only
    # after the world has loaded, and with big worlds (small_city, city_osm_roundabout) a bridge
    # subscribed before that never received it (no /clock in ROS -> nothing on sim time starts).
    name = ET.parse(patched).getroot().find('world').get('name', 'default')
    actions.append(Node(
        package='ros_gz_bridge', executable='parameter_bridge', name='sim_clock_bridge',
        output='screen',
        arguments=[f'/world/{name}/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        remappings=[(f'/world/{name}/clock', '/clock')],
    ))
    return actions


def generate_launch_description():
    share = get_package_share_directory(PKG)
    bridge_dir = os.path.join(share, 'config', 'bridge')

    args = [
        DeclareLaunchArgument('world', default_value='office_cpr',
                              description='World name (see `ros2 run jo_sim list_worlds`) or path'),
        DeclareLaunchArgument('gui', default_value='true', description='Open the Gazebo GUI'),
        DeclareLaunchArgument('follow', default_value='true',
                              description='Gazebo GUI camera follows the robot'),
        DeclareLaunchArgument('gz_verbosity', default_value='3'),
        DeclareLaunchArgument('sens_rviz', default_value='false',
                              description='RViz with the simulated sensors (as sens_rviz in jo_bringup)'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('z', default_value='0.6'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        # GNSS datum used when the world has no <spherical_coordinates> (default: Pisa, UTM 32N)
        DeclareLaunchArgument('latitude', default_value='43.7167'),
        DeclareLaunchArgument('longitude', default_value='10.3966'),
        DeclareLaunchArgument('elevation', default_value='0.0'),
    ]
    args += [DeclareLaunchArgument(s, default_value='true', description=f'Publish the {s} topics')
             for s in SENSOR_BRIDGES]
    args += [
        DeclareLaunchArgument('sim_noise', default_value='true',
                              description='Simulated sensor noise (IMU, GNSS, cameras, lidar)'),
        DeclareLaunchArgument('lidar_range_stddev', default_value='0.015',
                              description='[m] lidar range noise when sim_noise is true (VLP-16: +-3 cm)'),
    ]

    description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('jo_description'), 'launch', 'description.launch.py')),
        launch_arguments={'use_sim_time': 'true', 'use_ros2_control': 'false',
                          'sim_noise': LaunchConfiguration('sim_noise')}.items(),
    )

    spawn = Node(
        package='ros_gz_sim', executable='create', output='screen',
        arguments=['-topic', 'robot_description', '-name', 'jo',
                   '-x', LaunchConfiguration('x'), '-y', LaunchConfiguration('y'),
                   '-z', LaunchConfiguration('z'), '-Y', LaunchConfiguration('yaw')],
    )

    bridges = [bridge('sim_bridge', os.path.join(bridge_dir, 'core.yaml'))]
    for sensor, files in SENSOR_BRIDGES.items():
        for f in files:
            bridges.append(bridge(f'sim_bridge_{os.path.splitext(f)[0]}', os.path.join(bridge_dir, f),
                                  IfCondition(LaunchConfiguration(sensor))))

    for cam in ('front', 'back'):
        bridges.append(Node(
            package='ros_gz_image', executable='image_bridge', name=f'sim_bridge_{cam}_cam_image',
            arguments=[f'{cam}_camera/image'],
            # image_transport does not apply the base remap to its plugin topics: remap each one
            remappings=[(f'/{cam}_camera/image{t}', f'/{cam}_camera/camera/color/image_raw{t}')
                        for t in IMAGE_TRANSPORTS],
            parameters=[{'use_sim_time': True}],
            condition=IfCondition(LaunchConfiguration(f'{cam}_cam')),
        ))

    drivers = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'driver_emulation.launch.py')),
    )

    rviz = Node(
        package='rviz2', executable='rviz2', name='sim_rviz', output='screen',
        arguments=['-d', os.path.join(share, 'rviz', 'sim.rviz')],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('sens_rviz')),
    )

    return LaunchDescription([
        *args,
        description,
        OpaqueFunction(function=world_and_gazebo),
        spawn,
        *bridges,
        drivers,
        rviz,
    ])
