"""Parts of the real drivers that are not the sensor itself, emulated for the simulator.

* RealSense (realsense2_camera, publish_tf: true): TF tree below <camera>_link, which on the robot
  comes from the driver and therefore is not in jo_description.
* Gazebo's RGB-D point cloud is restamped from the optical frame (shared with the images) to the
  non-optical depth frame, because Gazebo builds it in the X-forward convention.
* Velodyne (velodyne-all-nodes-VLP16-launch.py): velodyne_emulation gives the RGL cloud the driver's
  fields (ring, time) and range limits, plus range noise when sim_noise is true; then the real
  velodyne_laserscan_node publishes /scan (used by the Nav2 costmaps), with the driver's parameters.

Follows the lidar / front_cam / back_cam / sim_noise flags of the including launch (default: on).
"""
from launch import LaunchDescription
from launch.actions import OpaqueFunction
from launch_ros.actions import Node


def enabled(context, name):
    return context.launch_configurations.get(name, 'true').lower() in ('true', '1')


def velodyne(context):
    if not enabled(context, 'lidar'):
        return []
    stddev = float(context.launch_configurations.get('lidar_range_stddev', '0.015'))
    return [
        Node(
            package='jo_sim', executable='velodyne_emulation', name='velodyne_emulation',
            parameters=[{'range_stddev': stddev if enabled(context, 'sim_noise') else 0.0,
                         'min_range': 0.9, 'max_range': 130.0, 'use_sim_time': True}],
            remappings=[('input', '/sim/velodyne_points_raw'), ('output', '/velodyne_points')],
        ),
        # Same node and parameters as velodyne_laserscan in the Velodyne driver launch
        Node(
            package='velodyne_laserscan', executable='velodyne_laserscan_node',
            name='velodyne_laserscan_node',
            parameters=[{'ring': -1, 'resolution': 0.007, 'use_sim_time': True}],
        ),
    ]


def drivers(context):
    actions = velodyne(context)
    cameras = [f'{c}_camera' for c in ('front', 'back') if enabled(context, f'{c}_cam')]
    if not cameras:
        return actions
    actions.append(Node(
        package='jo_sim', executable='realsense_tf', name='sim_realsense_tf', output='screen',
        parameters=[{'cameras': cameras, 'use_sim_time': True}],
        # without it the camera frames (and so the camera clouds in RViz) are missing
        respawn=True, respawn_delay=2.0,
    ))
    for cam in cameras:
        actions.append(Node(
            package='jo_sim', executable='frame_restamp', name=f'sim_{cam}_points_restamp',
            parameters=[{'frame_id': f'{cam}_depth_frame', 'use_sim_time': True}],
            remappings=[('input', f'/sim/{cam}/points_raw'),
                        ('output', f'/{cam}/camera/depth/color/points')],
        ))
    return actions


def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=drivers)])
