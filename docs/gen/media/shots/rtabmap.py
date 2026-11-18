"""office_cpr, local navigation with RTAB-Map (vslam:=true), in the image built with
BUILD_RTABMAP=true: Nav2 drives Jo along the corridor and back to the start, every other frame (2x
time-lapse). RViz shows RTAB-Map's occupancy grid (/visodom/map) and its graph (/visodom/mapPath) in
its own vslam_map frame, top-down. Each frame also records the ground truth, the visual odometry
and RTAB-Map's status, for the numbers on the page.
    JO_MEDIA_CONTAINER=<container of that image> python3 docs/gen/media/shoot.py rtabmap
RTAB-Map's own visualizer (rtabmap_viz) runs on a second virtual display (:98, started by the
caller), with a docs-only configuration: the robot's launch file keeps it disabled.
Used by: Visual odometry page."""
from nav_msgs.msg import Odometry, OccupancyGrid, Path  # noqa: E402  (the rig is prepended to this script)
from rtabmap_msgs.msg import Info  # noqa: E402
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy  # noqa: E402

GOALS = [(4.5, 0.0, 0.0), (0.6, 0.0, math.pi)]   # map frame; spawn yaw pi/2: world (-my, mx)
STRIDE = 2
VIZ_DISPLAY, VIZ_SIZE = ':98', (1600, 1000)
VIZ_PARAMS = {'frame_id': 'base_link', 'subscribe_depth': True, 'subscribe_rgb': False,
              'subscribe_odom_info': True, 'subscribe_scan_cloud': False, 'approx_sync': True,
              'approx_sync_max_interval': 0.05, 'topic_queue_size': 30, 'sync_queue_size': 30,
              'image_transport': 'compressed', 'depth_transport': 'compressedDepth', 'use_sim_time': True}


def start_viz(rig):
    """rtabmap_viz in the /visodom namespace, on its own display, filling it."""
    cam = '/front_camera/camera'
    args = [a for k, v in VIZ_PARAMS.items() for a in ('-p', f'{k}:={str(v).lower() if isinstance(v, bool) else v}')]
    remaps = {'rgb/image': f'{cam}/color/image_raw', 'rgb/camera_info': f'{cam}/color/camera_info',
              'depth/image': f'{cam}/aligned_depth_to_color/image_raw', 'odom': '/visodom/odom',
              'odom_info': '/visodom/odom_info'}
    args += [a for k, v in remaps.items() for a in ('-r', f'{k}:={v}')]
    env = dict(os.environ, DISPLAY=VIZ_DISPLAY, QT_QPA_PLATFORM='xcb', LIBGL_ALWAYS_SOFTWARE='1')
    rig._spawn(['ros2', 'run', 'rtabmap_viz', 'rtabmap_viz', '-qwindowgeometry',
                f'{VIZ_SIZE[0]}x{VIZ_SIZE[1]}+0+0', '--ros-args', '-r', '__ns:=/visodom', *args], 'viz.log', env=env)


def grab_viz(rig):
    """The visualizer at the frame the rig has just recorded."""
    os.makedirs(os.path.join(rig.out, 'viz'), exist_ok=True)
    ImageGrab.grab(xdisplay=VIZ_DISPLAY).save(os.path.join(rig.out, 'viz', f'{rig.n - 1:05d}.png'), compress_level=1)


def pose(m):
    p, q = m.pose.pose.position, m.pose.pose.orientation
    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
    return [round(p.x, 4), round(p.y, 4), round(yaw, 4), round(m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, 3),
            m.pose.covariance[0]]


def shot():
    volatile = {'Depth': 5, 'Durability Policy': 'Volatile', 'History Policy': 'Keep Last',
                'Reliability Policy': 'Reliable'}
    off = {'Enabled': False, 'Value': False}
    rv = rviz_config('rtabmap', 'nav', fixed_frame='vslam_map',
                     view={'Class': 'rviz_default_plugins/TopDownOrtho', 'Target Frame': '<Fixed Frame>',
                           'Scale': 105.0, 'X': 2.2, 'Y': -0.5, 'Angle': 0.0, 'Value': 'TopDownOrtho (rviz_default_plugins)'},
                     set_displays={
                         'Global Costmap': {'Name': 'RTAB-Map grid', 'Enabled': True, 'Value': True, 'Color Scheme': 'map', 'Alpha': 1.0,
                                            'Topic': {**volatile, 'Value': '/visodom/map'},
                                            'Update Topic': {**volatile, 'Value': '/visodom/map_updates'}},
                         'Planned Path': {'Name': 'RTAB-Map graph', 'Line Style': 'Billboards', 'Line Width': 0.12,
                                          'Color': '245; 158; 11', 'Topic': {**volatile, 'Value': '/visodom/mapPath'}},
                         'Grid': off, 'Local Costmap': off, 'Lidar': off, 'Jo': off, 'Axes': off, 'Footprint': off,
                         'Back Camera Points': off, 'Front Camera Points': off})
    # the grid hides the background colour the rig looks for: the 3D view's rectangle, as measured
    rig = Rig('rtabmap', world='office_cpr', rviz=rv, xvfb_crop=(384, 62, 2906, 1771),
              launch=['yaw:=1.5708', 'localization:=true', 'navigation:=true', 'vslam:=true'])
    try:
        rig.start(settle=15, ready_log='Managed nodes are active')
        rig.control(pause=False)        # the visualizer starts on a running world
        start_viz(rig)
        time.sleep(25)
        rig.sync()
        cam = rig.camera('main', 1920, 1080)
        rig.ros_camera('front', '/front_camera/camera/color/image_raw')
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE)
        rig.ros_value('gt', '/sim/ground_truth/odom', Odometry, pose)
        rig.ros_value('vo', '/visodom/odom', Odometry, pose)
        rig.ros_value('info', '/visodom/info', Info, lambda m: [m.ref_id, m.loop_closure_id, m.proximity_detection_id])
        rig.ros_value('grid', '/visodom/map', OccupancyGrid,
                      lambda m: [m.info.width, m.info.height, round(m.info.resolution, 3),
                                 round(m.info.origin.position.x, 2), round(m.info.origin.position.y, 2),
                                 sum(1 for v in m.data if v >= 0)], qos)
        rig.ros_value('path', '/visodom/mapPath', Path, lambda m: len(m.poses), qos)
        rig.frame(record=False)
        x, y, z, yaw = rig.robot
        eye, tgt = [x + 3.0, y - 4.5, z + 3.2], [x, y, z]
        g, sent, t_sent, end = 0, False, 0, None
        for i in range(800):
            rx, ry, rz, ryaw = rig.robot
            if g < len(GOALS):
                mx, my, myaw = GOALS[g]
                if not sent:
                    rig.goal(mx, my, myaw)
                    sent, t_sent = True, i
                    rig.extra = {'goal': g}
                if math.hypot(rx + my, ry - mx) < 0.6 and i - t_sent > 30:
                    log(f'goal {g} reached at frame {rig.n}')
                    g, sent = g + 1, False
                    if g == len(GOALS):
                        end = i
            elif i - end > 45:
                break
            back = ryaw + math.pi + 0.5
            want = (rx + 3.6 * math.cos(back), ry + 3.6 * math.sin(back), rz + 2.6)
            eye = [e + (w - e) * 0.08 for e, w in zip(eye, want)]
            tgt = [p + (q - p) * 0.2 for p, q in zip(tgt, (rx, ry, rz + 0.2))]
            cam.look(eye, tgt)
            rig.frame(stride=STRIDE, xvfb_wait=0.6)
            grab_viz(rig)
        log('end at frame', rig.n, 'goals done', g)
    finally:
        rig.stop()


main(shot)
