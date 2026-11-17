"""office_cpr, sensors only: orbit around Jo at rest, then a drive into the open room with a chase camera.
Records the Gazebo camera (main), RViz (sim view, cropped) and Jo's front camera (front).
Used by: hero reel, first-run clip."""


def shot():
    rv = rviz_config('office_drive', 'sim', view={'Distance': 8.5, 'Pitch': 0.62, 'Yaw': 3.55,
                                                  'Focal Point': {'X': 2.5, 'Y': 0.0, 'Z': 0.0}},
                     set_displays=DOCS_CLOUDS)
    rig = Rig('office_drive', world='office_cpr', launch=['yaw:=1.5708'], rviz=rv)
    try:
        rig.start(settle=30)
        cam = rig.camera('main', 1920, 1080)
        rig.ros_camera('front', '/front_camera/camera/color/image_raw')
        rig.frame(record=False)
        x, y, z, yaw = rig.robot
        # A: orbit, 5 s, from the front-left round to behind
        n = 5 * FPS
        for i in range(n):
            u = smooth(i / (n - 1))
            a = yaw + math.radians(40 + 130 * u)
            r, h = 3.4 - 0.6 * u, 1.3 + 0.3 * u
            cam.look((x + r * math.cos(a), y + r * math.sin(a), z + h), (x, y, z + 0.15))
            rig.frame(part='orbit')
        # B: drive 10 s: 2.4 m along +y into the open room, a left arc (r 1.2 m), then along -x
        eye = [x + r * math.cos(a), y + r * math.sin(a), z + h]
        tgt = [x, y, z + 0.15]
        n = 10 * FPS
        for i in range(n):
            t = i / FPS
            vx = 0.6 * smooth(t / 1.0)
            wz = 0.0 if t < 4.4 else 0.5 * smooth((t - 4.4) / 0.6) * (1 - smooth((t - 7.5) / 0.6))
            rig.cmd_vel(vx, wz)
            rx, ry, rz, ryaw = rig.robot
            back = ryaw + math.pi + math.radians(25)
            want = (rx + 2.8 * math.cos(back), ry + 2.8 * math.sin(back), rz + 1.25)
            k = 0.06 + 0.06 * smooth(i / 50)
            eye = [e + (w - e) * k for e, w in zip(eye, want)]
            look = (rx + 0.8 * math.cos(ryaw), ry + 0.8 * math.sin(ryaw), rz + 0.15)
            tgt = [p + (q - p) * 0.25 for p, q in zip(tgt, look)]
            cam.look(eye, tgt)
            rig.frame(part='drive')
        rig.cmd_vel(0, 0)
    finally:
        rig.stop()


main(shot)
