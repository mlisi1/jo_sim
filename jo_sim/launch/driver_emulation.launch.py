"""Parts of the real drivers that are not the sensor itself, emulated for the simulator.

* RealSense (realsense2_camera, publish_tf: true): TF tree below <camera>_link, which on the robot
  comes from the driver and therefore is not in jo_description.
* Gazebo's RGB-D point cloud is restamped from the optical frame (shared with the images) to the
  non-optical depth frame, because Gazebo builds it in the X-forward convention.

Follows the front_cam / back_cam flags of the including launch (default: both on).
"""
from launch import LaunchDescription
from launch.actions import OpaqueFunction
from launch_ros.actions import Node


def enabled(context, name):
    return context.launch_configurations.get(name, 'true').lower() in ('true', '1')


def drivers(context):
    cameras = [f'{c}_camera' for c in ('front', 'back') if enabled(context, f'{c}_cam')]
    if not cameras:
        return []
    actions = [Node(
        package='jo_sim', executable='realsense_tf', name='sim_realsense_tf', output='screen',
        parameters=[{'cameras': cameras, 'use_sim_time': True}],
    )]
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
