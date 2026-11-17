"""office_cpr, local navigation (GLIM + EKF + Nav2): a goal 4.5 m ahead, then back.
Records a high chase camera (main), RViz (navigation view: costmaps, path, lidar) and Jo's front
camera (front). Goals go to /goal_pose in the map frame, as RViz's 2D Goal Pose tool does; the map
frame starts at the spawn pose (x 0, y 0, yaw 90°), so map (mx, my) is world (-my, mx).
Used by: navigation page, hero reel."""

GOALS = [((4.5, 0.0), 0.0), ((1.0, 0.0), math.pi)]  # map frame


def shot():
    rv = rviz_config('nav_local', 'nav',
                     view={'Target Frame': 'base_footprint', 'Distance': 10.0, 'Pitch': 0.95,
                           'Yaw': math.pi + 0.55, 'Focal Point': {'X': 1.5, 'Y': 0.0, 'Z': 0.0}},
                     set_displays={'Global Costmap': {'Enabled': True, 'Value': True, 'Alpha': 0.3},
                                   'Local Costmap': {'Alpha': 0.45},
                                   'Planned Path': {'Line Style': 'Billboards', 'Line Width': 0.09,
                                                    'Color': '245; 158; 11'},
                                   'Front Camera Points': {'Enabled': False},
                                   'Back Camera Points': {'Enabled': False},
                                   'Lidar': {'Size (Pixels)': 4}})
    rig = Rig('nav_local', world='office_cpr',
              launch=['yaw:=1.5708', 'localization:=true', 'navigation:=true'], rviz=rv)
    try:
        rig.start(settle=10, ready_log='Managed nodes are active')
        cam = rig.camera('main', 1920, 1080)
        rig.ros_camera('front', '/front_camera/camera/color/image_raw')
        rig.frame(record=False)
        x, y, z, yaw = rig.robot
        eye = [x - 4.2, y - 3.0, z + 3.4]
        tgt = [x, y + 1.0, z]
        g, sent, still, done_at = 0, False, 0, None
        for i in range(60 * FPS):
            rx, ry, rz, ryaw = rig.robot
            if done_at is not None:
                if i - done_at > FPS:
                    break
                rig.frame()
                continue
            if not sent:
                (mx, my), myaw = GOALS[g]
                rig.goal(mx, my, myaw)
                sent, t_sent = True, i
                rig.extra = {'goal': g}
            (mx, my), _ = GOALS[g]
            wx, wy = -my, mx
            dist = math.hypot(rx - wx, ry - wy)
            prev = getattr(rig, '_prev', (rx, ry, ryaw))
            moving = math.hypot(rx - prev[0], ry - prev[1]) > 0.002 or abs(ryaw - prev[2]) > 0.003
            rig._prev = (rx, ry, ryaw)
            still = 0 if moving else still + 1
            if dist < 0.5 and still > FPS and i - t_sent > 2 * FPS:
                log(f'goal {g} reached at frame {rig.n}')
                g += 1
                sent = False
                if g == len(GOALS):
                    done_at = i
            # high chase camera, behind-left of the robot, smoothed
            back = ryaw + math.pi - 0.6
            want = (rx + 4.6 * math.cos(back), ry + 4.6 * math.sin(back), rz + 3.4)
            eye = [e + (w - e) * 0.05 for e, w in zip(eye, want)]
            tgt = [p + (q - p) * 0.12 for p, q in zip(tgt, (rx + math.cos(ryaw), ry + math.sin(ryaw), rz))]
            cam.look(eye, tgt)
            rig.frame(dist=round(dist, 3))
        else:
            log('timeout before the last goal')
    finally:
        rig.stop()


main(shot)
