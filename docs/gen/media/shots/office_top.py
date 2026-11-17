"""Helper: a top-down render of office_cpr with a 1 m grid reference (to plan routes)."""
def shot():
    rig = Rig('office_top', world='office_cpr')
    try:
        rig.start(settle=12)
        cam = rig.camera('main', 1600, 1600, fov=1.4)
        cam.pose((0, 0, 14), (0, math.pi / 2, math.pi / 2))   # looking down, image up = +x? (yaw 90: up = +y?)
        rig.frame()
        rig.frame()
    finally:
        rig.stop()
main(shot)
