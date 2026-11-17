"""Jo simulator: world + robot + sensor bridges + driver emulation.

The simulator exposes the same ROS interface as the real robot (jo-zotac / jo_bringup): same
topics, frame ids and TF ownership. The stack (jo_navigation) is NOT launched here; use
sim_bringup.launch.py for the jo_bringup-equivalent entry point.

    ros2 launch jo_sim launch_sim.launch.py world:=warehouse sens_rviz:=true
    ros2 launch jo_sim launch_sim.launch.py gui:=false paused:=true rtf:=2
    ros2 run jo_sim list_worlds
"""
import os
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_prefix, get_package_share_directory

from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument, ExecuteProcess,
                            IncludeLaunchDescription, LogInfo, OpaqueFunction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from jo_sim.world_tools import load_obstacles, prepare_world, resolve_world, resource_dirs, world_settings

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


def truthy(value):
    return value.strip().lower() in ('true', '1', 'yes', 'on')


def settings_from(context):
    """World path and its settings (command line > sidecar <world>.yaml > defaults)."""
    world = resolve_world(LaunchConfiguration('world').perform(context))
    overrides = {k: LaunchConfiguration(k).perform(context)
                 for k in ('x', 'y', 'z', 'yaw', 'latitude', 'longitude', 'elevation')}
    return world, world_settings(world, overrides, LaunchConfiguration('spawn').perform(context))


def world_and_gazebo(context):
    world, st = settings_from(context)
    rtf = LaunchConfiguration('rtf').perform(context).strip()
    if rtf:
        try:
            rtf = float(rtf)
        except ValueError:
            raise RuntimeError(f'[jo_sim] rtf:={rtf}: not a number') from None
        if rtf < 0:
            raise RuntimeError(f'[jo_sim] rtf:={rtf:g}: must be >= 0 (0 = as fast as possible)')
    obstacles_file = LaunchConfiguration('obstacles').perform(context).strip()
    obstacles = load_obstacles(obstacles_file) if obstacles_file else None
    patched, changes = prepare_world(world, st['latitude'], st['longitude'], st['elevation'],
                                     rtf=rtf if rtf != '' else None, obstacles=obstacles)
    gui = truthy(LaunchConfiguration('gui').perform(context))
    paused = truthy(LaunchConfiguration('paused').perform(context))
    gz_args = ('' if paused else '-r ') + f"-v{LaunchConfiguration('gz_verbosity').perform(context)} "
    if not gui:
        gz_args += '-s --headless-rendering '

    actions = [LogInfo(msg=f'[jo_sim] world: {world}')]
    if st['sidecar']:
        actions.append(LogInfo(msg=f"[jo_sim] sidecar: {st['sidecar']}" +
                                   (f" ({st['description']})" if st['description'] else '')))
    actions.append(LogInfo(msg=f"[jo_sim] spawn x {st['x']} y {st['y']} z {st['z']} yaw {st['yaw']}"))
    actions += [LogInfo(msg=f'[jo_sim]   {c}') for c in changes]
    actions += [AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', d) for d in resource_dirs(world)]
    # jo_sim's own Gazebo systems (WaypointMover, for moving obstacles)
    actions.append(AppendEnvironmentVariable('GZ_SIM_SYSTEM_PLUGIN_PATH', os.path.join(get_package_prefix(PKG), 'lib')))
    actions.append(IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args + patched, 'on_exit_shutdown': 'true'}.items(),
    ))
    if paused:
        actions.append(LogInfo(msg='[jo_sim] paused: press play in the Gazebo GUI, or run '
                                   '`ros2 run jo_sim sim_control play`'))
    if gui and truthy(LaunchConfiguration('follow').perform(context)):
        # Gazebo GUI camera follows the robot (scripts/gui_follow)
        actions.append(ExecuteProcess(
            cmd=[os.path.join(get_package_prefix(PKG), 'lib', PKG, 'gui_follow'), 'jo'],
            name='sim_gui_follow', output='screen'))

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
    actions.append(Node(
        package='ros_gz_sim', executable='create', output='screen',
        arguments=['-topic', 'robot_description', '-name', 'jo',
                   '-x', str(st['x']), '-y', str(st['y']), '-z', str(st['z']), '-Y', str(st['yaw'])],
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
        DeclareLaunchArgument('paused', default_value='false',
                              description='Start with the simulation paused (play in the GUI or '
                                          '`ros2 run jo_sim sim_control play`)'),
        DeclareLaunchArgument('rtf', default_value='',
                              description="Target real-time factor; empty = the world's own (usually 1), "
                                          '0 = as fast as possible'),
        DeclareLaunchArgument('gz_verbosity', default_value='3', description='Gazebo log level (0-4)'),
        DeclareLaunchArgument('sens_rviz', default_value='false',
                              description='RViz with the simulated sensors (as sens_rviz in jo_bringup)'),
        # Spawn pose and GNSS datum: empty = from the world's sidecar <world>.yaml, else the defaults
        # (0, 0, 0.6, yaw 0; datum Pisa, UTM 32N, used when the world has no <spherical_coordinates>)
        DeclareLaunchArgument('x', default_value='', description='[m] spawn x; empty = sidecar, else 0'),
        DeclareLaunchArgument('y', default_value='', description='[m] spawn y; empty = sidecar, else 0'),
        DeclareLaunchArgument('z', default_value='', description='[m] spawn z; empty = sidecar, else 0.6'),
        DeclareLaunchArgument('yaw', default_value='', description='[rad] spawn yaw; empty = sidecar, else 0'),
        DeclareLaunchArgument('spawn', default_value='',
                              description="Named spawn pose from the world's sidecar (spawns:)"),
        DeclareLaunchArgument('latitude', default_value='',
                              description='[deg] GNSS datum for worlds without <spherical_coordinates>; '
                                          'empty = sidecar, else Pisa'),
        DeclareLaunchArgument('longitude', default_value='', description='[deg] GNSS datum, see latitude'),
        DeclareLaunchArgument('elevation', default_value='', description='[m] GNSS datum, see latitude'),
        DeclareLaunchArgument('obstacles', default_value='',
                              description='YAML file of moving obstacles added to the world (see Worlds)'),
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
        *bridges,
        drivers,
        rviz,
    ])
