"""Helper: a top-down render of small_city around the spawn (to plan the GPS route)."""
def shot():
    rig = Rig('city_top', world='small_city', launch=['lidar:=false', 'front_cam:=false', 'back_cam:=false'])
    try:
        rig.start(settle=20)
        cam = rig.camera('main', 1600, 1600, fov=1.4)
        cam.pose((0, 0, 60), (0, math.pi / 2, 0))   # image top = +x (east), right = -y (south)
        rig.frame()
        rig.frame()
    finally:
        rig.stop()
main(shot)
