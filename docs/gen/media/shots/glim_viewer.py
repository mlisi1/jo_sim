"""small_city, local navigation, with GLIM's own viewer on the virtual display: the Nav2 route of
glim_city (15 m west to the crossroads, then 25 m north, in ~8 m legs), every third frame (3x
time-lapse). The viewer runs from a docs-only copy of the sim's GLIM config (window size only) and
a docs-only imgui.ini (panel layout); the robot's and the sim's configs are not touched.
Used by: GLIM maps page."""
import pathlib  # noqa: E402  (the rig is prepended to this script)

GOALS = [((8.0, -0.3), 0.0), ((15.0, -0.3), -math.pi / 2), ((15.0, -8.0), -math.pi / 2),
         ((15.0, -16.0), -math.pi / 2), ((15.0, -25.0), -math.pi / 2)]
STRIDE = 3
MAX_FRAMES = 400 * FPS // STRIDE
VIEW = (1920, 1080)
SOURCE = '/home/ros/install/jo_navigation/share/jo_navigation/config/glim/glim_config_bunker_sim'
DOCS = pathlib.Path('/tmp/jo_sim/glim_docs')
IMGUI = """[Window][selection]
Pos=16,16
Collapsed=0

[Window][logging]
Pos=16,1040
Size=600,200
Collapsed=1

[Window][submap]
Pos=16,1000
Collapsed=1
"""


def docs_config():
    shutil.rmtree(DOCS, ignore_errors=True)
    shutil.copytree(SOURCE, DOCS / 'config')
    viewer = {'viewer_width': VIEW[0], 'viewer_height': VIEW[1], 'default_z_range': [-2.0, 4.0],
              'enable_partial_rendering': False, 'partial_rendering_budget': 1024,
              'point_shape_circle': True, 'point_size_metric': True, 'point_size': 0.025,
              'points_alpha': 0.5, 'factors_alpha': 0.5}
    (DOCS / 'config' / 'config_viewer.json').write_text(
        json.dumps({'standard_viewer': viewer, 'interactive_viewer': viewer}, indent=2))
    (DOCS / 'imgui.ini').write_text(IMGUI)


def shot():
    docs_config()
    rig = Rig('glim_viewer', world='small_city', cwd=str(DOCS), xvfb_crop=(0, 0, *VIEW),
              launch=['yaw:=3.1416', 'localization:=true', 'navigation:=true', 'glim_view:=true',
                      f'glim_config:={DOCS}/config'])
    try:
        rig.start(settle=10, ready_log='Managed nodes are active')
        cam = rig.camera('main', 1920, 1080)
        rig.frame(record=False)
        x, y, z, yaw = rig.robot
        eye, tgt = [x + 6.0, y - 5.0, z + 6.5], [x, y, z]
        g, sent, still, done_at = 0, False, 0, None
        for i in range(MAX_FRAMES):
            rx, ry, rz, ryaw = rig.robot
            if done_at is not None:
                if i - done_at > FPS // STRIDE * 2:
                    break
                rig.frame(stride=STRIDE, xvfb_wait=0.4)
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
            rig.frame(stride=STRIDE, xvfb_wait=0.4, dist=round(dist, 2))
            if i == 300 and g == 0 and math.hypot(rx, ry) < 0.5:
                raise RuntimeError('Jo has not moved: the goal was not accepted?')
        else:
            log('timeout before the last goal')
    finally:
        rig.stop()


main(shot)
