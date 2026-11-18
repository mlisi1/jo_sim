"""small_city, local navigation (GLIM + EKF + Nav2): Nav2 goals 15 m west to the crossroads, then
25 m north along the street (in ~8 m legs). RViz shows GLIM's map (/glim_ros/map, coloured by height) growing,
the current aligned scan and the planned path, following Jo. Records RViz (xvfb), a low aerial
Gazebo camera (main), every third frame (3x time-lapse), and in each frame record the ground truth
(world frame), GLIM's local and global odometry and the EKF output, each with its message stamp,
for the ground truth page's plot (compared at equal stamps, not at the frame's sim time). The ground truth is only recorded here (evaluation), never fed to the stack.
Used by: ground truth page (the plot)."""
from nav_msgs.msg import Odometry  # noqa: E402  (the rig is prepended to this script)

# map frame = Jo's spawn pose (yaw pi): map (mx, my) is world (-mx, -my)
# Nav2 (mapless, rolling costmaps) aborts goals far outside its costmap: the street is split into
# goals ~8 m apart; the intermediate ones are passed through (next goal within 1.2 m)
GOALS = [((8.0, -0.3), 0.0), ((15.0, -0.3), -math.pi / 2), ((15.0, -8.0), -math.pi / 2),
         ((15.0, -16.0), -math.pi / 2), ((15.0, -25.0), -math.pi / 2)]
STRIDE = 3


def pose(m):
    p, q = m.pose.pose.position, m.pose.pose.orientation
    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
    stamp = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
    return [round(p.x, 4), round(p.y, 4), round(p.z, 4), round(yaw, 4), m.header.frame_id, round(stamp, 4)]


def shot():
    flat = {'Style': 'Flat Squares', 'Decay Time': 0, 'Enabled': True, 'Value': True}
    rv = rviz_config('glim_city', 'nav',
                     view={'Target Frame': 'base_footprint', 'Distance': 24.0, 'Pitch': 0.7,
                           'Yaw': 2.5, 'Focal Point': {'X': 3.0, 'Y': -3.0, 'Z': 0.0}},
                     set_displays={
                         'Front Camera Points': {**flat, 'Name': 'GLIM Map', 'Size (m)': 0.07,
                                                 'Color Transformer': 'AxisColor', 'Axis': 'Z',
                                                 'Autocompute Value Bounds': {'Max Value': 6.0, 'Min Value': -0.5, 'Value': False},
                                                 'Topic': {'Depth': 1, 'Durability Policy': 'Transient Local',
                                                           'History Policy': 'Keep Last',
                                                           'Reliability Policy': 'Reliable',
                                                           'Value': '/glim_ros/map'}},
                         'Back Camera Points': {**flat, 'Name': 'GLIM Scan', 'Size (m)': 0.06,
                                                'Color Transformer': 'FlatColor', 'Color': '6; 182; 212',
                                                'Topic': {'Depth': 5, 'Durability Policy': 'Volatile',
                                                          'History Policy': 'Keep Last',
                                                          'Reliability Policy': 'Reliable',
                                                          'Value': '/glim_ros/aligned_points'}},
                         'Lidar': {'Enabled': False, 'Value': False},
                         'Global Costmap': {'Enabled': False, 'Value': False},
                         'Local Costmap': {'Enabled': False, 'Value': False},
                         'Planned Path': {'Line Style': 'Billboards', 'Line Width': 0.25,
                                          'Color': '245; 158; 11'}})
    rig = Rig('glim_city', world='small_city',
              launch=['yaw:=3.1416', 'localization:=true', 'navigation:=true'], rviz=rv)
    try:
        rig.start(settle=10, ready_log='Managed nodes are active')
        cam = rig.camera('main', 1920, 1080)
        # /glim_ros/map goes out at most every map_publish_period s of sim time (default 10): a
        # runtime parameter of this run only, so the map grows smoothly in the time-lapse
        rig.run('ros2', 'param', 'set', '/glim_ros', 'map_publish_period', '1.0')
        rig.ros_value('gt', '/sim/ground_truth/odom', Odometry, pose)
        rig.ros_value('glim_local', '/glim_ros/odometry/local', Odometry, pose)
        rig.ros_value('glim_global', '/glim_ros/odometry/global', Odometry, pose)
        rig.ros_value('ekf', '/odometry/filtered', Odometry, pose)
        rig.frame(record=False)
        x, y, z, yaw = rig.robot
        eye, tgt = [x + 6.0, y - 5.0, z + 6.5], [x, y, z]
        g, sent, still, done_at = 0, False, 0, None
        for i in range(400 * FPS // STRIDE):
            rx, ry, rz, ryaw = rig.robot
            if done_at is not None:
                if i - done_at > FPS // STRIDE * 2:
                    break
                rig.frame(stride=STRIDE, xvfb_wait=0.3)
                continue
            if not sent:
                (mx, my), myaw = GOALS[g]
                rig.goal(mx, my, myaw)
                sent, t_sent = True, i
                rig.extra = {'goal': g}
            (mx, my), _ = GOALS[g]
            dist = math.hypot(rx + mx, ry + my)
            prev = getattr(rig, '_prev', (rx, ry, ryaw))
            moving = math.hypot(rx - prev[0], ry - prev[1]) > 0.004 or abs(ryaw - prev[2]) > 0.005
            rig._prev = (rx, ry, ryaw)
            still = 0 if moving else still + 1
            last = g == len(GOALS) - 1
            if (dist < 0.8 and still > 8 and i - t_sent > 20) or (not last and dist < 1.2):
                log(f'goal {g} reached at frame {rig.n}')
                g, sent = g + 1, False
                if g == len(GOALS):
                    done_at = i
            back = ryaw + math.pi + 0.6
            want = (rx + 7.0 * math.cos(back), ry + 7.0 * math.sin(back), rz + 5.5)
            eye = [e + (w - e) * 0.08 for e, w in zip(eye, want)]
            tgt = [p + (q - p) * 0.2 for p, q in zip(tgt, (rx + 1.5 * math.cos(ryaw), ry + 1.5 * math.sin(ryaw), rz))]
            cam.look(eye, tgt)
            rig.frame(stride=STRIDE, xvfb_wait=0.3, dist=round(dist, 2))
            if i == 300 and g == 0 and math.hypot(rx, ry) < 0.5:
                raise RuntimeError('Jo has not moved: the goal was not accepted?')
        else:
            log('timeout before the last goal')
    finally:
        rig.stop()


main(shot)
