"""small_city, GPS navigation (full_gps_navigation): two GPS waypoints sent to Nav2's
follow_gps_waypoints (as send_gps_waypoints.py does), 15 m west to the crossroads, then 12 m north.
Records a high aerial camera following Jo (main), every other frame (2x time-lapse), and the /gnss
fix in each frame record. Used by: navigation page, hero reel."""
from sensor_msgs.msg import NavSatFix  # noqa: E402  (the rig is prepended to this script)
from jo_sim.world_tools import resolve_world, world_settings  # noqa: E402

WAYPOINTS = [(-15.0, 0.0), (-15.0, 12.0)]  # world (east, north) [m]


def shot():
    st = world_settings(resolve_world('small_city'), {}, '')
    datum = (float(st['latitude']), float(st['longitude']))
    rig = Rig('nav_gps', world='small_city',
              launch=['yaw:=3.1416', 'gnss:=true', 'localization_gps:=true', 'navigation_gps:=true'])
    try:
        rig.start(settle=10, ready_log='Managed nodes are active')
        cam = rig.camera('main', 1920, 1080)
        rig.ros_value('gnss', '/gnss', NavSatFix, lambda m: [m.latitude, m.longitude])
        rig.extra = {'datum': datum, 'waypoints': WAYPOINTS}
        rig.frame(record=False)
        x, y, z, yaw = rig.robot
        rig.gps_waypoints(WAYPOINTS, datum)
        eye = [x + 9.0, y - 7.0, z + 11.0]
        tgt = [x, y, z]
        still, end_at = 0, None
        wx, wy = WAYPOINTS[-1]
        for i in range(90 * FPS // 2):
            rx, ry, rz, ryaw = rig.robot
            back = ryaw + math.pi + 0.5
            want = (rx + 9.0 * math.cos(back), ry + 9.0 * math.sin(back), rz + 10.0)
            eye = [e + (w - e) * 0.04 for e, w in zip(eye, want)]
            tgt = [p + (q - p) * 0.15 for p, q in zip(tgt, (rx, ry, rz))]
            cam.look(eye, tgt)
            prev = getattr(rig, '_prev', (rx, ry))
            rig._prev = (rx, ry)
            still = still + 1 if math.hypot(rx - prev[0], ry - prev[1]) < 0.004 else 0
            if end_at is None and math.hypot(rx - wx, ry - wy) < 1.5 and still > 12:
                end_at = i
                log(f'last waypoint reached at frame {rig.n}')
            if end_at is not None and i - end_at > 20:
                break
            rig.frame(stride=2)
            if i == 10:
                f = rig._gps_future
                if not f.done() or not f.result().accepted:
                    raise RuntimeError('the GPS waypoints were not accepted')
                log('GPS waypoints accepted')
        else:
            log('timeout before the last waypoint')
        rig.extra = {}
    finally:
        rig.stop()


main(shot)
